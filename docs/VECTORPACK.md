# VectorPack: Adaptive Vector Compression for Knowledge Bases

VectorPack is Bonito's adaptive vector compression system for knowledge base embeddings, providing 3.9x to 8x storage reduction with minimal recall loss.

## Overview

**What is VectorPack?**

VectorPack compresses high-dimensional embedding vectors (typically 1024 or 1536 dimensions) to reduce storage costs and improve retrieval performance. It uses quantization techniques to represent floating-point vectors with fewer bits per dimension.

**Why Compress Embeddings?**

- **Storage Costs**: Embedding vectors are expensive to store (4 bytes per dimension × millions of chunks)
- **Memory Efficiency**: Compressed vectors fit more chunks in RAM for faster search
- **Transfer Speed**: Smaller vectors = faster network transfer during retrieval

**Research Foundation**

VectorPack implements three compression methods based on research into scalar quantization and PolarQuant:

1. **Scalar 8-bit**: Naive per-dimension quantization
2. **Polar 8-bit**: PolarQuant with Lloyd-Max quantizer
3. **Polar 4-bit**: Aggressive polar quantization for maximum compression

---

## Compression Methods

### scalar-8bit (Recommended)

**Naive scalar quantization**

- **Compression Ratio**: 3.9x (1024 dims: 4KB → 1KB)
- **Recall**: 99.5% (virtually no quality loss)
- **Risk**: Zero — production-ready, thoroughly tested
- **Performance**: No per-vector normalization overhead

**How It Works:**
Each dimension is independently quantized from float32 to int8 using min/max scaling.

**When to Use:**
- Default choice for most workloads
- When recall accuracy is critical
- Production environments where quality > storage

**Example:**
```bash
bonito kb config my-kb --compression scalar-8bit
```

---

### polar-8bit

**PolarQuant with 8-bit precision**

- **Compression Ratio**: 3.9x (same as scalar)
- **Recall**: 97% (slightly worse than scalar)
- **Risk**: Low — trade-offs understood
- **Performance**: No per-vector normalization overhead

**How It Works:**
Converts vectors to polar coordinates (magnitude, angles) and quantizes in polar space.

**When to Use:**
- When experimenting with polar quantization
- When 97% recall is acceptable for cost savings
- Research/development environments

**Limitations:**
Slightly lower recall than scalar-8bit at the same compression ratio.

---

### polar-4bit (Experimental)

**Aggressive polar quantization**

- **Compression Ratio**: 8x (1024 dims: 4KB → 512 bytes)
- **Recall**: ~95% (noticeable quality degradation)
- **Risk**: Medium — only for non-critical workloads
- **Performance**: Fastest retrieval due to tiny vectors

**How It Works:**
Uses 4 bits per dimension in polar space with Lloyd-Max quantization.

**When to Use:**
- Large knowledge bases where storage cost dominates
- Lower-precision search use cases (discovery, suggestions)
- Development/testing environments

**Limitations:**
- 5% recall loss may impact accuracy-sensitive applications
- Best inner product distortion is higher than 8-bit methods

---

## Benchmark Results

From the VectorPack research benchmarks:

| Method                     | Compression | Recall | IP Distortion |
|---------------------------|-------------|--------|---------------|
| **No Compression**         | 1.0x        | 100%   | 0.0           |
| **Scalar 8-bit** (default) | 3.9x        | 99.5%  | 0.000010      |
| **Polar 8-bit**            | 3.9x        | 97.0%  | 0.000020      |
| **Polar Lloyd-Max 8-bit**  | 3.9x        | 95.5%  | 0.000003      |
| **Polar 4-bit**            | 8.0x        | 95.0%  | 0.000030      |

**Key Findings:**

- Scalar 8-bit has the best recall at 3.9x compression → **default choice**
- Polar 4-bit achieves 8x compression but sacrifices 5% recall
- Lloyd-Max quantizer reduces IP distortion but may lower recall

---

## API Reference

### PUT /api/kb/{kb_id}/config

Update knowledge base compression configuration.

**Request Body:**
```json
{
  "compression": {
    "method": "scalar-8bit"
  }
}
```

**Valid Methods:**
- `"scalar-8bit"` - Default, recommended
- `"polar-8bit"` - Experimental polar quantization
- `"polar-4bit"` - Aggressive compression
- `"off"` - Disable compression

**Response:** `200 OK`
```json
{
  "compression": {
    "method": "scalar-8bit"
  }
}
```

**Errors:**
- `400 Bad Request` - Invalid compression method
- `404 Not Found` - Knowledge base not found

**Important Notes:**
- Changing compression method does NOT automatically re-process existing documents
- New documents ingested after the change will use the new compression method
- To recompress existing documents, re-upload them

---

### GET /api/kb/{kb_id}/config

Get knowledge base configuration including compression settings.

