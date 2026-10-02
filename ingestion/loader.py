"""
Data Loader for Mutual Fund Scheme Pages.

Fetches and parses HTML pages from Groww for HDFC mutual fund schemes.
Extracts relevant sections: overview, expense ratio, exit load, riskometer,
benchmark, minimum SIP, lock-in period, fund manager, and asset allocation.
"""

import re
import json
import logging
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup, Comment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Source URLs
# =============================================================================

SOURCE_URLS = [
    {
        "scheme_name": "HDFC Large Cap Fund",
        "url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Equity Fund (Flexi Cap)",
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC ELSS Tax Saver Fund",
        "url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    },
    {
        "scheme_name": "HDFC Small Cap Fund",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    {
        "scheme_name": "HDFC Balanced Advantage Fund",
        "url": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
    },
]

# Headers to mimic a real browser request
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class SchemeSection:
    """Represents a single section of a mutual fund scheme page."""

    scheme_name: str
    source_url: str
    section_title: str
    text: str


# =============================================================================
# HTML Cleaner
# =============================================================================

def clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Remove only elements that are definitely non-content.

    Groww pages may place useful mutual-fund information inside
    containers whose classes contain words such as sidebar, widget,
    or navigation, so avoid broad class-based deletion.
    """

    # Remove elements that never contain useful page content.
    for tag in soup([
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
    ]):
        tag.decompose()

    # Remove HTML comments.
    for comment in soup.find_all(
        string=lambda text: isinstance(text, Comment)
    ):
        comment.extract()

    return soup

def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace and normalizing.
    """
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


# =============================================================================
# Section Extractors
# =============================================================================

def _get_page_text(soup: BeautifulSoup) -> str:
    """Return the complete visible page text as normalized text."""
    return clean_text(soup.get_text(" ", strip=True))


def extract_overview(soup: BeautifulSoup) -> Optional[str]:
    """Extract the investment objective / scheme overview."""

    text = _get_page_text(soup)

    match = re.search(
        r"Investment Objective\s+(.*?)(?=\s+Fund benchmark\b)",
        text,
        re.I,
    )

    if match:
        objective = clean_text(match.group(1))
        if objective:
            return f"Overview: {objective}"

    return None

def extract_expense_ratio(soup: BeautifulSoup) -> Optional[str]:
    """Extract the expense ratio."""

    text = _get_page_text(soup)

    match = re.search(
        r"Expense ratio\s+(\d+(?:\.\d+)?)%",
        text,
        re.I,
    )

    if match:
        return f"Expense Ratio: {match.group(1)}%"

    return None


def extract_exit_load(soup: BeautifulSoup) -> Optional[str]:
    """Extract the current exit load statement."""

    text = _get_page_text(soup)

    match = re.search(
        r"Minimum Lumpsum Investment is\s+₹?[\d,]+(?:\.\d+)?\.\s+"
        r"Exit load of\s+([^;]+)",
        text,
        re.I,
    )

    if match:
        return f"Exit Load: {clean_text(match.group(1))}"

    return None
def extract_riskometer(soup: BeautifulSoup) -> Optional[str]:
    """Extract the fund risk level."""

    text = _get_page_text(soup)

    match = re.search(
        r"is rated\s+([^\.]+?)\.\s+Minimum SIP",
        text,
        re.I,
    )

    if match:
        return f"Riskometer: {clean_text(match.group(1))}"

    return None
def extract_benchmark(soup: BeautifulSoup) -> Optional[str]:
    """Extract the benchmark index."""

    text = _get_page_text(soup)

    match = re.search(
        r"Fund benchmark\s+(.*?)(?=\s+Scheme Information Document)",
        text,
        re.I,
    )

    if match:
        return f"Benchmark: {match.group(1).strip()}"

    return None


def extract_minimum_sip(soup: BeautifulSoup) -> Optional[str]:
    """Extract the minimum SIP amount."""

    text = _get_page_text(soup)

    match = re.search(
        r"Min\.\s*for SIP\s+₹?\s*([\d,]+)",
        text,
        re.I,
    )

    if match:
        return f"Minimum SIP: ₹{match.group(1)}"

    match = re.search(
        r"Minimum SIP Investment is set to\s+₹?\s*([\d,]+)",
        text,
        re.I,
    )

    if match:
        return f"Minimum SIP: ₹{match.group(1)}"

    return None


def extract_lock_in(soup: BeautifulSoup) -> Optional[str]:
    """Extract an explicit lock-in period from the page."""
    text = _get_page_text(soup)

    match = re.search(
        r"\b(\d+)\s*Y\s+Lock-in\b",
        text,
        re.I,
    )

    if match:
        years = match.group(1)
        return f"Lock-in Period: {years} years"

    match = re.search(
        r"\bLock[- ]?in\s*(?:period)?\s*(?:of)?\s*(\d+)\s*years?\b",
        text,
        re.I,
    )

    if match:
        years = match.group(1)
        return f"Lock-in Period: {years} years"

    return None
def extract_fund_manager(soup: BeautifulSoup) -> Optional[str]:
    """Extract the current fund manager."""

    text = _get_page_text(soup)

    match = re.search(
        r"Fund management\s+(?:[A-Z]{1,3}\s+)?"
        r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,2})\s+"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s+\d{4}\s*-\s*Present",
        text,
        re.I,
    )

    if match:
        return f"Fund Manager: {clean_text(match.group(1))}"

    return None
