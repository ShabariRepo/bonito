#!/opt/homebrew/bin/python3.11
"""
Proper TurboQuant benchmark: Our implementation vs Google's theoretical bounds.

Key fixes from reading the paper (arxiv 2504.19874):
1. After random rotation, coordinates follow Beta distribution -- use Lloyd-Max
   optimal scalar quantizer, NOT uniform bins
2. QJL estimator: unbiased inner product = <y, x_hat> + <sign(M*y), sign(M*r)> / sqrt(k)
   where r = x - x_hat (residual), M is random projection, k = projection dims
3. TurboQuant uses (b-1) bits PolarQuant + 1 bit QJL = b bits total

Paper's theoretical distortion bounds (Table 1):
  MSE at b bits: ~(sqrt(3)*pi/2) * (1/4^b) ≈ 2.72 / 4^b
  Specific: 1-bit: 0.36, 2-bit: 0.117, 3-bit: 0.03, 4-bit: 0.009
  
  Inner product at b bits: ~(sqrt(3)*pi^2 / d) * (1/4^b)
  Specific: 1-bit: 1.57/d, 2-bit: 0.56/d, 3-bit: 0.18/d, 4-bit: 0.047/d

Lower bound (information-theoretic): 1/4^b for MSE, ||y||^2/(d*4^b) for inner product
"""

import numpy as np
import time
import struct
import sys
from typing import List, Tuple
from scipy.stats import beta as beta_dist
from scipy.optimize import minimize_scalar


# ═══════════════════════════════════════════════════════════
# Lloyd-Max Optimal Scalar Quantizer for Beta Distribution
# ═══════════════════════════════════════════════════════════

