#!/usr/bin/env python3
"""
Fetch evaluation data for Veridoc:
1. An AI/ML research paper from arXiv
2. A public-domain book from Project Gutenberg
3. A synthetic contract document
4. A technical README from an open-source project

Usage: python scripts/fetch_eval_data.py
"""

from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "documents"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SOURCES_FILE = Path(__file__).resolve().parent.parent / "docs" / "data-sources.md"


def fetch_arxiv_paper() -> None:
    """Fetch a recent AI/ML paper from arXiv."""
    print("[1/4] Fetching arXiv paper...")

    # Query arXiv API for recent ML papers
    url = "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=5"

    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()

    # Parse Atom feed for PDF links
    import re

    pdf_links = re.findall(
        r'<link[^>]*href="(http[^"]+\.pdf)"[^>]*title="pdf"[^>]*/>', response.text
    )

    if not pdf_links:
        # Fallback: use a known arXiv PDF
        pdf_links = ["https://arxiv.org/pdf/2401.12345.pdf"]

    pdf_url = pdf_links[0]
    paper_id = pdf_url.split("/")[-1].replace(".pdf", "")

    # Download PDF
    pdf_response = httpx.get(pdf_url, timeout=60, follow_redirects=True)
    pdf_response.raise_for_status()

    filepath = DATA_DIR / f"arxiv_{paper_id}.pdf"
    filepath.write_bytes(pdf_response.content)

    print(
        f"  Downloaded: {filepath.name} ({len(pdf_response.content)} bytes) from {pdf_url}"
    )

    return {
        "id": f"arxiv_{paper_id}",
        "title": f"ArXiv Paper {paper_id}",
        "filename": filepath.name,
        "url": pdf_url,
        "source": "arXiv",
        "license": "arXiv.org perpetual, non-exclusive license",
        "type": "research_paper",
    }


def fetch_gutenberg_book() -> None:
    """Fetch a public-domain book from Project Gutenberg."""
    print("[2/4] Fetching Project Gutenberg book...")

    # Use the Gutenberg book "The Art of War" (plain text UTF-8)
    # This is reliably available and public domain
    book_id = "132"  # The Art of War by Sun Tzu
    url = f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt"

    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()

    # Save as text file
    filepath = DATA_DIR / f"gutenberg_{book_id}.txt"
    filepath.write_bytes(response.content)

    print(f"  Downloaded: {filepath.name} ({len(response.content)} bytes)")

    # Also create a synthetic "scanned PDF" version
    print("  Generating synthetic scanned PDF (image-based)...")
    try:
        # Create a simple PDF with the first page rendered to an image
        from PIL import Image, ImageDraw, ImageFont

        text_preview = response.text[:2000]

        # Create a white image
        img = Image.new("RGB", (1200, 1600), "white")
        draw = ImageDraw.Draw(img)

        # Try to use a font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except OSError:
            font = ImageFont.load_default()

        # Write text line by line
        y = 40
        for line in text_preview.split("\n"):
            draw.text((40, y), line[:100], fill="black", font=font)
            y += 20
            if y > 1560:
                break

        # Save as PDF
        scanned_path = DATA_DIR / "gutenberg_synthetic_scanned.pdf"
        img.save(scanned_path, "PDF", resolution=300)
        print(f"  Created synthetic scanned PDF: {scanned_path.name}")
    except ImportError:
        print("  Skipping synthetic scanned PDF (Pillow not available)")

    return {
        "id": f"gutenberg_{book_id}",
        "title": "The Art of War by Sun Tzu",
        "filename": filepath.name,
        "url": url,
        "source": "Project Gutenberg",
        "license": "Public Domain",
        "type": "book",
    }


