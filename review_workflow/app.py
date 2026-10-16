
from pathlib import Path
import textwrap

import altair as alt
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEPLOYMENT_DATA_DIR = BASE_DIR / "deployment_data"


def resolve_data_file(filename):
    local_file = DATA_DIR / filename
    if local_file.exists():
        return local_file
    return DEPLOYMENT_DATA_DIR / filename


REVIEWS_FILE = resolve_data_file("groww_reviews.csv")
CLUSTERED_FILE = resolve_data_file("clustered_reviews.csv")
THEMES_FILE = resolve_data_file("theme_summary.csv")
PULSE_FILE = BASE_DIR / "weekly_product_pulse.md"
FEE_FILE = BASE_DIR / "fee_explainer.md"

def format_pulse_for_email(report: str) -> str:
    formatted_lines = []

    for line in report.splitlines():
        if "Source: " in line and "Review ID:" in line:
            quote_part, source_part = line.split("Source:", 1)
            quote_part = textwrap.fill(
                quote_part.rstrip(),
                width=85,
                subsequent_indent="  ",
            )

            source_url, review_id = source_part.split(
                "| Review ID:", 1
            )

            formatted_lines.append(quote_part)
            formatted_lines.append("  Source: " + source_url.strip())
            formatted_lines.append("  Review ID: " + review_id.strip())
        elif len(line) > 85 and not line.startswith("http"):
            formatted_lines.append(textwrap.fill(line, width=85))
        else:
            formatted_lines.append(line)

    return "\n".join(formatted_lines)

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

pages = [
    "Overview",
    "Review Explorer",
    "Theme Analysis",
    "Product Pulse",
    "Fee Explainer",
    "Approval Workflow",
]

page = st.sidebar.radio("Choose a section", pages)

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

    rating_chart = (
        alt.Chart(rating_counts.reset_index())
        .mark_bar()
        .encode(
            x=alt.X("Rating:O", title="Rating"),
            y=alt.Y(
                "Reviews:Q",
                title="Number of reviews",
                scale=alt.Scale(domainMin=0),
            ),
            tooltip=["Rating", "Reviews"],
        )
    )

    st.altair_chart(rating_chart, use_container_width=True)


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

    from gmail_drafts import (
        GmailConfigError,
        create_gmail_draft,
        gmail_is_configured,
    )

    st.header("Human Approval Workflow")
    st.caption(
        "Review the proposed email, edit it if needed, and explicitly "
        "approve creation of a Gmail draft. This workflow does not send emails."
    )

    if not gmail_is_configured():
        st.warning(
            "Gmail is not configured in this environment. "
            "Locally, run `python review_workflow/gmail_auth.py` after "
            "saving credentials.json next to this app. On Streamlit Cloud, "
            "add a `[gmail]` secret with `client_id`, `client_secret`, "
            "and `refresh_token`. This page creates drafts only; it never "
            "sends email."
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
                + format_pulse_for_email(pulse_text)
                + "\n\nRegards,\nReview Intelligence"
            ),
            height=550,
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
        elif not gmail_is_configured():
            st.error(
                "Gmail is not configured, so a draft was not created. "
                "Follow the setup instructions on this page first."
            )
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

            if st.session_state.get("_gmail_draft_key") == draft_key:
                st.info(
                    "A draft for this exact recipient, subject, and body "
                    "was already created in this session."
                )
                previous_id = st.session_state.get("_gmail_draft_id")
                if previous_id:
                    st.write("Draft ID:")
                    st.code(previous_id)
            else:
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
                            if isinstance(exc, GmailConfigError):
                                st.caption(str(exc))
                            else:
                                st.caption(
                                    "Technical details: "
                                    f"{type(exc).__name__}"
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

                            st.session_state["_gmail_draft_key"] = draft_key
                            st.session_state["_gmail_draft_id"] = draft_id

                            st.success("Gmail draft created successfully.")
                            st.write("Draft ID:")
                            st.code(draft_id)
                            st.info(
                                "Open Gmail → Drafts to review it. "
                                "The application has not sent the email."
                            )

                except Exception:
                    st.error(
                        "The action ledger could not be read or updated. "
                        "Check Gmail Drafts and the ledger before retrying."
                    )

st.caption(
    "Prototype status: local Streamlit app. "
    "Gmail draft creation is connected; document updates are pending. "
    "This workflow does not send emails automatically."
)
