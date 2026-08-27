# Data Directory

The raw data files (`user_health_data.csv`, `supplement_usage.csv`, `experiments.csv`, and `user_profiles.csv`) contain proprietary datasets and are excluded from version control via `.gitignore`.

### Testing Pipeline Logic
To test and verify the ETL transformations, run the unit test suite:

```bash
pytest tests/