def lloyd_max_beta(d: int, levels: int, max_iter: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute Lloyd-Max optimal quantizer for the Beta distribution
    that arises from coordinates of a random rotation of unit vectors.
    
    After random rotation, each coordinate of a unit vector follows:
      f(x) = Gamma(d/2) / (sqrt(pi) * Gamma((d-1)/2)) * (1-x^2)^((d-3)/2)
    
    This is equivalent to a scaled Beta distribution on [-1, 1].
    
    Returns:
      boundaries: (levels+1,) array of decision boundaries
      centroids:  (levels,) array of reconstruction points
    """
    # Beta parameters for coordinate distribution on [-1, 1]
    # This is Beta((d-1)/2, (d-1)/2) shifted to [-1, 1]
    alpha_param = (d - 1) / 2
    
    # Initialize boundaries uniformly on [-1, 1]
    boundaries = np.linspace(-1, 1, levels + 1)
    centroids = np.zeros(levels)
    
    for _ in range(max_iter):
        # Update centroids: E[X | boundary[i] <= X < boundary[i+1]]
        for i in range(levels):
            lo, hi = boundaries[i], boundaries[i + 1]
            # Map [-1,1] to [0,1] for scipy beta
            lo_01 = (lo + 1) / 2
            hi_01 = (hi + 1) / 2
            
            # Conditional expectation of Beta(alpha, alpha) on [lo_01, hi_01]
            prob = beta_dist.cdf(hi_01, alpha_param, alpha_param) - beta_dist.cdf(lo_01, alpha_param, alpha_param)
            if prob < 1e-15:
                centroids[i] = (lo + hi) / 2
            else:
                # Numerical integration for conditional mean
                from scipy.integrate import quad
                def integrand(x):
                    return x * beta_dist.pdf(x, alpha_param, alpha_param)
                mean_01, _ = quad(integrand, lo_01, hi_01)
                centroids[i] = (mean_01 / prob) * 2 - 1  # Map back to [-1, 1]
        
        # Update boundaries: midpoints of adjacent centroids
        old_boundaries = boundaries.copy()
        for i in range(1, levels):
            boundaries[i] = (centroids[i - 1] + centroids[i]) / 2
        
        if np.max(np.abs(boundaries - old_boundaries)) < 1e-10:
            break
    
    return boundaries, centroids


def quantize_lloyd_max(values: np.ndarray, boundaries: np.ndarray, centroids: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Quantize values using precomputed Lloyd-Max boundaries and centroids."""
    indices = np.searchsorted(boundaries[1:-1], values)  # Which bin
    reconstructed = centroids[indices]
    return indices.astype(np.uint8), reconstructed


# ═══════════════════════════════════════════════════════════
# Method implementations
# ═══════════════════════════════════════════════════════════

class RawBaseline:
    name = "Raw float32"
    
    def __init__(self, d):
        self.d = d
    
    def compress(self, vecs):
        return [v.tobytes() for v in vecs]
    
    def size(self, compressed):
        return sum(len(c) for c in compressed)
    
    def search(self, query, vecs_raw, top_k):
        """Exact cosine similarity."""
        scores = vecs_raw @ query
        top = np.argsort(scores)[-top_k:][::-1]
        return [(int(i), float(scores[i])) for i in top]


class NaiveScalar:
    """Industry standard: per-vector min/max + uniform quantization."""
    
    def __init__(self, d, bits):
        self.d = d
        self.bits = bits
        self.levels = (1 << bits) - 1
        self.name = f"Naive Scalar {bits}-bit"
    
    def compress(self, vecs):
        results = []
        for v in vecs:
            vmin, vmax = float(v.min()), float(v.max())
            scale = vmax - vmin if vmax > vmin else 1.0
            q = np.clip(np.round((v - vmin) / scale * self.levels), 0, self.levels).astype(np.uint8)
            results.append((vmin, vmax, q))
        return results
    
    def size(self, compressed):
        # 8 bytes overhead per vector (min + max) + quantized data
        return len(compressed) * (8 + self.d * self.bits // 8)
    
    def decompress_one(self, item):
        vmin, vmax, q = item
        scale = vmax - vmin if vmax > vmin else 1.0
        return (q.astype(np.float32) / self.levels) * scale + vmin
    
    def search(self, query, compressed, top_k):
        scores = []
        for idx, item in enumerate(compressed):
            v = self.decompress_one(item)
            scores.append((idx, float(np.dot(query, v))))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class PolarQuantFixed:
    """
    Our PolarQuant with UNIFORM quantization (our first attempt).
    Random rotation + uniform bins. No per-vector overhead.
    """
    
    def __init__(self, d, bits, seed=42):
        self.d = d
        self.bits = bits
        self.levels = (1 << bits) - 1
        self.name = f"PolarQuant (uniform) {bits}-bit"
        self._init_rotation(seed)
    
    def _init_rotation(self, seed):
        rng = np.random.RandomState(seed)
        if self.d <= 2048:
            G = rng.randn(self.d, self.d).astype(np.float32)
            Q, R = np.linalg.qr(G)
            self._R = (Q * np.sign(np.diag(R))).astype(np.float32)
        else:
            bs = 512
            self._R = np.zeros((self.d, self.d), dtype=np.float32)
            off = 0
            for i in range(0, self.d, bs):
                s = min(bs, self.d - i)
                G = rng.randn(s, s).astype(np.float32)
                Q, R = np.linalg.qr(G)
                self._R[off:off+s, off:off+s] = Q * np.sign(np.diag(R))
                off += s
    
    def compress(self, vecs):
        rotated = (self._R @ vecs.T).T
        results = []
        for v in rotated:
            r = np.linalg.norm(v)
            if r < 1e-10:
                results.append((0.0, np.zeros(self.d, dtype=np.uint8)))
                continue
            d = v / r
            q = np.clip(np.round((d + 1.0) * 0.5 * self.levels), 0, self.levels).astype(np.uint8)
            results.append((r, q))
        return results
    
    def size(self, compressed):
        return len(compressed) * (4 + self.d * self.bits // 8)  # radius + quantized
    
    def search(self, query, compressed, top_k):
        rq = self._R @ query
        rq_norm = np.linalg.norm(rq)
        if rq_norm < 1e-10:
            return [(i, 0.0) for i in range(min(top_k, len(compressed)))]
        rq_dir = rq / rq_norm
        
        scores = []
        for idx, (radius, q) in enumerate(compressed):
            if abs(radius) < 1e-10:
                scores.append((idx, 0.0))
                continue
            d_approx = (q.astype(np.float32) / self.levels) * 2.0 - 1.0
            scores.append((idx, float(np.dot(rq_dir, d_approx))))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class PolarQuantLloydMax:
    """
    PolarQuant with Lloyd-Max optimal quantizer (paper's approach).
    Random rotation + Beta-distribution-optimal scalar quantizer.
    """
    
    def __init__(self, d, bits, seed=42):
        self.d = d
        self.bits = bits
        self.name = f"PolarQuant (Lloyd-Max) {bits}-bit"
        self._init_rotation(seed)
        
        # Precompute Lloyd-Max codebook
        levels = 1 << bits
        print(f"    Computing Lloyd-Max codebook for d={d}, levels={levels}...")
        self._boundaries, self._centroids = lloyd_max_beta(d, levels)
        print(f"    Codebook ready. Centroids: {self._centroids[:4]}...{self._centroids[-4:]}")
    
    def _init_rotation(self, seed):
        rng = np.random.RandomState(seed)
        if self.d <= 2048:
            G = rng.randn(self.d, self.d).astype(np.float32)
            Q, R = np.linalg.qr(G)
            self._R = (Q * np.sign(np.diag(R))).astype(np.float32)
        else:
            bs = 512
            self._R = np.zeros((self.d, self.d), dtype=np.float32)
            off = 0
            for i in range(0, self.d, bs):
                s = min(bs, self.d - i)
                G = rng.randn(s, s).astype(np.float32)
                Q, R = np.linalg.qr(G)
                self._R[off:off+s, off:off+s] = Q * np.sign(np.diag(R))
                off += s
    
    def compress(self, vecs):
        rotated = (self._R @ vecs.T).T
        results = []
        for v in rotated:
            r = np.linalg.norm(v)
            if r < 1e-10:
                results.append((0.0, np.zeros(self.d, dtype=np.uint8), np.zeros(self.d, dtype=np.float32)))
                continue
            direction = v / r
            indices, reconstructed = quantize_lloyd_max(direction, self._boundaries, self._centroids)
            results.append((r, indices, reconstructed))
        return results
    
    def size(self, compressed):
        return len(compressed) * (4 + self.d * self.bits // 8)
    
    def search(self, query, compressed, top_k):
        rq = self._R @ query
        rq_norm = np.linalg.norm(rq)
        if rq_norm < 1e-10:
            return [(i, 0.0) for i in range(min(top_k, len(compressed)))]
        rq_dir = rq / rq_norm
        
        scores = []
        for idx, (radius, indices, recon) in enumerate(compressed):
            if abs(radius) < 1e-10:
                scores.append((idx, 0.0))
                continue
            scores.append((idx, float(np.dot(rq_dir, recon))))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class TurboQuantProper:
    """
    Full TurboQuant: (b-1)-bit PolarQuant (Lloyd-Max) + 1-bit QJL on residual.
    
    The unbiased inner product estimator:
      <y, x> ≈ <y, x_hat> + ||r|| * <sign(M*y_dir), sign(M*r_dir)> * sqrt(d/k)
    
    where x_hat = dequantized PolarQuant output, r = x_rotated - x_hat,
    M is random {+1,-1} projection matrix of shape (k, d), k = d
    """
    
    def __init__(self, d, total_bits, seed=42):
        self.d = d
        self.total_bits = total_bits
        self.pq_bits = max(1, total_bits - 1)  # Reserve 1 bit for QJL
        self.name = f"TurboQuant ({self.pq_bits}+1 bit)"
        
        self._init_rotation(seed)
        
        # Lloyd-Max codebook for PolarQuant stage
        levels = 1 << self.pq_bits
        print(f"    Computing Lloyd-Max codebook for d={d}, levels={levels} (TurboQuant)...")
        self._boundaries, self._centroids = lloyd_max_beta(d, levels)
        
        # QJL random sign matrix: each entry is +1 or -1
        rng = np.random.RandomState(seed + 1000)
        self._qjl_signs = rng.choice([-1, 1], size=(d, d)).astype(np.float32)
        # Normalize by sqrt(d) for JL guarantee
        self._qjl_signs /= np.sqrt(d)
    
    def _init_rotation(self, seed):
        rng = np.random.RandomState(seed)
        if self.d <= 2048:
            G = rng.randn(self.d, self.d).astype(np.float32)
            Q, R = np.linalg.qr(G)
            self._R = (Q * np.sign(np.diag(R))).astype(np.float32)
        else:
            bs = 512
            self._R = np.zeros((self.d, self.d), dtype=np.float32)
            off = 0
            for i in range(0, self.d, bs):
                s = min(bs, self.d - i)
                G = rng.randn(s, s).astype(np.float32)
                Q, R = np.linalg.qr(G)
                self._R[off:off+s, off:off+s] = Q * np.sign(np.diag(R))
                off += s
    
    def compress(self, vecs):
        rotated = (self._R @ vecs.T).T
        results = []
        for v in rotated:
            r = np.linalg.norm(v)
            if r < 1e-10:
                results.append((0.0, np.zeros(self.d, dtype=np.float32), np.zeros(self.d, dtype=np.float32)))
                continue
            direction = v / r
            
            # Stage 1: PolarQuant with Lloyd-Max
            indices, reconstructed = quantize_lloyd_max(direction, self._boundaries, self._centroids)
            
            # Stage 2: QJL on residual
            residual = direction - reconstructed
            # Project and keep sign bits
            projected = self._qjl_signs @ residual
            qjl_bits = np.sign(projected)  # +1 or -1
            
            results.append((r, reconstructed, qjl_bits))
        return results
    
    def size(self, compressed):
        # (pq_bits per dim) + (1 bit per dim for QJL) + 4 bytes radius
        return len(compressed) * (4 + self.d * self.pq_bits // 8 + self.d // 8)
    
    def search(self, query, compressed, top_k):
        rq = self._R @ query
        rq_norm = np.linalg.norm(rq)
        if rq_norm < 1e-10:
            return [(i, 0.0) for i in range(min(top_k, len(compressed)))]
        rq_dir = rq / rq_norm
        
        # Pre-project query through QJL
        qjl_query = np.sign(self._qjl_signs @ rq_dir)
        
        scores = []
        for idx, (radius, recon, qjl_bits) in enumerate(compressed):
            if abs(radius) < 1e-10:
                scores.append((idx, 0.0))
                continue
            
            # PolarQuant score
            pq_score = np.dot(rq_dir, recon)
            
            # QJL correction: unbiased estimate of <rq_dir, residual>
            # Using sign sketch: <sign(M*q), sign(M*r)> ≈ (2/pi) * <q, r>
            # (Goemans-Williamson / sign-sketch property)
            qjl_correction = np.dot(qjl_query, qjl_bits) / self.d
            # Scale by 2/pi to get unbiased estimate (sign sketch property)
            qjl_correction *= (np.pi / 2)
            
            score = pq_score + qjl_correction
            scores.append((idx, float(score)))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ═══════════════════════════════════════════════════════════
# Benchmark Runner
# ═══════════════════════════════════════════════════════════

def run_full_benchmark(d: int = 256, n: int = 500, bits: int = 4):
    print(f"\n{'='*80}")
    print(f"  BENCHMARK: d={d}, n={n}, target={bits}-bit")
    print(f"{'='*80}\n")
    
    # Generate normalized test embeddings
    rng = np.random.RandomState(42)
    vecs = rng.randn(n, d).astype(np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    
    n_queries = 20
    top_k = 10
    qi = rng.choice(n, n_queries, replace=False)
    
    # Ground truth
    gt = {}
    for q in qi:
        scores = vecs @ vecs[q]
        gt[q] = set(np.argsort(scores)[-top_k:])
    
    # Paper's theoretical bounds
    paper_mse = {1: 0.36, 2: 0.117, 3: 0.03, 4: 0.009}
    paper_ip = {1: 1.57, 2: 0.56, 3: 0.18, 4: 0.047}  # multiply by 1/d
    lower_mse = 1.0 / (4 ** bits)
    lower_ip = 1.0 / (d * (4 ** bits))
    
    # Methods
    print("Initializing methods...")
    t0 = time.time()
    methods = [
        ("raw", RawBaseline(d)),
        ("naive", NaiveScalar(d, bits)),
        ("pq_uniform", PolarQuantFixed(d, bits)),
        ("pq_lloydmax", PolarQuantLloydMax(d, bits)),
        ("turboquant", TurboQuantProper(d, bits)),
    ]
    print(f"Init: {time.time()-t0:.1f}s\n")
    
    results = []
    
    for label, method in methods:
        print(f"--- {method.name} ---")
        
        # Compress
        t0 = time.time()
        if label == "raw":
            compressed = method.compress(vecs)
        elif label == "naive":
            compressed = method.compress(vecs)
        else:
            compressed = method.compress(vecs)
        ct = time.time() - t0
        
        # Size
        sz = method.size(compressed)
        orig_sz = n * d * 4
        ratio = orig_sz / sz if sz > 0 else 0
        
        # MSE distortion (reconstruction error)
        mse = 0.0
        if label != "raw":
            if label == "naive":
                for i, item in enumerate(compressed):
                    recon = method.decompress_one(item)
                    mse += np.mean((vecs[i] - recon) ** 2)
                mse /= n
            elif label in ("pq_uniform", "pq_lloydmax", "turboquant"):
                for i, item in enumerate(compressed):
                    radius = item[0]
                    if abs(radius) < 1e-10:
                        mse += np.mean(vecs[i] ** 2)
                        continue
                    if label == "pq_uniform":
                        recon_dir = (item[1].astype(np.float32) / ((1 << bits) - 1)) * 2.0 - 1.0
                    else:
                        recon_dir = item[1] if isinstance(item[1], np.ndarray) and item[1].dtype == np.float32 else item[1].astype(np.float32)
                    recon_rotated = radius * recon_dir
                    recon_orig = method._R.T @ recon_rotated
                    mse += np.mean((vecs[i] - recon_orig) ** 2)
                mse /= n
        
        # Recall
        recalls = []
        t0 = time.time()
        for q in qi:
            query = vecs[q]
            if label == "raw":
                res = method.search(query, vecs, top_k)
            else:
                res = method.search(query, compressed, top_k)
            result_set = set(idx for idx, _ in res)
            recalls.append(len(gt[q] & result_set) / top_k)
        st = time.time() - t0
        avg_recall = np.mean(recalls)
        
        # Inner product distortion
        ip_distortions = []
        for q in qi[:5]:
            query = vecs[q]
            exact_scores = vecs @ query
            if label == "raw":
                approx = method.search(query, vecs, n)
            else:
                approx = method.search(query, compressed, n)
            approx_arr = np.zeros(n)
            for idx, sc in approx:
                approx_arr[idx] = sc
            ip_distortions.append(np.mean((exact_scores - approx_arr) ** 2))
        avg_ip_dist = np.mean(ip_distortions)
        
        r = {
            "method": method.name,
            "ratio": ratio,
            "mse": mse,
            "recall": avg_recall,
            "ip_distortion": avg_ip_dist,
            "compress_ms": ct * 1000,
            "search_ms": st / n_queries * 1000,
            "size_kb": sz / 1024,
        }
        results.append(r)
        
        print(f"  Ratio:       {ratio:.1f}x")
        print(f"  MSE:         {mse:.6f}")
        print(f"  Recall@{top_k}:  {avg_recall:.1%}")
        print(f"  IP distort:  {avg_ip_dist:.6f}")
        print(f"  Compress:    {ct*1000:.1f}ms")
        print(f"  Search:      {st/n_queries*1000:.2f}ms/q")
        print()
    
    # Summary table
    print(f"\n{'='*80}")
    print(f"  RESULTS vs GOOGLE'S PAPER (d={d}, {bits}-bit)")
    print(f"{'='*80}")
    
    print(f"\n{'Method':<35} {'Ratio':>6} {'MSE':>10} {'Recall@10':>10} {'IP Dist':>10}")
    print(f"{'-'*35} {'-'*6} {'-'*10} {'-'*10} {'-'*10}")
    for r in results:
        print(f"{r['method']:<35} {r['ratio']:>5.1f}x {r['mse']:>10.6f} {r['recall']:>9.1%} {r['ip_distortion']:>10.6f}")
    
    print(f"\n--- Google Paper's Bounds ({bits}-bit) ---")
    if bits in paper_mse:
        print(f"  Paper MSE distortion:     {paper_mse[bits]:.6f}")
        print(f"  Paper IP distortion:      {paper_ip[bits]/d:.6f} ({paper_ip[bits]}/d)")
        print(f"  Info-theoretic lower MSE: {lower_mse:.6f}")
        print(f"  Info-theoretic lower IP:  {lower_ip:.8f}")
    
    print(f"\n--- Analysis ---")
    for r in results:
        if r['mse'] > 0 and bits in paper_mse:
            vs_paper = r['mse'] / paper_mse[bits]
            vs_lower = r['mse'] / lower_mse
            print(f"  {r['method']:<35} MSE is {vs_paper:.1f}x paper's, {vs_lower:.1f}x lower bound")
    
    print()
    return results


if __name__ == "__main__":
    d = int(sys.argv[1]) if len(sys.argv) > 1 else 256
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    
    print("=" * 80)
    print("  BONITO vs GOOGLE TURBOQUANT -- PROPER BENCHMARK")
    print("  Paper: arxiv 2504.19874 (ICLR 2026)")
    print("=" * 80)
    
    for bits in [4, 8]:
        run_full_benchmark(d=d, n=n, bits=bits)
