
import re
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "groww_reviews.csv"
OUTPUT_DIR = BASE_DIR / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CLUSTERED_FILE = OUTPUT_DIR / "clustered_reviews.csv"
SUMMARY_FILE = OUTPUT_DIR / "theme_summary.csv"

MAX_THEMES = 5
MIN_REVIEW_LENGTH = 20


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    print("Loading Groww reviews...")

    df = pd.read_csv(INPUT_FILE)
    df["review_text"] = df["review_text"].fillna("").astype(str)
    df["clean_text"] = df["review_text"].map(clean_text)

    # Exclude very short comments from clustering.
    # Keep the original CSV unchanged.
    eligible = (
        df["clean_text"].str.len() >= MIN_REVIEW_LENGTH
    )

    work = df.loc[eligible].copy()

    if len(work) < MAX_THEMES:
        print("Not enough sufficiently detailed reviews to cluster.")
        return

    print(f"Total reviews: {len(df)}")
    print(f"Reviews eligible for clustering: {len(work)}")

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=5000,
        ngram_range=(1, 2),
        min_df=3,
        max_df=0.90,
        sublinear_tf=True,
    )

    matrix = vectorizer.fit_transform(work["clean_text"])

    model = KMeans(
        n_clusters=MAX_THEMES,
        random_state=42,
        n_init=10,
    )

    work["theme_id"] = model.fit_predict(matrix)

    terms = vectorizer.get_feature_names_out()
    summaries = []

    for theme_id in range(MAX_THEMES):
        positions = [
            i for i, label in enumerate(work["theme_id"])
            if label == theme_id
        ]

        if not positions:
            continue

        # Top terms describe a cluster; they are not yet
        # verified human-readable theme labels.
        mean_scores = matrix[positions].mean(axis=0)
        scores = mean_scores.A1
        top_indices = scores.argsort()[::-1][:10]
        top_terms = [terms[i] for i in top_indices]

        cluster_reviews = work.iloc[positions]
        representative = cluster_reviews.assign(
            text_length=cluster_reviews["review_text"].str.len()
        ).sort_values(
            ["text_length", "thumbs_up"],
            ascending=[False, False],
        )

        summaries.append({
            "theme_id": theme_id,
            "review_count": len(cluster_reviews),
            "share_of_clustered_reviews_pct": round(
                len(cluster_reviews) / len(work) * 100, 2
            ),
            "average_rating": round(
                cluster_reviews["rating"].mean(), 2
            ),
            "top_terms": ", ".join(top_terms),
            "representative_review": (
                representative.iloc[0]["review_text"]
            ),
            "representative_review_date": (
                representative.iloc[0]["date"]
            ),
            "representative_review_rating": int(
                representative.iloc[0]["rating"]
            ),
            "representative_review_id": (
                representative.iloc[0]["review_id"]
            ),
        })

    work.to_csv(CLUSTERED_FILE, index=False, encoding="utf-8-sig")

    summary = pd.DataFrame(summaries).sort_values(
        "review_count", ascending=False
    )
    summary.to_csv(SUMMARY_FILE, index=False, encoding="utf-8-sig")

    print("\nTHEME SUMMARY — REVIEW BEFORE NAMING THEMES")
    print(
        summary[
            [
                "theme_id",
                "review_count",
                "share_of_clustered_reviews_pct",
                "average_rating",
                "top_terms",
            ]
        ].to_string(index=False)
    )

    print(f"\nClustered reviews saved to: {CLUSTERED_FILE}")
    print(f"Theme summary saved to: {SUMMARY_FILE}")
    print("\nImportant: review cluster terms and quotes manually.")
    print("Do not treat a cluster label as a verified finding.")


if __name__ == "__main__":
    main()
