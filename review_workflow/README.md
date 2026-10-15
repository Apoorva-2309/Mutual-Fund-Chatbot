# Groww Review Intelligence - Milestone 2

## 1. Overview

This workflow analyzes public Google Play reviews for the Groww app and produces a review intelligence dashboard, preliminary theme analysis, a weekly product pulse, and an optional Gmail draft approval workflow.

The analysis is exploratory. Keyword matches and machine-generated clusters are not verified findings, and public reviews may not represent all Groww users.

## 2. Prerequisites

- Windows and PowerShell
- Python 3.11
- Git
- Internet access for collecting Google Play reviews
- A Google Cloud project with the Gmail API enabled, if using Gmail draft creation

Run the commands in this README from the repository root unless stated otherwise.

## 3. Environment setup

Activate the repository virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the Milestone 2 dependencies:

```powershell
python -m pip install -r review_workflow\requirements.txt
```

The Milestone 2 dependency file is separate from the repository's root `requirements.txt` to avoid unnecessarily changing the original chatbot environment.

## 4. Workflow execution order

### Step 1 - Collect reviews

```powershell
python review_workflow\collect_reviews.py
```

Expected output:

`review_workflow\data\groww_reviews.csv`

The collector requests English-language reviews for the Groww Google Play listing in India. It uses a rolling 12-week date window, so subsequent runs can produce different datasets.
Review collection depends on the availability and behavior of the external Google Play service.

### Step 2 - Cluster reviews

```powershell
python review_workflow\analyze_reviews.py
```

Expected outputs:

- `review_workflow\data\clustered_reviews.csv`
- `review_workflow\data\theme_summary.csv`

The script filters short reviews and uses TF-IDF features and KMeans clustering. Cluster terms are descriptive signals, not verified human-readable theme labels.

### Step 3 - Audit themes

```powershell
python review_workflow\audit_themes.py
```

Expected outputs:

- `review_workflow\data\theme_audit_summary.csv`
- `review_workflow\data\theme_audit_examples.csv`

The audit uses predefined keyword lists. Themes can overlap, and keyword matches can be false positives. Review examples manually before drawing conclusions.

### Step 4 - Build the weekly product pulse

```powershell
python review_workflow\build_product_pulse.py
```

Expected output:

`review_workflow\weekly_product_pulse.md`

The report summarizes preliminary keyword matches, selected customer quotes, and proposed action ideas.

### Step 5 - Validate the report

```powershell
python review_workflow\validate_pulse.py
```

The validator checks the report's word count, quote count, HTTPS source-link format, action ideas, and required caveat.

A passing validation result does not independently verify the accuracy of the quotes, links, or theme classifications.

### Step 6 - Launch the dashboard

From the repository root:

```powershell
streamlit run review_workflow\app.py
```

The dashboard provides the Overview, Review Explorer, Theme Analysis, Product Pulse, Fee Explainer, and Approval Workflow pages.

The review dataset must exist before the dashboard can start. Generate the other outputs before using their corresponding pages.

## 5. Gmail draft setup - optional

Gmail integration is optional. The analysis and dashboard can be used independently of Gmail.

1. Enable the Gmail API in Google Cloud.
2. Configure the OAuth consent screen and add your account as a test user if the application is in testing mode.
3. Create a Desktop OAuth client.
4. Save the downloaded client credentials as `review_workflow\credentials.json`.
5. Authenticate:

   ```powershell
   python review_workflow\gmail_auth.py
   ```

6. Launch the dashboard and open Approval Workflow.
7. Review the recipient, subject, and body, then explicitly approve creation of the draft.

The application creates Gmail drafts; it does not automatically send emails.

**Security:** Never commit `credentials.json`, `token.json`, API secrets, or other authentication material. The Gmail OAuth scope used by this integration is `gmail.compose`, which permits both draft management and sending. The application code uses the draft-creation endpoint and does not call the send endpoint.

The local action ledger is stored at `review_workflow\data\action_ledger.json`. It records draft-creation attempts to help prevent accidental duplicate attempts. Preserve it when continuing work in the same local environment. If an attempt has an unresolved outcome, check Gmail Drafts before retrying.

## 6. Data and generated files

The `review_workflow\data\` directory contains locally generated datasets and workflow state. These files do not need to be committed to Git to run the workflow, but the source dataset must be generated or supplied before downstream scripts can run.

Keep original datasets and any locally useful outputs backed up if they are needed for later comparisons.

The existing report's Google Play URLs point to the app listing, not necessarily to individual reviews.

## 7. Interpretation and limitations

- Reviews are public user-generated content and may not represent the overall user population.
- The collection window changes over time.
- Clustering depends on the dataset and configured model parameters.
- Keyword-based counts are preliminary estimates; different themes can match the same review.
- Fee-related allegations are not verified policy findings.
- Review excerpts should be checked against their source before external distribution.
- The Gmail workflow creates drafts only; document updates are not automated.

## 8. Git and environment safety

Use a dedicated branch for Milestone 2 changes. Do not make Milestone 2 dependency changes in the root `requirements.txt` unless the original chatbot's environment has been deliberately reviewed.

Keep virtual environments, credentials, OAuth tokens, and local action state out of version control. Review `git status` and `git diff` before committing changes.