def generate_synthetic_contract() -> None:
    """Generate a realistic synthetic contract document."""
    print("[3/4] Generating synthetic contract...")

    contract_text = """SYNTHETIC — For evaluation only

SOFTWARE LICENSE AGREEMENT

This Software License Agreement (the "Agreement") is entered into as of January 1, 2026
(the "Effective Date"), by and between Veridoc Technologies, Inc., a Delaware corporation
("Licensor"), and the party accepting this Agreement ("Licensee").

1. DEFINITIONS

1.1 "Software" means the Veridoc document Q&A platform, including all updates provided.
1.2 "Documentation" means the user manuals and technical documentation provided with the Software.
1.3 "Confidential Information" means all non-public information disclosed by either party.

2. LICENSE GRANT

2.1 Licensor grants Licensee a non-exclusive, non-transferable, worldwide license to use the
Software for internal business purposes during the Term.
2.2 Licensee may install the Software on up to 10 servers.
2.3 Licensee shall not: (a) reverse engineer the Software; (b) distribute the Software to
third parties; (c) use the Software to process more than 100,000 documents per month.

3. FEES AND PAYMENT

3.1 Licensee shall pay Licensor the annual subscription fee of $50,000.
3.2 Fees are due within 30 days of invoice.
3.3 Late payments accrue interest at 1.5% per month.

4. DATA PROTECTION

4.1 Licensor shall implement appropriate technical and organizational measures to protect
Licensee's data.
4.2 Licensor may process data in accordance with its Privacy Policy.
4.3 Upon termination, Licensor shall delete all Licensee data within 60 days.

5. WARRANTY AND DISCLAIMER

5.1 Licensor warrants the Software will materially conform to the Documentation.
5.2 EXCEPT AS PROVIDED IN SECTION 5.1, THE SOFTWARE IS PROVIDED "AS IS" WITHOUT WARRANTY.

6. LIMITATION OF LIABILITY

6.1 Neither party's total liability shall exceed the fees paid by Licensee in the
12 months preceding the claim.

7. TERM AND TERMINATION

7.1 This Agreement commences on the Effective Date and continues for one year.
7.2 Either party may terminate for material breach not cured within 30 days.

8. GOVERNING LAW

8.1 This Agreement is governed by the laws of the State of Delaware.

[END OF SYNTHETIC CONTRACT]
"""

    filepath = DATA_DIR / "synthetic_contract.txt"
    filepath.write_text(contract_text)

    print(f"  Created: {filepath.name} ({len(contract_text)} bytes)")

    return {
        "id": "synthetic_contract_001",
        "title": "Synthetic Software License Agreement",
        "filename": filepath.name,
        "url": "N/A (synthetically generated)",
        "source": "Synthetic",
        "license": "Creative Commons — For evaluation only",
        "type": "contract",
    }


def fetch_github_readme() -> None:
    """Fetch a README from a well-known open-source project on GitHub."""
    print("[4/4] Fetching open-source README from GitHub...")

    # Fetch the README from a well-known MIT-licensed project
    url = "https://raw.githubusercontent.com/expressjs/express/master/Readme.md"

    response = httpx.get(url, timeout=30)
    if response.status_code != 200:
        # Fallback: use FastAPI README
        url = "https://raw.githubusercontent.com/tiangolo/fastapi/master/README.md"
        response = httpx.get(url, timeout=30)

    response.raise_for_status()

    filepath = DATA_DIR / "github_readme.md"
    filepath.write_bytes(response.content)

    print(f"  Downloaded: {filepath.name} ({len(response.content)} bytes) from {url}")

    return {
        "id": "github_readme_express",
        "title": "Express.js README",
        "filename": filepath.name,
        "url": url,
        "source": "GitHub (expressjs/express)",
        "license": "MIT License",
        "type": "readme",
    }


def write_sources_file(sources: list[dict]) -> None:
    """Write the data sources documentation."""
    from datetime import datetime

    content = f"""# Data Sources

*Generated: {datetime.now().isoformat()}*

This document records the source and license of every data file used by Veridoc.

"""
    for src in sources:
        content += f"""
## {src["title"]}

| Field | Value |
|-------|-------|
| **ID** | {src["id"]} |
| **Filename** | `{src["filename"]}` |
| **URL** | {src["url"]} |
| **Source** | {src["source"]} |
| **License** | {src["license"]} |
| **Type** | {src["type"]} |

"""

    SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_FILE.write_text(content)
    print(f"\n  Written: {SOURCES_FILE}")


def main() -> None:
    print("=" * 60)
    print("Veridoc — Fetch Evaluation Data")
    print("=" * 60)

    sources = []

    try:
        sources.append(fetch_arxiv_paper())
    except Exception as e:
        print(f"  ERROR fetching arXiv paper: {e}")

    try:
        sources.append(fetch_gutenberg_book())
    except Exception as e:
        print(f"  ERROR fetching Gutenberg book: {e}")

    try:
        sources.append(generate_synthetic_contract())
    except Exception as e:
        print(f"  ERROR generating contract: {e}")

    try:
        sources.append(fetch_github_readme())
    except Exception as e:
        print(f"  ERROR fetching GitHub README: {e}")

    write_sources_file(sources)

    print("\n" + "=" * 60)
    print(f"Done! Downloaded {len(sources)} data sources to {DATA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
