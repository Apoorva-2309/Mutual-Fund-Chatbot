
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "groww_reviews.csv"
OUTPUT_FILE = BASE_DIR / "weekly_product_pulse.md"

RULES = {
    "Trading reliability and performance": [
        "chart", "slow", "lag", "crash", "stuck",
        "technical error", "not working", "order failed",
        "unable to trade", "blank screen",
    ],
    "Fees and charge transparency": [
        "brokerage", "dp charge", "hidden charge",
        "hidden fee", "charges", "deducted", "fee",
    ],
    "Customer support and resolution": [
        "customer care", "customer support", "support team",
        "customer service", "no response", "not resolved",
        "call centre", "call center",
    ],
    "Interface and usability": [
        "interface", "layout", "navigation",
        "difficult to use", "new update", "button",
        "user friendly",
    ],
    "Privacy and security concerns": [
        "privacy", "without consent", "data shared",
        "unauthorized access", "unauthorised access",
    ],
}


def short_quote(text, limit=85):
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def main():
    df = pd.read_csv(DATA_FILE)
    df["review_text"] = df["review_text"].fillna("").astype(str)
    df["review_text_lower"] = df["review_text"].str.lower()
    df["date"] = pd.to_datetime(
        df["date"], utc=True, errors="coerce"
    )

    # Detailed, low-rated reviews for pain-point discovery.
    detailed = df[
        (df["rating"] <= 3) &
        (df["review_text"].str.len() >= 40)
    ].copy()

    matches = []
    for theme, keywords in RULES.items():
        mask = detailed["review_text_lower"].apply(
            lambda text: any(k in text for k in keywords)
        )
        subset = detailed.loc[mask]
        if not subset.empty:
            matches.append((theme, subset))

    matches.sort(key=lambda item: len(item[1]), reverse=True)
    top_themes = matches[:3]


    # Select distinct, low-rated reviews that directly match each theme.
    quote_keywords = {
        "Trading reliability and performance": [
            "chart", "slow", "lag", "crash", "stuck",
            "technical error", "not working", "order failed",
            "unable to trade", "blank screen",
        ],
        "Customer support and resolution": [
            "customer care", "customer support", "support team",
            "customer service", "no response", "not resolved",
            "call centre", "call center",
        ],
        "Fees and charge transparency": [
            "brokerage", "dp charge", "hidden charge",
            "hidden fee", "transaction charge", "extra charges",
            "charges on cancelled orders",
            "charges on unexecuted orders",
        ],
    }

    quote_rows = []
    used_ids = set()

    for theme, subset in top_themes:
        keywords = quote_keywords.get(theme, [])
        candidates = subset.copy()

        candidates["keyword_score"] = candidates[
            "review_text_lower"
        ].apply(
            lambda text: sum(1 for k in keywords if k in text)
        )

        candidates = candidates[
            candidates["keyword_score"] > 0
        ].sort_values(
            ["rating", "keyword_score", "thumbs_up", "date"],
            ascending=[True, False, False, False],
        )

        for _, row in candidates.iterrows():
            review_id = str(row.get("review_id", ""))
            if review_id not in used_ids:
                quote_rows.append((theme, row))
                used_ids.add(review_id)
                break

    if len(quote_rows) < 3:
        print(
            "Warning: fewer than three distinct, theme-matched quotes "
            "were found. Do not substitute unrelated quotes."
        )


    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "# Weekly Product Pulse - Groww",
        f"Generated: {generated} UTC",
        f"Dataset: {len(df):,} public reviews; "
        f"{len(detailed):,} detailed reviews rated 1-3 stars.",
        "",
        "## Top themes",
    ]

    for theme, subset in top_themes:
        lines.append(
            f"- {theme}: {len(subset)} keyword matches; preliminary."
        )

    lines.extend(["", "## Customer quotes"])

    for theme, row in quote_rows:
        date = (
            row["date"].strftime("%Y-%m-%d")
            if pd.notna(row["date"]) else "Date unavailable"
        )
        source = row.get("source_url", "")
        review_id = str(row.get("review_id", ""))
        lines.append(
            f'- {theme} ({date}, {int(row["rating"])} stars): '
            f'"{short_quote(row["review_text"])}"'
        )
        lines.append(f"  Source: {source} | Review ID: {review_id}")

    lines.extend([
        "",
        "## Key observation",
        "Reviews suggest friction in trading reliability, support, "
        "and charge clarity. Counts are keyword-based, themes overlap, "
        "and fee allegations are not verified policy findings.",
        "",
        "## Action ideas",
        "1. Investigate chart, order, and payment failures.",
        "2. Test how easily users find brokerage, DP charges, and taxes.",
        "3. Measure support response and resolution times.",
        "",
        "Note: Public reviews may not represent all Groww users.",
    ])

    report = "\n".join(lines)
    word_count = len(report.split())

    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"Report word count: {word_count}")
    if word_count > 250:
        print("Warning: report exceeds the 250-word target.")
    else:
        print("Word-count target met.")
    print(f"Product pulse saved to: {OUTPUT_FILE}")
    print("Top themes:")
    for theme, subset in top_themes:
        print(f"- {theme}: {len(subset)} matches")
    print(f"Selected quote count: {len(quote_rows)}")


if __name__ == "__main__":
    main()
