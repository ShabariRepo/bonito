#!/usr/bin/env python3
"""
LOCOMO Benchmark Harness for Bonobot Memory System

Tests both vector-only and graph+vector fusion approaches on the LOCOMO
long-term conversational memory benchmark.
"""

import asyncio
import json
import sys
import os
import time
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path

# Add the backend to Python path to import Bonobot modules
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from tqdm import tqdm

# For graph+vector fusion
import networkx as nx
import re
from collections import defaultdict, Counter

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryEntry:
    """Represents a single memory entry."""
    
    def __init__(self, content: str, memory_type: str = "interaction", 
                 importance_score: float = 1.0, session_id: str = None,
                 dialogue_id: str = None, timestamp: str = None):
        self.content = content
        self.memory_type = memory_type
        self.importance_score = importance_score
        self.session_id = session_id
        self.dialogue_id = dialogue_id
        self.timestamp = timestamp
        self.embedding = None
        self.entities = set()
        self.access_count = 0
        
    def __repr__(self):
        return f"MemoryEntry(type={self.memory_type}, content='{self.content[:50]}...')"


class VectorMemorySystem:
    """Current Bonobot vector-only memory system simulation."""
    
    def __init__(self):
        print("Loading sentence transformer model...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.memories: List[MemoryEntry] = []
        self.memory_embeddings = None
        
    def store_memory(self, memory: MemoryEntry):
        """Store a memory with vector embedding."""
        memory.embedding = self.encoder.encode(memory.content)
        self.memories.append(memory)
        
        # Rebuild embeddings matrix
        self._rebuild_embeddings()
        
    def _rebuild_embeddings(self):
        """Rebuild the embeddings matrix."""
        if self.memories:
            self.memory_embeddings = np.array([m.embedding for m in self.memories])
    
    def search_memories(self, query: str, limit: int = 10) -> List[Tuple[MemoryEntry, float]]:
        """Search memories using vector similarity."""
        if not self.memories:
            return []
            
        query_embedding = self.encoder.encode(query)
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1), 
            self.memory_embeddings
        ).flatten()
        
        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:limit]
        results = []
        
        for idx in top_indices:
            memory = self.memories[idx]
            memory.access_count += 1
            results.append((memory, float(similarities[idx])))
            
        return results


