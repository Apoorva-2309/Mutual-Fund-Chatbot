
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

REVIEWS_FILE = DATA_DIR / "groww_reviews.csv"
CLUSTERED_FILE = DATA_DIR / "clustered_reviews.csv"
THEMES_FILE = DATA_DIR / "theme_summary.csv"
PULSE_FILE = BASE_DIR / "weekly_product_pulse.md"
FEE_FILE = BASE_DIR / "fee_explainer.md"

st.set_page_config(
    page_title="Groww Review Intelligence",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Groww Review Intelligence")
st.caption(
    "Milestone 2 | RAGs & Context Engineering | "
    "Public review analysis and product insights"
)


@st.cache_data
def load_csv(path):
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


reviews = load_csv(REVIEWS_FILE)
clusters = load_csv(CLUSTERED_FILE)
themes = load_csv(THEMES_FILE)

if reviews.empty:
    st.error(
        "Reviews dataset not found. Run collect_reviews.py first."
    )
    st.stop()

st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Choose a section",
    [
        "Overview",
        "Review Explorer",
        "Theme Analysis",
        "Product Pulse",
        "Fee Explainer",
        "Approval Workflow",
    ],
)

st.sidebar.caption(
    "Source: public Google Play reviews. "
    "Customer claims are not independently verified."
)


if page == "Overview":
    st.header("Review Dataset Overview")

    reviews["rating"] = pd.to_numeric(
        reviews["rating"], errors="coerce"
    )
    reviews["date"] = pd.to_datetime(
        reviews["date"], errors="coerce", utc=True
    )

    low_rated_detailed = reviews[
        (reviews["rating"] <= 3)
        & (reviews["review_text"].fillna("").str.len() >= 40)
    ]

    c1, c2, c3 = st.columns(3)
    c1.metric("Reviews collected", f"{len(reviews):,}")
    c2.metric(
        "Average rating",
        f"{reviews['rating'].mean():.2f} / 5"
    )
    c3.metric(
        "Detailed low-rated reviews",
        f"{len(low_rated_detailed):,}"
    )

    st.subheader("Rating distribution")
    rating_counts = (
        reviews["rating"]
        .value_counts()
        .sort_index()
        .rename_axis("Rating")
        .rename("Reviews")
    )
    st.bar_chart(rating_counts)

    st.subheader("Dataset preview")
    st.dataframe(reviews.head(10), use_container_width=True)

    st.info(
        "Theme counts are preliminary keyword-based matches. "
        "Themes may overlap and are not proof of a product defect."
    )

elif page == "Review Explorer":
    st.header("Review Explorer")

    ratings = sorted(
        pd.to_numeric(reviews["rating"], errors="coerce")
        .dropna()
        .unique()
        .tolist()
    )
    selected_ratings = st.multiselect(
        "Filter by rating",
        ratings,
        default=ratings,
    )

    search_text = st.text_input(
        "Search review text",
        placeholder="e.g. brokerage, customer support, chart",
    )

    filtered = reviews.copy()
    filtered["rating"] = pd.to_numeric(
        filtered["rating"], errors="coerce"
    )
    filtered = filtered[
        filtered["rating"].isin(selected_ratings)
    ]

    if search_text.strip():
        filtered = filtered[
            filtered["review_text"]
            .fillna("")
            .str.contains(search_text, case=False, regex=False)
        ]

    st.write(f"Matching reviews: {len(filtered):,}")
    display_columns = [
        c for c in [
            "date", "rating", "review_text",
            "thumbs_up", "review_id", "source_url"
        ] if c in filtered.columns
    ]
    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        height=500,
    )

    st.download_button(
        "Download filtered reviews",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="filtered_groww_reviews.csv",
        mime="text/csv",
    )

elif page == "Theme Analysis":
    st.header("Theme Analysis")
    st.caption(
        "The counts below come from existing analysis outputs. "
        "Keyword matches may overlap; interpret them as directional signals."
    )

    if not themes.empty:
        st.subheader("Theme summary")
        st.dataframe(themes, use_container_width=True)
    else:
        st.warning(
            "Theme summary file not found. Run analyze_reviews.py first."
        )

    if not clusters.empty:
        st.subheader("Clustering output")
        st.dataframe(clusters.head(100), use_container_width=True)
    else:
        st.info(
            "Clustered review output not found. "
            "Run analyze_reviews.py to generate it."
        )

elif page == "Product Pulse":
    st.header("Weekly Product Pulse")

    if PULSE_FILE.exists():
        pulse_text = PULSE_FILE.read_text(encoding="utf-8")
        st.markdown(pulse_text)
        st.download_button(
            "Download product pulse",
            data=pulse_text,
            file_name="weekly_product_pulse.md",
            mime="text/markdown",
        )
    else:
        st.warning("Product pulse not found. Run build_product_pulse.py.")

elif page == "Fee Explainer":
    st.header("Understanding Groww Trading Charges")

    if FEE_FILE.exists():
        fee_text = FEE_FILE.read_text(encoding="utf-8")
        st.markdown(fee_text)
        st.download_button(
            "Download fee explainer",
            data=fee_text,
            file_name="fee_explainer.md",
            mime="text/markdown",
        )
    else:
        st.error("fee_explainer.md was not found.")


