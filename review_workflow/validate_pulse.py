
from pathlib import Path
import re

report_path = Path(__file__).resolve().parent / "weekly_product_pulse.md"
report = report_path.read_text(encoding="utf-8")

word_count = len(report.split())
quote_count = len(re.findall(r'^\- .* stars\): "', report, re.MULTILINE))
source_count = len(re.findall(r'^\s+Source: https://', report, re.MULTILINE))

checks = {
    "Report exists": report_path.exists(),
    "Within 250 words": word_count <= 250,
    "Exactly 3 customer quotes": quote_count == 3,
    "Each quote has a source link": source_count == 3,
    "Three action ideas included": "3. Measure support" in report,
    "Caveat about unverified allegations included": (
        "not verified policy findings" in report
    ),
}

print(f"Word count: {word_count}")
for check, passed in checks.items():
    print(f"[{'PASS' if passed else 'FAIL'}] {check}")

if not all(checks.values()):
    raise SystemExit("Validation failed. Review the report.")

print("\nAll validation checks passed.")