class GraphVectorFusionSystem:
    """Graph+Vector fusion prototype inspired by Memwright."""
    
    def __init__(self):
        print("Loading sentence transformer model for fusion system...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.memories: List[MemoryEntry] = []
        self.memory_embeddings = None
        self.entity_graph = nx.Graph()
        self.entity_to_memories = defaultdict(set)
        self.keyword_index = defaultdict(set)
        
    def _extract_entities(self, text: str) -> set:
        """Simple entity extraction using regex patterns."""
        entities = set()
        
        # Extract names (capitalized words, 2-15 chars)
        names = re.findall(r'\b[A-Z][a-z]{1,14}\b', text)
        entities.update(names)
        
        # Extract dates
        dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}\b|\b\w+\s+\d{1,2},?\s+\d{4}\b', text)
        entities.update(dates)
        
        # Extract locations (words ending in common location suffixes)
        locations = re.findall(r'\b\w+(?:town|city|ville|berg|burg|field|ford|land|wood|port|gate|hill)\b', text, re.IGNORECASE)
        entities.update(locations)
        
        # Extract topics (education-related terms, emotions, activities)
        topics = re.findall(r'\b(?:education|school|college|university|job|career|painting|art|therapy|counseling|support|group|race|charity|camping|swimming)\b', text, re.IGNORECASE)
        entities.update(topics)
        
        return {e.lower() for e in entities if len(e) > 2}
    
    def _build_keyword_index(self, memory: MemoryEntry):
        """Build keyword index for tag/keyword matching."""
        words = re.findall(r'\b\w+\b', memory.content.lower())
        for word in words:
            if len(word) > 3:  # Skip short words
                self.keyword_index[word].add(len(self.memories) - 1)
    
    def _update_entity_graph(self, memory: MemoryEntry):
        """Update entity graph with new memory."""
        entities = list(memory.entities)
        
        # Add entities to graph
        for entity in entities:
            if entity not in self.entity_graph:
                self.entity_graph.add_node(entity)
            self.entity_to_memories[entity].add(len(self.memories) - 1)
        
        # Connect entities that appear in the same memory
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                if self.entity_graph.has_edge(entity1, entity2):
                    self.entity_graph[entity1][entity2]['weight'] += 1
                else:
                    self.entity_graph.add_edge(entity1, entity2, weight=1)
    
    def store_memory(self, memory: MemoryEntry):
        """Store a memory with vector embedding and entity extraction."""
        # Extract entities
        memory.entities = self._extract_entities(memory.content)
        
        # Generate embedding
        memory.embedding = self.encoder.encode(memory.content)
        
        # Store memory
        self.memories.append(memory)
        
        # Update indices
        self._build_keyword_index(memory)
        self._update_entity_graph(memory)
        
        # Rebuild embeddings matrix
        self._rebuild_embeddings()
    
    def _rebuild_embeddings(self):
        """Rebuild the embeddings matrix."""
        if self.memories:
            self.memory_embeddings = np.array([m.embedding for m in self.memories])
    
    def _keyword_search(self, query: str) -> List[int]:
        """Layer 1: Keyword/tag matching."""
        query_words = re.findall(r'\b\w+\b', query.lower())
        matching_memory_ids = set()
        
        for word in query_words:
            if word in self.keyword_index:
                matching_memory_ids.update(self.keyword_index[word])
        
        return list(matching_memory_ids)
    
    def _graph_expansion(self, query: str, max_hops: int = 2) -> List[int]:
        """Layer 2: Graph expansion via BFS."""
        query_entities = self._extract_entities(query)
        expanded_memory_ids = set()
        
        # Start with direct entity matches
        for entity in query_entities:
            if entity in self.entity_to_memories:
                expanded_memory_ids.update(self.entity_to_memories[entity])
        
        # Expand via graph traversal
        visited_entities = set()
        for hop in range(max_hops):
            current_entities = query_entities - visited_entities
            if not current_entities:
                break
                
            next_entities = set()
            for entity in current_entities:
                if entity in self.entity_graph:
                    neighbors = list(self.entity_graph.neighbors(entity))
                    next_entities.update(neighbors)
                    
                    # Add memories of neighbor entities
                    for neighbor in neighbors:
                        if neighbor in self.entity_to_memories:
                            expanded_memory_ids.update(self.entity_to_memories[neighbor])
            
            visited_entities.update(current_entities)
            query_entities.update(next_entities)
        
        return list(expanded_memory_ids)
    
    def _vector_search(self, query: str, limit: int = 20) -> List[Tuple[int, float]]:
        """Layer 3: Vector similarity search."""
        if not self.memories:
            return []
            
        query_embedding = self.encoder.encode(query)
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1), 
            self.memory_embeddings
        ).flatten()
        
        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:limit]
        return [(int(idx), float(similarities[idx])) for idx in top_indices]
    
    def _temporal_boost(self, memory_ids: List[int], memory_scores: Dict[int, float], max_boost: float = 0.2, decay_days: int = 90) -> Dict[int, float]:
        """Apply temporal boosting - more recent memories get higher scores."""
        current_time = datetime.now()
        
        for mem_id in memory_ids:
            if mem_id < len(self.memories):
                memory = self.memories[mem_id]
                
                # Simple temporal boost based on access count (proxy for recency)
                boost = max_boost * min(1.0, memory.access_count / 5.0)
                memory_scores[mem_id] = memory_scores.get(mem_id, 0.0) + boost
                
        return memory_scores
    
    def _reciprocal_rank_fusion(self, keyword_results: List[int], 
                               graph_results: List[int], 
                               vector_results: List[Tuple[int, float]], 
                               k: int = 60) -> List[Tuple[int, float]]:
        """Combine results using Reciprocal Rank Fusion."""
        rrf_scores = defaultdict(float)
        
        # Layer 1: Keyword scores
        for rank, mem_id in enumerate(keyword_results):
            rrf_scores[mem_id] += 1.0 / (k + rank + 1)
        
        # Layer 2: Graph expansion scores
        for rank, mem_id in enumerate(graph_results):
            rrf_scores[mem_id] += 1.0 / (k + rank + 1)
        
        # Layer 3: Vector scores (already similarity-weighted)
        for rank, (mem_id, similarity) in enumerate(vector_results):
            rrf_scores[mem_id] += similarity / (k + rank + 1)
        
        # Apply temporal boost
        memory_scores = dict(rrf_scores)
        memory_scores = self._temporal_boost(list(memory_scores.keys()), memory_scores)
        
        # Sort by final score
        ranked_results = sorted(memory_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked_results
    
    def search_memories(self, query: str, limit: int = 10, token_budget: int = 1000) -> List[Tuple[MemoryEntry, float]]:
        """Search memories using 3-layer graph+vector fusion."""
        if not self.memories:
            return []
        
        # Layer 1: Keyword search
        keyword_results = self._keyword_search(query)
        
        # Layer 2: Graph expansion
        graph_results = self._graph_expansion(query)
        
        # Layer 3: Vector search
        vector_results = self._vector_search(query, limit=20)
        
        # Fuse results using RRF
        fused_results = self._reciprocal_rank_fusion(
            keyword_results, graph_results, vector_results
        )
        
        # Apply token budget constraint (greedy selection)
        selected_results = []
        total_tokens = 0
        
        for mem_id, score in fused_results[:limit]:
            if mem_id < len(self.memories):
                memory = self.memories[mem_id]
                memory_tokens = len(memory.content.split())  # Simple token estimation
                
                if total_tokens + memory_tokens <= token_budget:
                    memory.access_count += 1
                    selected_results.append((memory, score))
                    total_tokens += memory_tokens
                else:
                    break
        
        return selected_results


class LOCOMOBenchmark:
    """LOCOMO benchmark runner."""
    
    def __init__(self):
        self.locomo_data = None
        
    def load_data(self, data_path: str = "locomo10.json"):
        """Load LOCOMO benchmark data."""
        print(f"Loading LOCOMO data from {data_path}")
        with open(data_path, 'r') as f:
            self.locomo_data = json.load(f)
        print(f"Loaded {len(self.locomo_data)} conversation samples")
    
    def extract_conversation_memories(self, conversation: Dict[str, Any]) -> List[MemoryEntry]:
        """Extract memories from a conversation."""
        memories = []
        
        # Process each session
        session_keys = [k for k in conversation.keys() if k.startswith('session_') and not k.endswith('_date_time')]
        
        for session_key in sorted(session_keys):
            session_data = conversation[session_key]
            session_datetime = conversation.get(f"{session_key}_date_time", "")
            
            if not session_data:  # Some sessions are empty
                continue
                
            # Extract individual dialogue turns
            for turn in session_data:
                if isinstance(turn, dict) and 'text' in turn:
                    memory = MemoryEntry(
                        content=turn['text'],
                        memory_type="interaction",
                        importance_score=1.0,
                        session_id=session_key,
                        dialogue_id=turn.get('dia_id', ''),
                        timestamp=session_datetime
                    )
                    memories.append(memory)
        
        return memories
    
    def evaluate_retrieval(self, retrieved_memories: List[MemoryEntry], evidence_ids: List[str]) -> Tuple[float, float, float]:
        """Evaluate retrieval performance against ground truth evidence."""
        if not retrieved_memories or not evidence_ids:
            return 0.0, 0.0, 0.0
        
        # Extract dialogue IDs from retrieved memories
        retrieved_ids = set()
        for memory in retrieved_memories:
            if memory.dialogue_id:
                retrieved_ids.add(memory.dialogue_id)
        
        evidence_set = set(evidence_ids)
        
        # Calculate metrics
        if len(retrieved_ids) == 0:
            precision = 0.0
        else:
            precision = len(evidence_set & retrieved_ids) / len(retrieved_ids)
        
        if len(evidence_set) == 0:
            recall = 1.0  # Perfect recall if no evidence needed
        else:
            recall = len(evidence_set & retrieved_ids) / len(evidence_set)
        
        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)
        
        return precision, recall, f1
    
    def run_benchmark(self, memory_system, sample_limit: int = None) -> Dict[str, Any]:
        """Run benchmark on a memory system."""
        if not self.locomo_data:
            raise ValueError("No LOCOMO data loaded")
        
        results = []
        total_retrieval_time = 0.0
        
        samples_to_test = self.locomo_data[:sample_limit] if sample_limit else self.locomo_data
        
        print(f"Running benchmark on {len(samples_to_test)} samples...")
        
        for sample_idx, sample in enumerate(tqdm(samples_to_test)):
            conversation = sample['conversation']
            qa_pairs = sample['qa']
            
            # Store conversation memories
            memories = self.extract_conversation_memories(conversation)
            for memory in memories:
                memory_system.store_memory(memory)
            
            # Test each QA pair
            sample_results = []
            for qa in qa_pairs:
                question = qa['question']
                evidence_ids = qa['evidence']
                
                # Retrieve memories
                start_time = time.time()
                retrieved = memory_system.search_memories(question, limit=10)
                retrieval_time = time.time() - start_time
                total_retrieval_time += retrieval_time
                
                # Evaluate
                retrieved_memories = [mem for mem, score in retrieved]
                precision, recall, f1 = self.evaluate_retrieval(retrieved_memories, evidence_ids)
                
                sample_results.append({
                    'question': question,
                    'evidence_ids': evidence_ids,
                    'retrieved_count': len(retrieved_memories),
                    'precision': precision,
                    'recall': recall,
                    'f1': f1,
                    'retrieval_time': retrieval_time
                })
            
            # Calculate sample-level metrics
            if sample_results:
                sample_precision = np.mean([r['precision'] for r in sample_results])
                sample_recall = np.mean([r['recall'] for r in sample_results])
                sample_f1 = np.mean([r['f1'] for r in sample_results])
                
                results.append({
                    'sample_id': sample_idx,
                    'num_questions': len(sample_results),
                    'precision': sample_precision,
                    'recall': sample_recall,
                    'f1': sample_f1,
                    'questions': sample_results
                })
        
        # Calculate overall metrics
        if results:
            overall_precision = np.mean([r['precision'] for r in results])
            overall_recall = np.mean([r['recall'] for r in results])
            overall_f1 = np.mean([r['f1'] for r in results])
            avg_retrieval_time = total_retrieval_time / sum(len(r['questions']) for r in results)
            
            # Token efficiency (total tokens retrieved per question)
            total_questions = sum(len(r['questions']) for r in results)
            total_tokens = sum(
                len(mem.content.split()) 
                for r in results 
                for q in r['questions'] 
                for mem in [memory_system.memories[i] for i in range(q['retrieved_count'])]
            ) if hasattr(memory_system, 'memories') and memory_system.memories else 0
            
            avg_tokens_per_question = total_tokens / total_questions if total_questions > 0 else 0
        else:
            overall_precision = overall_recall = overall_f1 = 0.0
            avg_retrieval_time = 0.0
            avg_tokens_per_question = 0.0
        
        return {
            'overall_precision': overall_precision,
            'overall_recall': overall_recall,
            'overall_f1': overall_f1,
            'avg_retrieval_time': avg_retrieval_time,
            'avg_tokens_per_question': avg_tokens_per_question,
            'total_questions': sum(len(r['questions']) for r in results),
            'results': results
        }


