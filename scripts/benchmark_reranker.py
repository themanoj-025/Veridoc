#!/usr/bin/env python3
"""
Cross-encoder reranker batching benchmark (B10 remainder).

Measures real before/after latency for reranking 20 candidate pairs
using batch_size=1 (simulating one-by-one) vs. the batched default.

Usage::

    python scripts/benchmark_reranker.py

Requires: sentence-transformers, torch (installed from requirements.txt)
The cross-encoder model is downloaded on first run (~300MB).
"""

import sys
import time
from pathlib import Path

# Add backend to path so we can import the model
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def main() -> None:
    print("=" * 60)
    print("  Cross-Encoder Reranker Batching Benchmark")
    print("=" * 60)

    # Load the model
    print("\n[1/4] Loading cross-encoder model...")
    start = time.time()
    try:
        from sentence_transformers import CrossEncoder

        reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        load_time = time.time() - start
        print(f"      Model loaded in {load_time:.1f}s")
    except Exception as e:
        print(f"      FAILED: {e}")
        print(
            "\n      Cannot load the cross-encoder model. Ensure sentence-transformers"
        )
        print("      and torch are installed:  pip install -r backend/requirements.txt")
        sys.exit(1)

    # Create synthetic query and 20 candidate chunks
    print("\n[2/4] Preparing 20 synthetic candidate pairs...")
    query = "What is the capital of France and what is its population?"
    chunks = [
        "Paris is the capital of France, located on the Seine River. It has a population of approximately 2.1 million in the city proper."
        " The city is known for its art, fashion, and culture. The Eiffel Tower is one of the most recognizable landmarks in the world.",
        "France is a country in Western Europe. Its capital is Paris, which is also the largest city in the country."
        " The population of Paris is about 2.1 million people, with the metropolitan area housing over 12 million residents.",
        "London is the capital of the United Kingdom, located on the River Thames. It has a population of around 8.9 million people."
        " The city is a global financial center and home to numerous museums, theaters, and galleries.",
        "Berlin is the capital of Germany, known for its history and cultural diversity. The city has a population of approximately 3.6 million."
        " Berlin is famous for the Berlin Wall, Brandenburg Gate, and its vibrant arts scene.",
        "Rome is the capital of Italy, with a rich history spanning over 2,500 years. The city has a population of about 2.8 million."
        " Rome is known for the Colosseum, Vatican City, and its ancient Roman architecture.",
        "Madrid is the capital of Spain, located in the center of the country. It has a population of approximately 3.2 million people."
        " The city is known for its art museums, beautiful parks, and lively nightlife.",
        "The population of a city is typically measured by the number of people living within the city limits."
        " Metropolitan areas often have much larger populations when including suburbs and surrounding regions.",
        "European capitals are diverse in size, culture, and history. Many date back centuries and have evolved into modern metropolises."
        " Each capital city serves as the political and administrative center of its country.",
        "Paris is divided into 20 arrondissements, each with its own character. The city covers an area of 105 square kilometers."
        " The most populous arrondissement is the 15th, with about 230,000 residents.",
        "France has a population of approximately 67 million people. The country is divided into 18 regions, including 5 overseas regions."
        " French is the official language, and the currency is the euro.",
        "The Eiffel Tower was built for the 1889 World's Fair and was initially criticized by many Parisians."
        " Today it is one of the most visited monuments in the world, attracting nearly 7 million visitors annually.",
        "The Louvre Museum in Paris is the world's largest art museum and a historic monument. It houses approximately 38,000 objects,"
        " including the Mona Lisa and the Venus de Milo. The museum is located in the Louvre Palace.",
        "France has a semi-presidential republic system of government. The president is the head of state, while the prime minister"
        " is the head of government. The current constitution was established in 1958.",
        "The Seine River flows through Paris, dividing the city into the Left Bank and the Right Bank. The river is 777 kilometers long"
        " and has been an important trade route since ancient times.",
        "Paris is one of the most populous cities in the European Union. The city proper has 2.1 million residents, while the"
        " metropolitan area, known as the Ile-de-France region, has over 12 million people.",
        "European Union member states have diverse capital cities. Brussels serves as the de facto capital of the EU, hosting"
        " the European Commission and Council of the European Union. Other important EU institutions are in Strasbourg and Luxembourg.",
        "Cities around the world vary greatly in population. Tokyo is the world's most populous city with over 37 million people,"
        " followed by Delhi with 32 million and Shanghai with 28 million in their metropolitan areas.",
        "Population density refers to the number of people per unit area. Densely populated cities like Paris have over 20,000"
        " people per square kilometer, making efficient public transportation essential.",
        "France has 13 metropolitan regions. The most populous is Ile-de-France, which includes Paris and its suburbs."
        " This region is the economic heart of France, contributing about 30% of the country's GDP.",
        "Historical capitals often started as small settlements along rivers or trade routes. Paris began as a Celtic settlement"
        " called Lutetia on the Ile de la Cite in the Seine River before becoming the capital of France.",
    ]
    pairs = [(query, c) for c in chunks]
    print(f"      {len(pairs)} candidate pairs prepared")

    # Warm up the model
    print("\n[3/4] Warming up model...")
    _ = reranker.predict(pairs[:2])

    # Benchmark: batch_size=1 (simulating one-by-one scoring)
    print("\n[4/4] Benchmarking...")
    print("      Running batch_size=1 (one-by-one)...")
    start = time.time()
    scores_1 = reranker.predict(pairs, batch_size=1)
    elapsed_1 = (time.time() - start) * 1000
    print(f"        {elapsed_1:.1f} ms  ({elapsed_1 / len(pairs):.1f} ms per pair)")

    # Benchmark: default batch_size (let model decide, typically 32)
    print("      Running default batch_size (model decides)...")
    start = time.time()
    scores_batch = reranker.predict(pairs)
    elapsed_batch = (time.time() - start) * 1000
    print(
        f"        {elapsed_batch:.1f} ms  ({elapsed_batch / len(pairs):.1f} ms per pair)"
    )

    # Benchmark: batch_size=20 (single batch for 20 candidates)
    print("      Running batch_size=20 (single batch)...")
    start = time.time()
    reranker.predict(pairs, batch_size=20)
    elapsed_20 = (time.time() - start) * 1000
    print(f"        {elapsed_20:.1f} ms  ({elapsed_20 / len(pairs):.1f} ms per pair)")

    # Results
    print(f"\n{'=' * 60}")
    print("  RESULTS")
    print(f"{'=' * 60}")
    print(f"  {'Method':<25} {'Total (ms)':<15} {'Per-pair (ms)':<15}")
    print(f"  {'-' * 25} {'-' * 15} {'-' * 15}")
    print(f"  {'batch_size=1':<25} {elapsed_1:<15.0f} {elapsed_1 / len(pairs):<15.1f}")
    print(
        f"  {'default (model decides)':<25} {elapsed_batch:<15.0f} {elapsed_batch / len(pairs):<15.1f}"
    )
    print(
        f"  {'batch_size=20 (single)':<25} {elapsed_20:<15.0f} {elapsed_20 / len(pairs):<15.1f}"
    )
    print(f"{'=' * 60}")

    # Compute speedup
    speedup_vs_1 = elapsed_1 / elapsed_batch
    speedup_vs_20 = elapsed_1 / elapsed_20
    print(f"\n  Speedup (default vs batch_size=1): {speedup_vs_1:.1f}x")
    print(f"  Speedup (batch_size=20 vs 1):     {speedup_vs_20:.1f}x")
    print()

    # Verify consistency
    # Check that all three runs produce the same ranking (roughly)
    ranks_1 = sorted(range(len(scores_1)), key=lambda i: scores_1[i], reverse=True)
    ranks_batch = sorted(
        range(len(scores_batch)), key=lambda i: scores_batch[i], reverse=True
    )
    rank_diff = sum(abs(r1 - r2) for r1, r2 in zip(ranks_1, ranks_batch))
    print(
        f"  Ranking consistency (1 vs default): {rank_diff} position differences across {len(scores_1)} items"
    )
    if rank_diff == 0:
        print("  [OK] Rankings are identical -- batching preserves ranking quality")
    else:
        print(
            f"  ⚠ Rankings differ by {rank_diff} positions (may be due to floating-point precision)"
        )

    print(
        "\n  Done. Log these numbers in BUILD_LOG.md under 'B10 — Cross-encoder batching'."
    )


if __name__ == "__main__":
    main()