def extract_asset_allocation(soup: BeautifulSoup) -> Optional[str]:
    """
    Extract explicit asset allocation.

    Do not treat individual stock holdings as asset allocation.
    """

    text = _get_page_text(soup)

    match = re.search(
        r"Asset Allocation\s+(.*?)(?=\s+Holdings\b)",
        text,
        re.I,
    )

    if not match:
        return None

    allocation_text = clean_text(match.group(1))

    if (
        not allocation_text
        or "HDFC" in allocation_text
        or "Direct Growth" in allocation_text
    ):
        return None

    percentages = re.findall(
        r"(Equity|Debt|Cash|Gold|Commodity|Others)"
        r"\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%",
        allocation_text,
        re.I,
    )

    if percentages:
        allocation = ", ".join(
            f"{name}: {percentage}%"
            for name, percentage in percentages
        )
        return f"Asset Allocation: {allocation}"

    return None
# =============================================================================
# Main Loader Class
# =============================================================================

class MFLoader:
    """Loads mutual fund scheme data from Groww HTML pages."""

    def __init__(self, timeout: int = 30):
        """
        Initialize the loader.

        Args:
            timeout: Request timeout in seconds.
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse an HTML page.

        Args:
            url: The URL to fetch.

        Returns:
            BeautifulSoup object or None if fetch fails.
        """
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            return soup
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def extract_sections(self, soup: BeautifulSoup, scheme_name: str, source_url: str) -> List[Dict]:
        """
        Extract all relevant sections from a parsed page.

        Args:
            soup: BeautifulSoup object.
            scheme_name: Name of the scheme.
            source_url: Source URL.

        Returns:
            List of section dictionaries.
        """
        # Clean the HTML first
        soup = clean_html(soup)

        sections = []
        extractors = [
            ("Overview", extract_overview),
            ("Expense Ratio", extract_expense_ratio),
            ("Exit Load", extract_exit_load),
            ("Riskometer", extract_riskometer),
            ("Benchmark", extract_benchmark),
            ("Minimum SIP", extract_minimum_sip),
            ("Lock-in Period", extract_lock_in),
            ("Fund Manager", extract_fund_manager),
            ("Asset Allocation", extract_asset_allocation),
        ]

        for section_title, extractor in extractors:
            try:
                text = extractor(soup)
                if text and len(text) > 10:  # Minimum meaningful content
                    sections.append(
                        {
                            "scheme_name": scheme_name,
                            "source_url": source_url,
                            "section_title": section_title,
                            "text": text,
                        }
                    )
                    logger.debug(f"  Extracted: {section_title} ({len(text)} chars)")
            except Exception as e:
                logger.warning(f"  Failed to extract {section_title}: {e}")

        return sections

    def load_scheme(self, scheme_info: Dict[str, str]) -> List[Dict]:
        """
        Load a single scheme page and extract sections.

        Args:
            scheme_info: Dictionary with 'scheme_name' and 'url'.

        Returns:
            List of section dictionaries.
        """
        scheme_name = scheme_info["scheme_name"]
        url = scheme_info["url"]

        soup = self.fetch_page(url)
        if soup is None:
            logger.error(f"Skipping {scheme_name} due to fetch failure")
            return []

        sections = self.extract_sections(soup, scheme_name, url)
        logger.info(f"Loaded {len(sections)} sections for {scheme_name}")
        return sections

    def load_all_schemes(self) -> List[Dict]:
        """
        Load all scheme pages and extract sections.

        Returns:
            List of all section dictionaries from all schemes.
        """
        all_sections = []
        for scheme_info in SOURCE_URLS:
            sections = self.load_scheme(scheme_info)
            all_sections.extend(sections)

        logger.info(f"Total sections loaded: {len(all_sections)}")
        return all_sections


# =============================================================================
# Convenience Functions
# =============================================================================

def load_all_schemes() -> List[Dict]:
    """
    Load all scheme pages and extract sections.

    Returns:
        List of all section dictionaries from all schemes.
    """
    loader = MFLoader()
    return loader.load_all_schemes()


def save_raw_sections(sections: List[Dict], filepath: str = "data/raw_sections.json") -> None:
    """
    Save raw loaded sections to a JSON file for inspection.

    Args:
        sections: List of section dictionaries from load_all_schemes().
        filepath: Output file path.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(sections)} raw sections to {filepath}")


def load_and_save_raw(filepath: str = "data/raw_sections.json") -> List[Dict]:
    """
    Load all schemes and save raw sections to a file.

    Args:
        filepath: Output file path.

    Returns:
        List of all section dictionaries from all schemes.
    """
    sections = load_all_schemes()
    save_raw_sections(sections, filepath)
    return sections


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Run the loader and print a summary."""
    print("=" * 70)
    print("Mutual Fund FAQ Assistant — Data Loader")
    print("=" * 70)
    print()

    loader = MFLoader()
    all_sections = loader.load_all_schemes()

    print()
    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)

    # Group by scheme
    schemes = {}
    for section in all_sections:
        name = section["scheme_name"]
        if name not in schemes:
            schemes[name] = []
        schemes[name].append(section["section_title"])

    for scheme_name, sections in schemes.items():
        print(f"\n{scheme_name}:")
        for section_title in sections:
            print(f"  - {section_title}")

    print()
    print(f"Total sections loaded: {len(all_sections)}")
    print(f"Total schemes: {len(schemes)}")
    print()
    print("Next step: Run chunker to split sections into chunks.")
    print("  python -c \"from ingestion.chunker import chunk_all_schemes; chunk_all_schemes()\"")
    print()


if __name__ == "__main__":
    main()