def main():
    """Main benchmark runner."""
    print("LOCOMO Memory Benchmark")
    print("=" * 50)
    
    # Initialize benchmark
    benchmark = LOCOMOBenchmark()
    benchmark.load_data()
    
    # Test on a subset first (to speed up testing)
    sample_limit = 3  # Use first 3 conversation samples for quick testing
    
    print(f"\nTesting on first {sample_limit} samples...")
    
    # Test 1: Vector-only system (current Bonobot approach)
    print("\n1. Testing Vector-Only Memory System")
    print("-" * 40)
    vector_system = VectorMemorySystem()
    vector_results = benchmark.run_benchmark(vector_system, sample_limit=sample_limit)
    
    print(f"Vector-Only Results:")
    print(f"  Precision: {vector_results['overall_precision']:.3f}")
    print(f"  Recall:    {vector_results['overall_recall']:.3f}")
    print(f"  F1:        {vector_results['overall_f1']:.3f}")
    print(f"  Avg Retrieval Time: {vector_results['avg_retrieval_time']:.4f}s")
    print(f"  Avg Tokens/Question: {vector_results['avg_tokens_per_question']:.1f}")
    
    # Test 2: Graph+Vector fusion system
    print("\n2. Testing Graph+Vector Fusion System")
    print("-" * 40)
    fusion_system = GraphVectorFusionSystem()
    fusion_results = benchmark.run_benchmark(fusion_system, sample_limit=sample_limit)
    
    print(f"Graph+Vector Fusion Results:")
    print(f"  Precision: {fusion_results['overall_precision']:.3f}")
    print(f"  Recall:    {fusion_results['overall_recall']:.3f}")
    print(f"  F1:        {fusion_results['overall_f1']:.3f}")
    print(f"  Avg Retrieval Time: {fusion_results['avg_retrieval_time']:.4f}s")
    print(f"  Avg Tokens/Question: {fusion_results['avg_tokens_per_question']:.1f}")
    
    # Comparison
    print("\n3. Comparison")
    print("-" * 40)
    precision_improvement = (fusion_results['overall_precision'] - vector_results['overall_precision']) / vector_results['overall_precision'] * 100 if vector_results['overall_precision'] > 0 else 0
    recall_improvement = (fusion_results['overall_recall'] - vector_results['overall_recall']) / vector_results['overall_recall'] * 100 if vector_results['overall_recall'] > 0 else 0
    f1_improvement = (fusion_results['overall_f1'] - vector_results['overall_f1']) / vector_results['overall_f1'] * 100 if vector_results['overall_f1'] > 0 else 0
    
    print(f"Improvements (Graph+Vector vs Vector-Only):")
    print(f"  Precision: {precision_improvement:+.1f}%")
    print(f"  Recall:    {recall_improvement:+.1f}%")
    print(f"  F1:        {f1_improvement:+.1f}%")
    
    # Save results
    results_data = {
        'benchmark_info': {
            'samples_tested': sample_limit,
            'total_questions': vector_results['total_questions'],
            'timestamp': datetime.now().isoformat()
        },
        'vector_only': vector_results,
        'graph_vector_fusion': fusion_results,
        'improvements': {
            'precision_pct': precision_improvement,
            'recall_pct': recall_improvement,
            'f1_pct': f1_improvement
        }
    }
    
    with open('benchmark_results.json', 'w') as f:
        json.dump(results_data, f, indent=2)
    
    # Generate markdown report
    generate_report(results_data)
    
    print(f"\nBenchmark complete! Results saved to benchmark_results.json and results.md")


