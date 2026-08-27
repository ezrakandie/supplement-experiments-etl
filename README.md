# Supplement Experiments ETL

![](https://github.com/ezrakandie/supplement-experiments-etl/actions/workflows/ci.yml/badge.svg)

A data engineering pipeline that cleans and merges four disparate data
sources wearable/health metrics, supplement intake logs, experiment
metadata, and user profiles into a single, analysis-ready dataset for
**1001-Experiments**, a personalized-supplement company.

## Problem

1001-Experiments collects data from wearables, supplement usage logs, and
user profiles across thousands of users. Previously, analysts cross-referenced
these sources manually and separately for every analysis slow and
error-prone. This pipeline consolidates them into one clean, daily-level
table.

## Data model

```
user_profiles ──< user_health_data
     │
     └──< supplement_usage >── experiments
```

| Table | Grain | Key columns |
|---|---|---|
| `user_profiles.csv` | 1 row per user | `user_id` (PK), `email`, `age` |
| `user_health_data.csv` | 1 row per user per day | `user_id`, `date` |
| `supplement_usage.csv` | 1+ rows per user per day | `user_id`, `date`, `experiment_id` |
| `experiments.csv` | 1 row per experiment | `experiment_id` (PK), `name` |

## What the pipeline does

- **Type coercion & parsing**: normalizes IDs, parses dates, strips
  inconsistent units (e.g. `sleep_hours` arrives as `"8.8h"` / `"8.0H"`).
- **Unit standardization**: converts all supplement dosages to grams
  (`mg` → `g` via ÷1000).
- **Categorical cleanup**: normalizes boolean encodings for `is_placebo`;
  fills missing supplement entries with the sentinel `'No intake'`.
- **Derived features**: buckets raw `age` into `user_age_group`
  (`Under 18`, `18-25`, ..., `Over 65`, or `Unknown` for missing values).
- **Join logic**: outer-joins health and supplement logs on `user_id` +
  `date` so health-only days, supplement-only days, and multi-supplement
  days are all represented correctly, then left-joins in experiment names
  and user profile info.
- **Data quality guarantees**: the output has zero missing values in
  `user_id`, `date`, or `email`, and no duplicate rows.

## Output schema

| Column | Description |
|---|---|
| `user_id` | Unique user identifier. Never missing. |
| `date` | Date of the log entry. Never missing. |
| `email` | User's contact email. Never missing. |
| `user_age_group` | Bucketed age group, or `'Unknown'` if age is missing. |
| `experiment_name` | Name of the associated experiment; missing if the user only logged health data that day. |
| `supplement_name` | Supplement taken; `'No intake'` if none logged. |
| `dosage_grams` | Dosage in grams (converted from mg where needed). |
| `is_placebo` | Whether the supplement was a placebo. |
| `average_heart_rate` | From wearable device. |
| `average_glucose` | From wearable device. |
| `sleep_hours` | Sleep for the night preceding the log date. |
| `activity_level` | Activity score, 0–100. |

## Usage

```python
from src.merge_all_data import merge_all_data

df = merge_all_data(
    "data/user_health_data.csv",
    "data/supplement_usage.csv",
    "data/experiments.csv",
    "data/user_profiles.csv",
)
```

## Project structure

```
.
├── src/
│   └── merge_all_data.py   # main ETL pipeline
├── tests/
│   └── test_merge_all_data.py
├── data/
│   └── README.md           # schema notes (source data not included)
├── requirements.txt
└── README.md
```

## Running tests

```bash
pip install -r requirements.txt
pytest tests/
```

## Tech stack

- Python 3
- pandas / numpy for transformation
- pytest for testing

## Notes

The source CSV files contain proprietary data and are excluded from this public repository via `.gitignore`. The included test suite (`tests/test_merge_all_data.py`) uses synthetic data fixtures to fully validate all transformation, joining, and data-quality rules without exposing private data.
