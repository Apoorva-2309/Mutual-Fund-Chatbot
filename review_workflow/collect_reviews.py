import pandas as pd
from datetime import datetime, timedelta, timezone
from google_play_scraper import Sort, reviews
from pathlib import Path
import time

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

APP_ID = "com.nextbillion.groww"

# Collect reviews from the last 12 weeks
END_DATE = datetime.now(timezone.utc)
START_DATE = END_DATE - timedelta(weeks=12)

OUTPUT_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "groww_reviews.csv"


def collect_groww_reviews():
    print("Starting Groww review collection...")
    print(f"Date range: {START_DATE.date()} to {END_DATE.date()}")

    collected_reviews = []
    continuation_token = None

    while True:
        try:
            result, continuation_token = reviews(
                APP_ID,
                lang="en",
                country="in",
                sort=Sort.NEWEST,
                count=200,
                continuation_token=continuation_token,
            )

        except Exception as error:
            print(f"Review collection stopped: {error}")
            break

        if not result:
            print("No more reviews returned.")
            break

        collected_reviews.extend(result)

        print(f"Reviews retrieved so far: {len(collected_reviews)}")

        oldest_date = min(
            review["at"] for review in result
        )

        if oldest_date.replace(tzinfo=timezone.utc) < START_DATE:
            break

        if continuation_token is None:
            break

        time.sleep(1)

    if not collected_reviews:
        print("No reviews were collected. Please check connectivity.")
        return

    df = pd.DataFrame([
        {
            "review_id": review.get("reviewId"),
            "date": review.get("at"),
            "rating": review.get("score"),
            "review_text": review.get("content"),
            "thumbs_up": review.get("thumbsUpCount", 0),
            "source": "Google Play",
            "app_id": APP_ID,
        }
        for review in collected_reviews
    ])

    df["date"] = pd.to_datetime(df["date"], utc=True)

    # Keep only reviews in the required date window
    df = df[
        (df["date"] >= START_DATE)
        & (df["date"] <= END_DATE)
    ].copy()

    # Remove duplicate reviews
    df = df.drop_duplicates(subset=["review_id"])
    df = df.drop_duplicates(subset=["review_text", "date"])

    # Remove empty review text
    df = df[
        df["review_text"].notna()
        & (df["review_text"].str.strip() != "")
    ]

    df = df.sort_values("date", ascending=False)

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("\nCollection completed.")
    print(f"Reviews saved: {len(df)}")
    print(f"Output file: {OUTPUT_FILE}")

    if not df.empty:
        print(f"Oldest review: {df['date'].min()}")
        print(f"Newest review: {df['date'].max()}")
        print("\nRating distribution:")
        print(df["rating"].value_counts().sort_index())


if __name__ == "__main__":
    collect_groww_reviews()