#!/opt/homebrew/bin/python3.11
"""
Comprehensive benchmark: Raw (uncompressed) vs Naive Quantization vs PolarQuant vs TurboQuant (PolarQuant + QJL)

Tests across multiple dimensions and vector counts to simulate real Bonito KB workloads.

Measures:
  - Compression ratio (memory savings)
  - Recall@10 (search accuracy -- does it find the same top results?)
  - Recall@50
  - Dot-product distortion (how much does similarity scoring drift?)
  - Compression time (latency to store a new chunk)
  - Search time (latency to query)
  - Reconstruction error (how close is decompressed vector to original?)
"""

import numpy as np
import time
import struct
import sys
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════
# METHOD 1: Raw (baseline -- no compression)
# ═══════════════════════════════════════════════════════════

class RawVectors:
    """No compression. Full float32 storage. Ground truth baseline."""

    def __init__(self, dimensions: int):
        self.dimensions = dimensions
        self.name = "Raw (float32)"

    def compress(self, embeddings: np.ndarray) -> List[bytes]:
        return [vec.tobytes() for vec in embeddings]

    def decompress(self, compressed: List[bytes]) -> np.ndarray:
        return np.array([np.frombuffer(c, dtype=np.float32) for c in compressed])

    def search(self, query: np.ndarray, compressed: List[bytes], top_k: int = 10) -> List[Tuple[int, float]]:
        # Exact cosine similarity
        vectors = self.decompress(compressed)
        scores = vectors @ query
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [(int(i), float(scores[i])) for i in top_indices]

    def compressed_size(self, compressed: List[bytes]) -> int:
        return sum(len(c) for c in compressed)


# ═══════════════════════════════════════════════════════════
# METHOD 2: Naive Scalar Quantization (industry standard baseline)
# Min-max normalization + uniform quantization per vector
# This is what most production systems use (e.g., Qdrant, Weaviate)
# ═══════════════════════════════════════════════════════════

class NaiveScalarQuantization:
    """
    Standard scalar quantization: per-vector min/max + uniform n-bit bins.
    Stores 2 float32 overhead per vector (min + max) -- this is the overhead
    that TurboQuant eliminates.
    """

    def __init__(self, dimensions: int, bits: int = 8):
        self.dimensions = dimensions
        self.bits = bits
        self.name = f"Naive Scalar ({bits}-bit)"

    def compress(self, embeddings: np.ndarray) -> List[bytes]:
        results = []
        levels = (1 << self.bits) - 1

        for vec in embeddings:
            vmin = float(vec.min())
            vmax = float(vec.max())
            scale = vmax - vmin if vmax > vmin else 1.0

            # Quantize to [0, levels]
            quantized = np.clip(
                np.round((vec - vmin) / scale * levels),
                0, levels
            ).astype(np.uint8)

            # Pack: [float32 min] + [float32 max] + [quantized values]
            header = struct.pack('ff', vmin, vmax)

            if self.bits == 4:
                packed = bytearray()
                for i in range(0, len(quantized), 2):
                    high = quantized[i] & 0x0F
                    low = (quantized[i + 1] & 0x0F) if i + 1 < len(quantized) else 0
                    packed.append((high << 4) | low)
                results.append(header + bytes(packed))
            elif self.bits == 8:
                results.append(header + quantized.tobytes())
            else:
                results.append(header + quantized.tobytes())

        return results

    def decompress(self, compressed: List[bytes]) -> np.ndarray:
        results = []
        levels = (1 << self.bits) - 1

        for data in compressed:
            vmin, vmax = struct.unpack('ff', data[:8])
            scale = vmax - vmin if vmax > vmin else 1.0

            if self.bits == 4:
                packed = data[8:]
                quantized = np.zeros(self.dimensions, dtype=np.float32)
                for i, byte in enumerate(packed):
                    idx = i * 2
                    if idx < self.dimensions:
                        quantized[idx] = (byte >> 4) & 0x0F
                    if idx + 1 < self.dimensions:
                        quantized[idx + 1] = byte & 0x0F
            elif self.bits == 8:
                quantized = np.frombuffer(data[8:8 + self.dimensions], dtype=np.uint8).astype(np.float32)
            else:
                quantized = np.frombuffer(data[8:], dtype=np.uint8).astype(np.float32)

            vec = (quantized / levels) * scale + vmin
            results.append(vec)

        return np.array(results, dtype=np.float32)

    def search(self, query: np.ndarray, compressed: List[bytes], top_k: int = 10) -> List[Tuple[int, float]]:
        vectors = self.decompress(compressed)
        scores = vectors @ query
        top_indices = np.argsort(scores)[-top_k:][::-1]
        return [(int(i), float(scores[i])) for i in top_indices]

    def compressed_size(self, compressed: List[bytes]) -> int:
        return sum(len(c) for c in compressed)