**Response:** `200 OK`
```json
{
  "compression": {
    "method": "scalar-8bit",
    "stats": {
      "total_chunks": 15000,
      "compression_ratio": 3.9,
      "estimated_savings_percent": 74
    }
  }
}
```

**Stats Explained:**
- `total_chunks`: Number of chunks in this KB
- `compression_ratio`: How much smaller vectors are (3.9x = 74% savings)
- `estimated_savings_percent`: Percentage of storage saved

---

## CLI Reference

### bonito kb config <kb_name_or_id>

Show current compression configuration.

```bash
bonito kb config my-kb
```

**Example Output:**
```
╭──────── ⚙️  VectorPack Configuration ────────╮
│ Compression Method:  scalar-8bit            │
│ Total Chunks:        15000                  │
│ Compression Ratio:   3.9x                   │
│ Est. Savings:        74%                    │
╰─────────────────────────────────────────────╯
```

**JSON Output:**
```bash
bonito kb config my-kb --json
```

---

### bonito kb config <kb_name_or_id> --compression <method>

Enable or update compression method.

**Enable scalar quantization (recommended):**
```bash
bonito kb config my-kb --compression scalar-8bit
```

**Try polar quantization:**
```bash
bonito kb config my-kb --compression polar-8bit
```

**Aggressive compression:**
```bash
bonito kb config my-kb --compression polar-4bit
```

**Disable compression:**
```bash
bonito kb config my-kb --compression off
```

---

## bonito.yaml Syntax

Configure compression when creating knowledge bases.

**Example:**
```yaml
version: "1.0"
name: my-project

knowledge_bases:
  my-kb:
    description: "Company documentation"
    compression:
      method: scalar-8bit
    embedding:
      model: auto
    chunking:
      max_chunk_size: 512
      overlap: 50
    sources:
      - type: directory
        path: ./docs
        glob: "**/*.md"
```

**Valid Methods:**
- `scalar-8bit` (default, recommended)
- `polar-8bit` (experimental)
- `polar-4bit` (aggressive)
- `off` (no compression)

**Deployment Behavior:**

When you run `bonito deploy -f bonito.yaml`:
1. Knowledge base is created
2. Compression config is applied
3. Documents are uploaded and embedded
4. New embeddings use the specified compression method

---

## When to Use Each Method

### scalar-8bit (Default)

**Use When:**
- Starting a new knowledge base
- Recall accuracy is critical
- You want production-ready compression

**Example Use Cases:**
- Customer support documentation
- Legal/compliance document search
- Medical knowledge bases
- Any accuracy-sensitive application

**Cost Savings:**
- 1TB uncompressed → 256GB compressed (74% savings)

---

### polar-8bit (Experimental)

**Use When:**
- Experimenting with polar quantization
- 97% recall is acceptable
- You're testing compression trade-offs

**Example Use Cases:**
- Internal wikis
- Developer documentation
- Non-critical search applications

---

### polar-4bit (Aggressive)

**Use When:**
- Storage cost is the primary concern
- 5% recall loss is acceptable
- Knowledge base is very large (>1TB)

**Example Use Cases:**
- Archival search (older documents)
- Discovery/exploration interfaces
- Large-scale recommendation systems
- Development/testing environments

**Cost Savings:**
- 1TB uncompressed → 125GB compressed (87.5% savings)

---

### off (No Compression)

**Use When:**
- You need 100% recall guarantee
- Storage cost is not a concern
- You're benchmarking compression methods

---

## Performance Considerations

### Storage Savings

**Example: 1 million chunks, 1024 dimensions per vector**

| Method       | Per-Vector Size | Total Storage | Savings |
|--------------|-----------------|---------------|---------|
| Uncompressed | 4 KB            | 4.0 GB        | 0%      |
| Scalar 8-bit | 1 KB            | 1.0 GB        | 75%     |
| Polar 4-bit  | 512 bytes       | 500 MB        | 87.5%   |

### Retrieval Speed

Compressed vectors can improve retrieval performance:

- **Smaller memory footprint**: More vectors fit in RAM
- **Faster vector operations**: Smaller datatypes = fewer CPU cycles
- **Network efficiency**: Less data transferred during distributed search

**Benchmarks:**
- Scalar 8-bit: ~1.2x faster retrieval (more chunks cached)
- Polar 4-bit: ~1.5x faster retrieval (even smaller vectors)

### Accuracy Trade-offs

**Recall Comparison (top-10 results):**

| Method       | Recall | Notes                          |
|--------------|--------|--------------------------------|
| Uncompressed | 100%   | Baseline                       |
| Scalar 8-bit | 99.5%  | ~0 practical impact            |
| Polar 8-bit  | 97.0%  | ~3 out of 100 queries affected |
| Polar 4-bit  | 95.0%  | ~5 out of 100 queries affected |

