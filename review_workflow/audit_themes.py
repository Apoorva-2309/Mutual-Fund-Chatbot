
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "groww_reviews.csv"
OUTPUT_DIR = BASE_DIR / "data"


THEMES = {
    "Customer support and resolution": [
        "customer care", "customer support", "support team",
        "customer service", "call centre", "call center",
        "customer representative", "support agent",
        "no response from support", "support is not responding",
        "not resolved", "issue not resolved", "poor support",
        "unable to reach customer care", "helpline",
    ],
    "Trading reliability and performance": [
        "chart not opening", "chart not working",
        "chart is not loading", "app is slow",
        "app is lagging", "very slow", "keeps crashing",
        "app crashes", "app stuck", "screen is blank",
        "blank screen", "order failed", "order not placed",
        "unable to trade", "unable to sell", "unable to buy",
        "trading error", "technical issue", "payment failed",
        "money is blocked", "transaction failed",
    ],
    "Fees and charge transparency": [
        "brokerage", "brokerage fee", "brokerage charges",
        "dp charge", "dp charges", "hidden charges",
        "hidden fees", "transaction charge", "transaction charges",
        "annual maintenance charge", "annual maintenance fee",
        "charges on cancelled orders",
        "charges on canceled orders",
        "charges on unexecuted orders",
        "fee deducted", "extra charges", "extra fees",
        "deducted without reason", "deducted from my account",
    ],
    "Privacy and security concerns": [
        "without my consent", "without consent",
        "shared my data", "data shared without",
        "personal information shared", "privacy violation",
        "security breach", "unauthorized access",
        "unauthorised access", "read my sms without",
        "read my otp without", "third party brokers",
        "random calls from third party",
    ],
    "Interface and usability": [
        "user friendly", "user-friendly", "interface",
        "app layout", "layout changed", "new layout",
        "difficult to navigate", "difficult to use",
        "hard to use", "confusing layout", "navigation",
        "after new update", "ridiculous new update",
        "button position", "back button",
        "option is given down", "cluttered interface",
    ],
}

def main():
    df = pd.read_csv(INPUT_FILE)
    df["review_text"] = df["review_text"].fillna("").astype(str)
    df["review_text_lower"] = df["review_text"].str.lower()

    total_reviews = len(df)
    results = []
    examples = []

    for theme, keywords in THEMES.items():
        # Count each review at most once per theme.
        matched = df["review_text_lower"].apply(
            lambda text: any(keyword in text for keyword in keywords)
        )

        subset = df.loc[matched].copy()

        results.append({
            "theme": theme,
            "matched_reviews": len(subset),
            "percentage_of_all_reviews": round(
                len(subset) / total_reviews * 100, 2
            ),
            "average_rating": round(
                subset["rating"].mean(), 2
            ) if not subset.empty else None,
            "method": "Keyword-based first-pass estimate",
        })

        # Save actual review excerpts for manual validation.
        for _, row in subset.sort_values(
            ["rating", "thumbs_up"],
            ascending=[True, False],
        ).head(5).iterrows():
            examples.append({
                "theme": theme,
                "date": row["date"],
                "rating": row["rating"],
                "review_id": row["review_id"],
                "review_text": row["review_text"],
                "source_url": row.get("source_url", ""),
            })

    summary = pd.DataFrame(results).sort_values(
        "matched_reviews", ascending=False
    )

    summary_path = OUTPUT_DIR / "theme_audit_summary.csv"
    examples_path = OUTPUT_DIR / "theme_audit_examples.csv"

    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(examples).to_csv(
        examples_path, index=False, encoding="utf-8-sig"
    )

    print(f"Total reviews analyzed: {total_reviews}")
    print("\nTHEME AUDIT — SORTED BY MATCHED REVIEW COUNT")
    print(summary.to_string(index=False))

    print(f"\nSummary saved to: {summary_path}")
    print(f"Examples saved to: {examples_path}")
    print(
        "\nCaution: themes can overlap, and keyword matches may be "
        "false positives. Review the examples before drawing conclusions."
    )


if __name__ == "__main__":
    main()