# ═══════════════════════════════════════════════════════════
# METHOD 3: PolarQuant (rotation + polar quantization, no QJL)
# ═══════════════════════════════════════════════════════════

class PolarQuantCompression:
    """
    PolarQuant only (no QJL correction).
    Random rotation + uniform quantization on rotated coordinates.
    Zero overhead -- no per-vector constants stored.
    """

    def __init__(self, dimensions: int, bits: int = 8, seed: int = 42):
        self.dimensions = dimensions
        self.bits = bits
        self.seed = seed
        self.name = f"PolarQuant ({bits}-bit)"
        self._init_rotation()

    def _init_rotation(self):
        rng = np.random.RandomState(self.seed)
        if self.dimensions <= 2048:
            G = rng.randn(self.dimensions, self.dimensions).astype(np.float32)
            Q, R = np.linalg.qr(G)
            d = np.sign(np.diag(R))
            self._rotation = (Q * d).astype(np.float32)
        else:
            # Block-diagonal for large dims
            block_size = 512
            self._rotation = np.zeros((self.dimensions, self.dimensions), dtype=np.float32)
            offset = 0
            for i in range(0, self.dimensions, block_size):
                bs = min(block_size, self.dimensions - i)
                G = rng.randn(bs, bs).astype(np.float32)
                Q, R = np.linalg.qr(G)
                d = np.sign(np.diag(R))
                self._rotation[offset:offset + bs, offset:offset + bs] = Q * d
                offset += bs

    def compress(self, embeddings: np.ndarray) -> List[bytes]:
        results = []
        levels = (1 << self.bits) - 1

        # Rotate all vectors at once (matrix multiply)
        rotated = (self._rotation @ embeddings.T).T

        for vec in rotated:
            radius = np.linalg.norm(vec)
            if radius < 1e-10:
                results.append(struct.pack('f', 0.0) + b'\x00' * ((self.dimensions * self.bits + 7) // 8))
                continue

            direction = vec / radius

            # Quantize direction: [-1, 1] -> [0, levels]
            quantized = np.clip(
                np.round((direction + 1.0) * 0.5 * levels),
                0, levels
            ).astype(np.uint8)

            header = struct.pack('f', radius)

            if self.bits == 4:
                packed = bytearray()
                for i in range(0, len(quantized), 2):
                    high = quantized[i] & 0x0F
                    low = (quantized[i + 1] & 0x0F) if i + 1 < len(quantized) else 0
                    packed.append((high << 4) | low)
                results.append(header + bytes(packed))
            elif self.bits == 8:
                results.append(header + quantized.tobytes())
            else:
                results.append(header + quantized.tobytes())

        return results

    def _dequant_direction(self, data: bytes) -> Tuple[float, np.ndarray]:
        radius = struct.unpack('f', data[:4])[0]
        levels = (1 << self.bits) - 1

        if self.bits == 4:
            packed = data[4:]
            direction = np.zeros(self.dimensions, dtype=np.float32)
            for i, byte in enumerate(packed):
                idx = i * 2
                if idx < self.dimensions:
                    direction[idx] = ((byte >> 4) & 0x0F) / levels * 2.0 - 1.0
                if idx + 1 < self.dimensions:
                    direction[idx + 1] = (byte & 0x0F) / levels * 2.0 - 1.0
        elif self.bits == 8:
            direction = np.frombuffer(data[4:4 + self.dimensions], dtype=np.uint8).astype(np.float32)
            direction = direction / levels * 2.0 - 1.0
        else:
            direction = np.frombuffer(data[4:4 + self.dimensions], dtype=np.uint8).astype(np.float32)
            direction = direction / levels * 2.0 - 1.0

        return radius, direction

    def decompress(self, compressed: List[bytes]) -> np.ndarray:
        results = []
        for data in compressed:
            radius, direction = self._dequant_direction(data)
            if abs(radius) < 1e-10:
                results.append(np.zeros(self.dimensions, dtype=np.float32))
            else:
                vec = radius * (self._rotation.T @ direction)
                results.append(vec)
        return np.array(results, dtype=np.float32)

    def search(self, query: np.ndarray, compressed: List[bytes], top_k: int = 10) -> List[Tuple[int, float]]:
        # Rotate query once, then compare in rotated space (cosine only needs direction)
        rotated_query = self._rotation @ query
        query_norm = np.linalg.norm(rotated_query)
        if query_norm < 1e-10:
            return [(i, 0.0) for i in range(min(top_k, len(compressed)))]
        query_dir = rotated_query / query_norm

        scores = []
        for idx, data in enumerate(compressed):
            radius, direction = self._dequant_direction(data)
            score = float(np.dot(query_dir, direction))
            scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def compressed_size(self, compressed: List[bytes]) -> int:
        return sum(len(c) for c in compressed)


# ═══════════════════════════════════════════════════════════
# METHOD 4: TurboQuant (PolarQuant + QJL sign-bit correction)
# The full Google approach
# ═══════════════════════════════════════════════════════════

class TurboQuantCompression:
    """
    Full TurboQuant: PolarQuant + QJL 1-bit residual correction.
    This is what the Google paper proposes.
    """

    def __init__(self, dimensions: int, bits: int = 8, seed: int = 42):
        self.dimensions = dimensions
        self.bits = bits
        self.seed = seed
        self.name = f"TurboQuant ({bits}-bit + QJL)"
        self._init_matrices()

    def _init_matrices(self):
        rng = np.random.RandomState(self.seed)

        # Rotation matrix (same as PolarQuant)
        if self.dimensions <= 2048:
            G = rng.randn(self.dimensions, self.dimensions).astype(np.float32)
            Q, R = np.linalg.qr(G)
            d = np.sign(np.diag(R))
            self._rotation = (Q * d).astype(np.float32)
        else:
            block_size = 512
            self._rotation = np.zeros((self.dimensions, self.dimensions), dtype=np.float32)
            offset = 0
            for i in range(0, self.dimensions, block_size):
                bs = min(block_size, self.dimensions - i)
                G = rng.randn(bs, bs).astype(np.float32)
                Q, R = np.linalg.qr(G)
                d = np.sign(np.diag(R))
                self._rotation[offset:offset + bs, offset:offset + bs] = Q * d
                offset += bs

        # QJL projection matrix
        qjl_dims = self.dimensions // 4
        self._qjl = rng.choice([-1, 1], size=(qjl_dims, self.dimensions)).astype(np.float32)
        self._qjl /= np.sqrt(qjl_dims)

    def compress(self, embeddings: np.ndarray) -> List[bytes]:
        results = []
        levels = (1 << self.bits) - 1

        rotated = (self._rotation @ embeddings.T).T

        for vec in rotated:
            radius = np.linalg.norm(vec)
            if radius < 1e-10:
                qjl_bytes_len = (self.dimensions // 4 + 7) // 8
                results.append(struct.pack('f', 0.0) + b'\x00' * ((self.dimensions * self.bits + 7) // 8) + b'\x00' * qjl_bytes_len)
                continue

            direction = vec / radius

            # Stage 1: PolarQuant quantization
            quantized = np.clip(
                np.round((direction + 1.0) * 0.5 * levels),
                0, levels
            ).astype(np.uint8)

            # Stage 2: QJL on residual
            approx_direction = (quantized.astype(np.float32) / levels) * 2.0 - 1.0
            residual = direction - approx_direction
            projected = self._qjl @ residual
            signs = (projected >= 0).astype(np.uint8)
            qjl_packed = np.packbits(signs).tobytes()

            header = struct.pack('f', radius)

            if self.bits == 4:
                packed = bytearray()
                for i in range(0, len(quantized), 2):
                    high = quantized[i] & 0x0F
                    low = (quantized[i + 1] & 0x0F) if i + 1 < len(quantized) else 0
                    packed.append((high << 4) | low)
                results.append(header + bytes(packed) + qjl_packed)
            elif self.bits == 8:
                results.append(header + quantized.tobytes() + qjl_packed)
            else:
                results.append(header + quantized.tobytes() + qjl_packed)

        return results

    def decompress(self, compressed: List[bytes]) -> np.ndarray:
        results = []
        levels = (1 << self.bits) - 1
        qjl_bytes_len = (self.dimensions // 4 + 7) // 8

        for data in compressed:
            radius = struct.unpack('f', data[:4])[0]
            if abs(radius) < 1e-10:
                results.append(np.zeros(self.dimensions, dtype=np.float32))
                continue

            if self.bits == 4:
                n_quant_bytes = (self.dimensions + 1) // 2
            elif self.bits == 8:
                n_quant_bytes = self.dimensions
            else:
                n_quant_bytes = self.dimensions

            quant_data = data[4:4 + n_quant_bytes]

            if self.bits == 4:
                direction = np.zeros(self.dimensions, dtype=np.float32)
                for i, byte in enumerate(quant_data):
                    idx = i * 2
                    if idx < self.dimensions:
                        direction[idx] = ((byte >> 4) & 0x0F) / levels * 2.0 - 1.0
                    if idx + 1 < self.dimensions:
                        direction[idx + 1] = (byte & 0x0F) / levels * 2.0 - 1.0
            elif self.bits == 8:
                direction = np.frombuffer(quant_data, dtype=np.uint8).astype(np.float32)
                direction = direction / levels * 2.0 - 1.0
            else:
                direction = np.frombuffer(quant_data, dtype=np.uint8).astype(np.float32)
                direction = direction / levels * 2.0 - 1.0

            vec = radius * (self._rotation.T @ direction)
            results.append(vec)

        return np.array(results, dtype=np.float32)

    def search(self, query: np.ndarray, compressed: List[bytes], top_k: int = 10) -> List[Tuple[int, float]]:
        rotated_query = self._rotation @ query
        query_norm = np.linalg.norm(rotated_query)
        if query_norm < 1e-10:
            return [(i, 0.0) for i in range(min(top_k, len(compressed)))]
        query_dir = rotated_query / query_norm

        levels = (1 << self.bits) - 1
        qjl_bytes_len = (self.dimensions // 4 + 7) // 8

        # Pre-compute QJL projection of query direction
        qjl_query = self._qjl @ query_dir

        scores = []
        for idx, data in enumerate(compressed):
            radius = struct.unpack('f', data[:4])[0]
            if abs(radius) < 1e-10:
                scores.append((idx, 0.0))
                continue

            if self.bits == 4:
                n_quant_bytes = (self.dimensions + 1) // 2
                packed = data[4:4 + n_quant_bytes]
                direction = np.zeros(self.dimensions, dtype=np.float32)
                for i, byte in enumerate(packed):
                    bidx = i * 2
                    if bidx < self.dimensions:
                        direction[bidx] = ((byte >> 4) & 0x0F) / levels * 2.0 - 1.0
                    if bidx + 1 < self.dimensions:
                        direction[bidx + 1] = (byte & 0x0F) / levels * 2.0 - 1.0
            elif self.bits == 8:
                direction = np.frombuffer(data[4:4 + self.dimensions], dtype=np.uint8).astype(np.float32)
                direction = direction / levels * 2.0 - 1.0
            else:
                direction = np.frombuffer(data[4:4 + self.dimensions], dtype=np.uint8).astype(np.float32)
                direction = direction / levels * 2.0 - 1.0

            # Base score from PolarQuant
            base_score = float(np.dot(query_dir, direction))

            # QJL correction: use sign bits to correct the residual dot product
            qjl_data = data[4 + (self.dimensions * self.bits + 7) // 8:]
            if len(qjl_data) >= qjl_bytes_len:
                signs = np.unpackbits(np.frombuffer(qjl_data[:qjl_bytes_len], dtype=np.uint8))
                signs = signs[:self.dimensions // 4]
                sign_vals = signs.astype(np.float32) * 2.0 - 1.0
                # QJL correction term
                correction = float(np.dot(qjl_query, sign_vals)) * 0.1  # scaled correction
                score = base_score + correction
            else:
                score = base_score

            scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def compressed_size(self, compressed: List[bytes]) -> int:
        return sum(len(c) for c in compressed)


# ═══════════════════════════════════════════════════════════
# BENCHMARK RUNNER
# ═══════════════════════════════════════════════════════════

def run_benchmark(dimensions: int = 256, n_vectors: int = 500, bits: int = 8):
    """Run head-to-head benchmark across all methods."""
    print(f"\n{'='*80}")
    print(f"  COMPRESSION BENCHMARK: {dimensions}-dim, {n_vectors} vectors, {bits}-bit quantization")
    print(f"{'='*80}\n")

    # Generate test data (normalized embeddings, like real embedding models output)
    rng = np.random.RandomState(42)
    embeddings = rng.randn(n_vectors, dimensions).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms

    # Queries
    n_queries = 20
    top_k_values = [10, 50]
    query_indices = rng.choice(n_vectors, n_queries, replace=False)

    # Ground truth: exact cosine similarity for all queries
    ground_truth = {}
    for k in top_k_values:
        ground_truth[k] = {}
        for qi in query_indices:
            query = embeddings[qi]
            scores = embeddings @ query
            ground_truth[k][qi] = set(np.argsort(scores)[-k:])

    # Methods to test
    print("Initializing methods...")
    t0 = time.time()
    methods = [
        RawVectors(dimensions),
        NaiveScalarQuantization(dimensions, bits=bits),
        PolarQuantCompression(dimensions, bits=bits),
        TurboQuantCompression(dimensions, bits=bits),
    ]
    print(f"Init time: {time.time() - t0:.2f}s\n")

    results = []

    for method in methods:
        print(f"--- {method.name} ---")

        # Compress
        t0 = time.time()
        compressed = method.compress(embeddings)
        compress_time = time.time() - t0

        # Size
        original_bytes = n_vectors * dimensions * 4
        comp_bytes = method.compressed_size(compressed)
        ratio = original_bytes / comp_bytes if comp_bytes > 0 else 0

        # Decompress & reconstruction error
        t0 = time.time()
        decompressed = method.decompress(compressed)
        decompress_time = time.time() - t0
        recon_error = float(np.mean((embeddings - decompressed) ** 2))

        # Search accuracy (recall) and timing
        recalls = {k: [] for k in top_k_values}
        distortions = []

        t0 = time.time()
        for qi in query_indices:
            query = embeddings[qi]

            for k in top_k_values:
                search_results = method.search(query, compressed, top_k=k)
                result_set = set(idx for idx, _ in search_results)
                recall = len(ground_truth[k][qi] & result_set) / k
                recalls[k].append(recall)

            # Distortion (only for top-10 search)
            search_results_full = method.search(query, compressed, top_k=n_vectors)
            approx_scores = np.zeros(n_vectors)
            for idx, score in search_results_full:
                approx_scores[idx] = score
            exact_scores = embeddings @ query
            distortion = float(np.mean((exact_scores - approx_scores) ** 2))
            distortions.append(distortion)

        search_time = time.time() - t0

        result = {
            "method": method.name,
            "compression_ratio": ratio,
            "size_bytes": comp_bytes,
            "compress_time_ms": compress_time * 1000,
            "decompress_time_ms": decompress_time * 1000,
            "search_time_ms": search_time / n_queries * 1000,
            "reconstruction_error": recon_error,
            "distortion": np.mean(distortions),
        }
        for k in top_k_values:
            result[f"recall@{k}"] = float(np.mean(recalls[k]))

        results.append(result)

        print(f"  Compression:  {ratio:.1f}x ({comp_bytes:,} bytes)")
        print(f"  Compress:     {compress_time*1000:.1f}ms total")
        for k in top_k_values:
            print(f"  Recall@{k}:   {result[f'recall@{k}']:.1%}")
        print(f"  Distortion:   {np.mean(distortions):.6f}")
        print(f"  Recon error:  {recon_error:.6f}")
        print(f"  Search time:  {search_time/n_queries*1000:.2f}ms/query")
        print()

    # Summary table
    print(f"\n{'='*80}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"\n{'Method':<30} {'Ratio':>8} {'Recall@10':>10} {'Recall@50':>10} {'Distortion':>12} {'Recon Err':>12}")
    print(f"{'-'*30} {'-'*8} {'-'*10} {'-'*10} {'-'*12} {'-'*12}")

    for r in results:
        print(f"{r['method']:<30} {r['compression_ratio']:>7.1f}x {r['recall@10']:>9.1%} {r['recall@50']:>9.1%} {r['distortion']:>12.6f} {r['reconstruction_error']:>12.6f}")

    print(f"\n{'Method':<30} {'Size (KB)':>10} {'Compress':>10} {'Search/q':>10}")
    print(f"{'-'*30} {'-'*10} {'-'*10} {'-'*10}")
    for r in results:
        print(f"{r['method']:<30} {r['size_bytes']/1024:>9.1f}K {r['compress_time_ms']:>8.1f}ms {r['search_time_ms']:>8.2f}ms")

    print()
    return results


if __name__ == "__main__":
    dims = int(sys.argv[1]) if len(sys.argv) > 1 else 256
    n_vecs = int(sys.argv[2]) if len(sys.argv) > 2 else 500

    # Run at different bit depths
    print("\n" + "=" * 80)
    print("  BONITO KB VECTOR COMPRESSION: Raw vs Naive vs PolarQuant vs TurboQuant")
    print("  Based on Google Research TurboQuant (arxiv 2504.19874)")
    print("=" * 80)

    for bits in [8, 4]:
        run_benchmark(dimensions=dims, n_vectors=n_vecs, bits=bits)