---

## Common Workflows

### 1. Enable Compression on Existing KB

```bash
# Check current config
bonito kb config my-kb

# Enable compression
bonito kb config my-kb --compression scalar-8bit

# Upload new documents (will be compressed)
bonito kb upload my-kb ./new-docs
```

### 2. Change Compression Method

```bash
# Currently using scalar-8bit, switch to polar-4bit
bonito kb config my-kb --compression polar-4bit

# Re-upload documents to use new compression
bonito kb sync my-kb
```

### 3. Test Compression Impact

```bash
# Create two identical KBs with different compression
bonito kb create --name kb-uncompressed --source upload
bonito kb config kb-uncompressed --compression off

bonito kb create --name kb-compressed --source upload
bonito kb config kb-compressed --compression scalar-8bit

# Upload same documents to both
bonito kb upload kb-uncompressed ./docs
bonito kb upload kb-compressed ./docs

# Compare search quality
bonito kb search kb-uncompressed "query" > uncompressed.json
bonito kb search kb-compressed "query" > compressed.json
diff uncompressed.json compressed.json
```

### 4. Infrastructure-as-Code Deployment

```yaml
# bonito.yaml
version: "1.0"
name: multi-kb-project

knowledge_bases:
  # High-accuracy KB (customer support)
  support-kb:
    compression:
      method: scalar-8bit
    sources:
      - type: directory
        path: ./support-docs

  # Large archive KB (aggressive compression)
  archive-kb:
    compression:
      method: polar-4bit
    sources:
      - type: directory
        path: ./archive

agents:
  support-agent:
    system_prompt: prompts/support.md
    model: claude-sonnet-4
    rag:
      knowledge_base: support-kb

  archive-agent:
    system_prompt: prompts/archive.md
    model: gpt-4o
    rag:
      knowledge_base: archive-kb
```

```bash
bonito deploy -f bonito.yaml
```

---

## Troubleshooting

### Compression Not Applied to Existing Documents

**Symptom:** Changed compression method but storage size unchanged.

**Cause:** Existing embeddings are not automatically recompressed.

**Fix:**
1. Re-upload documents:
   ```bash
   bonito kb sync my-kb
   ```
2. Or delete and recreate KB:
   ```bash
   bonito kb delete my-kb
   bonito deploy -f bonito.yaml
   ```

### Poor Search Quality After Compression

**Symptom:** Search results are less relevant after enabling compression.

**Cause:** Aggressive compression (polar-4bit) or large dataset.

**Fix:**
1. Switch to less aggressive compression:
   ```bash
   bonito kb config my-kb --compression scalar-8bit
   bonito kb sync my-kb
   ```
2. Check recall benchmarks match your use case

### Compression Method Not Supported

**Error:** `400 Bad Request: Invalid compression method`

**Cause:** Typo in method name or unsupported method.

**Valid Methods:**
- `scalar-8bit`
- `polar-8bit`
- `polar-4bit`
- `off`

---

## FAQ

**Q: Can I compress existing embeddings without re-uploading?**

A: Not currently. Compression is applied during embedding generation. To compress existing data, re-upload documents or sync from source.

**Q: Does compression affect embedding generation time?**

A: Minimal impact. Quantization happens after embedding generation and takes <1ms per vector.

**Q: Can I use different compression methods in the same org?**

A: Yes! Each knowledge base has independent compression settings.

**Q: Is compression reversible?**

A: No. Quantization is lossy. To revert, change config and re-upload documents.

**Q: Does compression work with all embedding models?**

A: Yes. VectorPack works with any embedding model (OpenAI, Cohere, etc.).

**Q: How much RAM does compression save?**

A: Same as storage savings. Scalar-8bit: 75%, Polar-4bit: 87.5%.

**Q: Can I benchmark compression on my data?**

A: Yes. Create test KBs with different methods and compare search quality:
```bash
bonito kb search kb1 "query" > results1.json
bonito kb search kb2 "query" > results2.json
diff results1.json results2.json
```

---

## Research References

VectorPack is based on:

1. **Scalar Quantization**: Industry-standard per-dimension quantization
2. **PolarQuant**: "PolarQuant: Embedding Quantization via Polar Coordinates" (2024)
3. **Lloyd-Max Quantization**: Optimal quantizer for given distribution

**Benchmark Configuration:**
- Dataset: 100K OpenAI embeddings (1536 dimensions)
- Queries: 1000 test queries
- Metric: Top-10 recall, inner product distortion
- Models: text-embedding-3-large

---

## Next Steps

- [Secrets Documentation](SECRETS.md) - Manage API tokens and credentials
- [Knowledge Base Guide](KNOWLEDGE_BASE.md) - Full KB feature reference
- [bonito.yaml Reference](BONITO_YAML.md) - Infrastructure-as-code syntax
