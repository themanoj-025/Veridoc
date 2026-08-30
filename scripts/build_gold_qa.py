#!/usr/bin/env python3
"""
Generate gold Q&A pairs (20-30) across downloaded documents for evaluation.

Usage: python scripts/build_gold_qa.py
"""

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent / "eval"
EVAL_DIR.mkdir(parents=True, exist_ok=True)

GOLD_QA_PATH = EVAL_DIR / "gold_qa.json"


def build_gold_qa() -> None:
    """Build gold Q&A pairs covering factual, multi-hop, and unanswerable questions."""
    gold_qa = [
        # ── ArXiv Paper Questions ──
        {
            "id": "arxiv-001",
            "document_id": "arxiv_*",
            "question": "What methodology is proposed in this paper?",
            "gold_answer": "The paper proposes a novel methodology described in the abstract and methodology section. The exact answer depends on the specific paper fetched.",
            "source_page": 1,
            "source_excerpt": "Abstract section",
            "type": "factual",
        },
        {
            "id": "arxiv-002",
            "document_id": "arxiv_*",
            "question": "What are the main contributions of this work?",
            "gold_answer": "The contributions are listed in the introduction section of the paper.",
            "source_page": 1,
            "source_excerpt": "Introduction / Contributions section",
            "type": "factual",
        },
        {
            "id": "arxiv-003",
            "document_id": "arxiv_*",
            "question": "What datasets were used for evaluation?",
            "gold_answer": "The evaluation datasets are described in the experimental setup section.",
            "source_page": None,
            "source_excerpt": "Experiments section",
            "type": "factual",
        },
        {
            "id": "arxiv-004",
            "document_id": "arxiv_*",
            "question": "How does this approach compare to previous methods?",
            "gold_answer": "The comparison is detailed in the results section with tables and discussion.",
            "source_page": None,
            "source_excerpt": "Results section",
            "type": "multi-hop",
        },
        # ── Gutenberg Book Questions ──
        {
            "id": "gutenberg-001",
            "document_id": "gutenberg_132",
            "question": "Who wrote 'The Art of War'?",
            "gold_answer": "Sun Tzu (also written as Sunzi) is credited as the author of The Art of War.",
            "source_page": None,
            "source_excerpt": "Book attribution and introduction",
            "type": "factual",
        },
        {
            "id": "gutenberg-002",
            "document_id": "gutenberg_132",
            "question": "What is the supreme art of war according to Sun Tzu?",
            "gold_answer": "According to Sun Tzu, the supreme art of war is to subdue the enemy without fighting.",
            "source_page": None,
            "source_excerpt": "Chapter on strategic attack",
            "type": "factual",
        },
        {
            "id": "gutenberg-003",
            "document_id": "gutenberg_132",
            "question": "What are the five fundamental factors in warfare?",
            "gold_answer": "The five fundamental factors are: The Moral Law, Heaven, Earth, The Commander, and Method and discipline.",
            "source_page": None,
            "source_excerpt": "Laying Plans chapter",
            "type": "factual",
        },
        {
            "id": "gutenberg-004",
            "document_id": "gutenberg_132",
            "question": "How does the concept of deception apply to warfare according to the book?",
            "gold_answer": "All warfare is based on deception. When able to attack, you must seem unable; when using forces, seem inactive; when near, make it seem far; when far, make it seem near.",
            "source_page": None,
            "source_excerpt": "Laying Plans chapter",
            "type": "factual",
        },
        {
            "id": "gutenberg-005",
            "document_id": "gutenberg_132",
            "question": "What is the relationship between the concepts of 'shih' and strategy?",
            "gold_answer": "The document discusses various strategic concepts, including positioning and momentum.",
            "source_page": None,
            "source_excerpt": "Multiple chapters",
            "type": "multi-hop",
        },
        # ── Contract Questions ──
        {
            "id": "contract-001",
            "document_id": "synthetic_contract_001",
            "question": "What is the annual subscription fee for the Software License Agreement?",
            "gold_answer": "The annual subscription fee is $50,000.",
            "source_page": None,
            "source_excerpt": "Section 3.1: Fees and Payment",
            "type": "factual",
        },
        {
            "id": "contract-002",
            "document_id": "synthetic_contract_001",
            "question": "How many servers can the Licensee install the Software on?",
            "gold_answer": "Licensee may install the Software on up to 10 servers.",
            "source_page": None,
            "source_excerpt": "Section 2.2: License Grant",
            "type": "factual",
        },
        {
            "id": "contract-003",
            "document_id": "synthetic_contract_001",
            "question": "What happens if Licensee does not pay fees on time?",
            "gold_answer": "Late payments accrue interest at 1.5% per month.",
            "source_page": None,
            "source_excerpt": "Section 3.3: Fees and Payment",
            "type": "factual",
        },
        {
            "id": "contract-004",
            "document_id": "synthetic_contract_001",
            "question": "How long after termination must Licensor delete Licensee data?",
            "gold_answer": "Upon termination, Licensor shall delete all Licensee data within 60 days.",
            "source_page": None,
            "source_excerpt": "Section 4.3: Data Protection",
            "type": "factual",
        },
        {
            "id": "contract-005",
            "document_id": "synthetic_contract_001",
            "question": "What is the governing law of this agreement?",
            "gold_answer": "The Agreement is governed by the laws of the State of Delaware.",
            "source_page": None,
            "source_excerpt": "Section 8.1: Governing Law",
            "type": "factual",
        },
        {
            "id": "contract-006",
            "document_id": "synthetic_contract_001",
            "question": "What restrictions apply to Licensee's use of the Software?",
            "gold_answer": "Licensee shall not: (a) reverse engineer the Software; (b) distribute the Software to third parties; (c) use the Software to process more than 100,000 documents per month.",
            "source_page": None,
            "source_excerpt": "Section 2.3: License Grant",
            "type": "multi-hop",
        },
        # ── README Questions ──
        {
            "id": "readme-001",
            "document_id": "github_readme_express",
            "question": "What is Express.js?",
            "gold_answer": "Express is a fast, unopinionated, minimalist web framework for Node.js.",
            "source_page": None,
            "source_excerpt": "README introduction",
            "type": "factual",
        },
        {
            "id": "readme-002",
            "document_id": "github_readme_express",
            "question": "How do you install Express?",
            "gold_answer": "Installation is done via npm: $ npm install express",
            "source_page": None,
            "source_excerpt": "Installation section",
            "type": "factual",
        },
        {
            "id": "readme-003",
            "document_id": "github_readme_express",
            "question": "What license does Express use?",
            "gold_answer": "Express is licensed under the MIT License.",
            "source_page": None,
            "source_excerpt": "License section",
            "type": "factual",
        },
        # ── Unanswerable Questions ──
        {
            "id": "unans-001",
            "document_id": "*",
            "question": "What is the phone number of the Licensor's CEO?",
            "gold_answer": "This information is not provided in any of the documents. The correct answer should state that the information cannot be found.",
            "source_page": None,
            "source_excerpt": "N/A — Not in documents",
            "type": "unanswerable",
        },
        {
            "id": "unans-002",
            "document_id": "*",
            "question": "What was the stock price of Veridoc Technologies in 2025?",
            "gold_answer": "This information is not available in the provided documents. The system should refuse to answer.",
            "source_page": None,
            "source_excerpt": "N/A — Not in documents",
            "type": "unanswerable",
        },
        {
            "id": "unans-003",
            "document_id": "*",
            "question": "How many employees does the company have?",
            "gold_answer": "This information is not mentioned in any of the provided documents. The system should clearly indicate it cannot answer this question.",
            "source_page": None,
            "source_excerpt": "N/A — Not in documents",
            "type": "unanswerable",
        },
        {
            "id": "unans-004",
            "document_id": "synthetic_contract_001",
            "question": "What specific security certifications does Licensor hold?",
            "gold_answer": "The contract mentions implementing appropriate measures but does not specify particular certifications. The system should state this information is not in the document.",
            "source_page": None,
            "source_excerpt": "Section 4.1: Data Protection (limited info)",
            "type": "unanswerable",
        },
        {
            "id": "unans-005",
            "document_id": "*",
            "question": "Who won the Nobel Prize in Literature in 2025?",
            "gold_answer": "This information is not present in any of the uploaded documents. The system should refuse to answer.",
            "source_page": None,
            "source_excerpt": "N/A — Not in documents",
            "type": "unanswerable",
        },
    ]

    return gold_qa


def main() -> None:
    logger.info("=" * 60)
    logger.info("Veridoc — Build Gold Q&A Pairs")
    logger.info("=" * 60)

    gold_qa = build_gold_qa()
    GOLD_QA_PATH.write_text(json.dumps(gold_qa, indent=2))

    # Count by type
    factual = sum(1 for q in gold_qa if q["type"] == "factual")
    multi_hop = sum(1 for q in gold_qa if q["type"] == "multi-hop")
    unanswerable = sum(1 for q in gold_qa if q["type"] == "unanswerable")

    logger.info(f"\nGenerated {len(gold_qa)} Q&A pairs:")
    logger.info(f"  Factual: {factual}")
    logger.info(f"  Multi-hop: {multi_hop}")
    logger.info(f"  Unanswerable: {unanswerable}")
    logger.info(f"\nWritten to: {GOLD_QA_PATH}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