def generate_report(results_data: Dict[str, Any]):
    """Generate markdown report."""
    
    report = f"""# LOCOMO Benchmark Results

Generated on: {results_data['benchmark_info']['timestamp']}

## Summary

This benchmark compares Bonobot's current vector-only memory approach against a prototype graph+vector fusion system on the LOCOMO conversational memory benchmark.

- **Samples tested**: {results_data['benchmark_info']['samples_tested']}
- **Total questions**: {results_data['benchmark_info']['total_questions']}

## Results

| Metric | Vector-Only | Graph+Vector Fusion | Improvement |
|--------|-------------|---------------------|-------------|
| Precision | {results_data['vector_only']['overall_precision']:.3f} | {results_data['graph_vector_fusion']['overall_precision']:.3f} | {results_data['improvements']['precision_pct']:+.1f}% |
| Recall | {results_data['vector_only']['overall_recall']:.3f} | {results_data['graph_vector_fusion']['overall_recall']:.3f} | {results_data['improvements']['recall_pct']:+.1f}% |
| F1 Score | {results_data['vector_only']['overall_f1']:.3f} | {results_data['graph_vector_fusion']['overall_f1']:.3f} | {results_data['improvements']['f1_pct']:+.1f}% |
| Avg Retrieval Time (s) | {results_data['vector_only']['avg_retrieval_time']:.4f} | {results_data['graph_vector_fusion']['avg_retrieval_time']:.4f} | {(results_data['graph_vector_fusion']['avg_retrieval_time'] - results_data['vector_only']['avg_retrieval_time']) / results_data['vector_only']['avg_retrieval_time'] * 100:+.1f}% |
| Avg Tokens/Question | {results_data['vector_only']['avg_tokens_per_question']:.1f} | {results_data['graph_vector_fusion']['avg_tokens_per_question']:.1f} | {(results_data['graph_vector_fusion']['avg_tokens_per_question'] - results_data['vector_only']['avg_tokens_per_question']) / results_data['vector_only']['avg_tokens_per_question'] * 100:+.1f}% |

## Analysis

### Vector-Only System (Current Bonobot)
- Uses sentence-transformers (all-MiniLM-L6-v2) for embeddings
- Simple cosine similarity matching
- Fast and straightforward

### Graph+Vector Fusion System (Prototype)
- **3-layer retrieval**:
  1. Keyword/tag matching
  2. Entity graph traversal (NetworkX BFS, 2 hops)
  3. Vector similarity search
- **Reciprocal Rank Fusion** combines results (k=60)
- **Temporal boost** (+0.2 max, access count based)
- **Token budget** constraint (1000 tokens max)

### Key Findings

{"🎯 **Performance**: " if results_data['improvements']['f1_pct'] > 0 else "⚠️ **Performance**: "}The graph+vector fusion approach {"improved" if results_data['improvements']['f1_pct'] > 0 else "did not improve"} overall F1 score by {abs(results_data['improvements']['f1_pct']):.1f}%.

{"⚡ **Speed**: " if results_data['graph_vector_fusion']['avg_retrieval_time'] <= results_data['vector_only']['avg_retrieval_time'] else "🐌 **Speed**: "}Retrieval latency {"improved" if results_data['graph_vector_fusion']['avg_retrieval_time'] < results_data['vector_only']['avg_retrieval_time'] else "increased"} by {abs((results_data['graph_vector_fusion']['avg_retrieval_time'] - results_data['vector_only']['avg_retrieval_time']) / results_data['vector_only']['avg_retrieval_time'] * 100):.1f}%.

{"💡 **Efficiency**: " if (results_data['graph_vector_fusion']['avg_tokens_per_question'] - results_data['vector_only']['avg_tokens_per_question']) / results_data['vector_only']['avg_tokens_per_question'] * 100 < 0 else "📊 **Efficiency**: "}Token usage per question {"decreased" if (results_data['graph_vector_fusion']['avg_tokens_per_question'] - results_data['vector_only']['avg_tokens_per_question']) / results_data['vector_only']['avg_tokens_per_question'] * 100 < 0 else "increased"} by {abs((results_data['graph_vector_fusion']['avg_tokens_per_question'] - results_data['vector_only']['avg_tokens_per_question']) / results_data['vector_only']['avg_tokens_per_question'] * 100):.1f}%.

## Recommendations

Based on these results:

1. **{"✅ Adopt" if results_data['improvements']['f1_pct'] > 5 else "⚠️ Consider"}** graph+vector fusion {"if the performance gains justify the added complexity" if results_data['improvements']['f1_pct'] > 0 else "after addressing performance issues"}
2. **Optimize** entity extraction with better NER models (spaCy, Transformers)
3. **Experiment** with different embedding models (sentence-transformers/all-mpnet-base-v2)
4. **Tune** RRF parameters and temporal decay functions
5. **Expand** testing to full LOCOMO dataset (10 samples)

## Technical Details

- **Entity extraction**: Regex-based (names, dates, locations, topics)
- **Graph construction**: NetworkX undirected graph with edge weights
- **Vector model**: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
- **Fusion method**: Reciprocal Rank Fusion with k=60
- **Token budget**: Greedy selection within 1000 token limit

---
*Generated by LOCOMO Benchmark Harness*
"""

    with open('results.md', 'w') as f:
        f.write(report)


if __name__ == "__main__":
    main()