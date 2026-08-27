# Data

The source CSVs used by this pipeline are not included in this repository,
since they contain private data from a certification exam / company dataset.

To run the pipeline yourself, place the following four files in this folder:

- `user_health_data.csv` — columns: `user_id, date, average_heart_rate, average_glucose, sleep_hours, activity_level`
- `supplement_usage.csv` — columns: `user_id, date, supplement_name, dosage, dosage_unit, is_placebo, experiment_id`
- `experiments.csv` — columns: `experiment_id, name, description`
- `user_profiles.csv` — columns: `user_id, email, age`

See the root `README.md` for the full data model and entity relationships.