elif page == "Approval Workflow":
    import hashlib
    import json

    from review_workflow.gmail_drafts import create_gmail_draft

    st.header("Human Approval Workflow")
    st.caption(
        "Review the proposed email, edit it if needed, and explicitly "
        "approve creation of a Gmail draft. This workflow does not send emails."
    )

    if PULSE_FILE.exists():
        pulse_text = PULSE_FILE.read_text(encoding="utf-8")
    else:
        pulse_text = (
            "Weekly Product Pulse is unavailable. "
            "Please generate the report before creating a draft."
        )

    st.subheader("1. Review the email")

    with st.form("gmail_draft_approval_form"):
        recipient = st.text_input(
            "Recipient email address",
            placeholder="Enter the intended recipient's email",
        )

        subject = st.text_input(
            "Email subject",
            value="Weekly Product Pulse — Groww Review Intelligence",
        )

        body = st.text_area(
            "Email body",
            value=(
                "Hello,\n\n"
                "Please find below the latest product pulse based on "
                "public Google Play reviews of Groww.\n\n"
                + pulse_text
                + "\n\nRegards,\nReview Intelligence"
            ),
            height=400,
        )

        approved = st.checkbox(
            "I have reviewed the recipient, subject, and body "
            "and approve creating this Gmail draft."
        )

        create_clicked = st.form_submit_button(
            "Approve and create Gmail draft",
            type="primary",
        )

    if create_clicked:
        if not approved:
            st.warning("Please explicitly approve the draft first.")
        elif (
            not recipient.strip()
            or "@" not in recipient
            or "." not in recipient.rsplit("@", 1)[-1]
        ):
            st.error("Enter a valid recipient email address.")
        elif not subject.strip() or not body.strip():
            st.error("The subject and body cannot be empty.")
        else:
            ledger_file = DATA_DIR / "action_ledger.json"
            draft_key = hashlib.sha256(
                (
                    recipient.strip().lower()
                    + "\n"
                    + subject.strip()
                    + "\n"
                    + body
                ).encode("utf-8")
            ).hexdigest()


            try:
                if ledger_file.exists():
                    ledger = json.loads(
                        ledger_file.read_text(encoding="utf-8")
                    )
                else:
                    ledger = {}

                existing = ledger.get(draft_key)

                if existing:
                    if (
                        existing.get("status") == "draft_created"
                        and existing.get("draft_id")
                    ):
                        st.info(
                            "A draft was already recorded for this exact "
                            "recipient, subject, and body."
                        )
                        st.write("Previously recorded draft ID:")
                        st.code(existing["draft_id"])
                    else:
                        st.warning(
                            "A previous attempt has an unresolved status. "
                            "Check Gmail Drafts before taking further action. "
                            "This app will not automatically retry it."
                        )
                        st.write("Recorded status:")
                        st.code(existing.get("status", "unknown"))

                else:
                    from datetime import datetime, timezone

                    DATA_DIR.mkdir(parents=True, exist_ok=True)

                    started_at = datetime.now(timezone.utc).isoformat()
                    ledger[draft_key] = {
                        "status": "creation_started",
                        "started_at": started_at,
                        "draft_id": None,
                    }

                    # Persist intent before contacting Gmail.
                    ledger_file.write_text(
                        json.dumps(ledger, indent=2),
                        encoding="utf-8",
                    )

                    try:
                        with st.spinner("Creating your Gmail draft..."):
                            draft_id = create_gmail_draft(
                                recipient.strip(),
                                subject.strip(),
                                body,
                            )
                    except Exception as exc:
                        ledger[draft_key]["status"] = "outcome_unknown"
                        ledger[draft_key]["updated_at"] = (
                            datetime.now(timezone.utc).isoformat()
                        )
                        ledger[draft_key]["error_type"] = type(exc).__name__

                        ledger_file.write_text(
                            json.dumps(ledger, indent=2),
                            encoding="utf-8",
                        )

                        st.error(
                            "The outcome could not be confirmed. "
                            "Check Gmail Drafts before retrying."
                        )
                        st.caption(
                            f"Technical details: {type(exc).__name__}: {exc}"
                        )
                    else:
                        ledger[draft_key]["status"] = "draft_created"
                        ledger[draft_key]["draft_id"] = draft_id
                        ledger[draft_key]["updated_at"] = (
                            datetime.now(timezone.utc).isoformat()
                        )

                        ledger_file.write_text(
                            json.dumps(ledger, indent=2),
                            encoding="utf-8",
                        )

                        st.success("Gmail draft created successfully.")
                        st.write("Draft ID:")
                        st.code(draft_id)
                        st.info(
                            "Open Gmail → Drafts to review it. "
                            "The application has not sent the email."
                        )

            except Exception as exc:
                st.error(
                    "The action ledger could not be read or updated. "
                    "Check Gmail Drafts and the ledger before retrying."
                )

st.caption(
    "Prototype status: local Streamlit app. "
    "Gmail draft creation is connected; document updates are pending. "
    "This workflow does not send emails automatically."
)
