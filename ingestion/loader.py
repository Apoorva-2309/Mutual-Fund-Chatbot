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
    Remove unnecessary elements from the BeautifulSoup object.

    Removes: script, style, nav, footer, header, iframe, comments,
    and elements with common ad/tracking classes.
    """
    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript"]):
        tag.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove elements with common ad/tracking/navigation classes
    ad_classes = [
        "ad", "ads", "advertisement", "banner", "popup", "modal",
        "cookie", "newsletter", "sidebar", "breadcrumb", "pagination",
        "social", "share", "related", "recommended", "footer", "header",
        "navbar", "menu", "nav", "toolbar", "widget",
    ]
    for cls in ad_classes:
        for element in soup.find_all(class_=re.compile(cls, re.I)):
            element.decompose()

    # Remove elements with common ad/tracking IDs
    ad_ids = ["ad", "ads", "banner", "popup", "modal", "cookie", "newsletter", "sidebar"]
    for id_val in ad_ids:
        for element in soup.find_all(id=re.compile(id_val, re.I)):
            element.decompose()

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

def extract_overview(soup: BeautifulSoup) -> Optional[str]:
    """Extract scheme overview/description."""
    # Try multiple selectors for overview
    selectors = [
        "div.scheme-description",
        "div.about-scheme",
        "div.scheme-overview",
        "div.description",
        "div[data-testid='scheme-description']",
        "p.scheme-description",
        "div.scheme-detail p",
        "div.scheme-info p",
    ]
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return clean_text(element.get_text())

    # Fallback: find paragraphs with substantial text near the top
    for p in soup.find_all("p"):
        text = clean_text(p.get_text())
        if len(text) > 100:  # Substantial paragraph
            return text

    return None


def extract_expense_ratio(soup: BeautifulSoup) -> Optional[str]:
    """Extract expense ratio information."""
    # Look for expense ratio in tables, divs, or specific sections
    patterns = [
        r"expense\s*ratio",
        r"total\s*expense",
        r"ter\b",
        r"annual\s*recurring\s*charges",
    ]

    # Search in tables
    for table in soup.find_all("table"):
        text = clean_text(table.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return f"Expense Ratio: {text}"

    # Search in divs/spans with relevant text
    for element in soup.find_all(["div", "span", "p", "td", "li"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 500:
                return f"Expense Ratio: {text}"

    return None


def extract_exit_load(soup: BeautifulSoup) -> Optional[str]:
    """Extract exit load structure."""
    patterns = [
        r"exit\s*load",
        r"redemption\s*charge",
        r"exit\s*charge",
    ]

    for table in soup.find_all("table"):
        text = clean_text(table.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return f"Exit Load: {text}"

    for element in soup.find_all(["div", "span", "p", "td", "li"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 500:
                return f"Exit Load: {text}"

    return None


def extract_riskometer(soup: BeautifulSoup) -> Optional[str]:
    """Extract riskometer level."""
    patterns = [
        r"riskometer",
        r"risk\s*level",
        r"risk\s*profile",
        r"investment\s*risk",
        r"moderate",
        r"high\s*risk",
        r"low\s*risk",
    ]

    for element in soup.find_all(["div", "span", "p", "td", "li", "img"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 300:
                return f"Riskometer: {text}"

    # Check for riskometer images with alt text
    for img in soup.find_all("img"):
        alt = img.get("alt", "")
        if re.search(r"risk", alt, re.I):
            return f"Riskometer: {alt}"

    return None


def extract_benchmark(soup: BeautifulSoup) -> Optional[str]:
    """Extract benchmark information."""
    patterns = [
        r"benchmark",
        r"index",
        r"nifty",
        r"s&p",
        r"bse",
        r"sensex",
        r"crISIL",
    ]

    for table in soup.find_all("table"):
        text = clean_text(table.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return f"Benchmark: {text}"

    for element in soup.find_all(["div", "span", "p", "td", "li"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 300:
                return f"Benchmark: {text}"

    return None


def extract_minimum_sip(soup: BeautifulSoup) -> Optional[str]:
    """Extract minimum SIP amount."""
    patterns = [
        r"minimum\s*sip",
        r"min\s*sip",
        r"sip\s*amount",
        r"minimum\s*investment",
        r"min\s*investment",
        r"sip",
    ]

    for table in soup.find_all("table"):
        text = clean_text(table.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return f"Minimum SIP: {text}"

    for element in soup.find_all(["div", "span", "p", "td", "li"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 300:
                return f"Minimum SIP: {text}"

    return None


def extract_lock_in(soup: BeautifulSoup) -> Optional[str]:
    """Extract lock-in period (relevant for ELSS)."""
    patterns = [
        r"lock[\s-]?in",
        r"lock\s*period",
        r"elss",
        r"tax\s*saver",
        r"3\s*years?",
        r"three\s*years?",
    ]

    for element in soup.find_all(["div", "span", "p", "td", "li"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 300:
                return f"Lock-in Period: {text}"

    return None


def extract_fund_manager(soup: BeautifulSoup) -> Optional[str]:
    """Extract fund manager details."""
    patterns = [
        r"fund\s*manager",
        r"fund\s*management",
        r"managed\s*by",
        r"portfolio\s*manager",
    ]

    for element in soup.find_all(["div", "span", "p", "td", "li"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 300:
                return f"Fund Manager: {text}"

    return None


def extract_asset_allocation(soup: BeautifulSoup) -> Optional[str]:
    """Extract asset allocation information."""
    patterns = [
        r"asset\s*allocation",
        r"allocation",
        r"equity\s*allocation",
        r"debt\s*allocation",
        r"portfolio\s*allocation",
        r"sector\s*allocation",
        r"top\s*holdings",
    ]

    for table in soup.find_all("table"):
        text = clean_text(table.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return f"Asset Allocation: {text}"

    for element in soup.find_all(["div", "span", "p", "td", "li"]):
        text = clean_text(element.get_text())
        for pattern in patterns:
            if re.search(pattern, text, re.I) and len(text) < 500:
                return f"Asset Allocation: {text}"

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
