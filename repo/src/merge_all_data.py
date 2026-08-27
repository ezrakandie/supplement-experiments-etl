"""
merge_all_data.py

ETL pipeline that cleans and merges 1001-Experiments' four source datasets
(user health metrics, supplement usage, experiment metadata, and user
profiles) into a single, analysis-ready daily-level dataset.

Author: <your name>
"""

import pandas as pd
import numpy as np


def _age_group(age):
    """
    Bucket a numeric age into one of the required age-group labels.

    Parameters
    ----------
    age : float or None
        The user's age in years. May be NaN/None if unknown.

    Returns
    -------
    str
        One of: 'Under 18', '18-25', '26-35', '36-45', '46-55',
        '56-65', 'Over 65', or 'Unknown' if age is missing/invalid.
    """
    if pd.isna(age):
        return 'Unknown'
    try:
        age = float(age)
    except (ValueError, TypeError):
        return 'Unknown'

    if age < 18:
        return 'Under 18'
    elif age <= 25:
        return '18-25'
    elif age <= 35:
        return '26-35'
    elif age <= 45:
        return '36-45'
    elif age <= 55:
        return '46-55'
    elif age <= 65:
        return '56-65'
    else:
        return 'Over 65'


def _load_health_data(path):
    """Load and clean the daily wearable/health metrics dataset."""
    health = pd.read_csv(path)
    health = health.drop_duplicates()

    health['user_id'] = health['user_id'].astype(str).str.strip()
    health['date'] = pd.to_datetime(health['date'], errors='coerce').dt.date

    # sleep_hours arrives as e.g. "8.8h" / "8.0H" -> strip unit suffix
    health['sleep_hours'] = (
        health['sleep_hours'].astype(str).str.strip()
        .str.replace('h', '', case=False, regex=False)
    )
    health['sleep_hours'] = pd.to_numeric(health['sleep_hours'], errors='coerce')

    for col in ['average_heart_rate', 'average_glucose', 'activity_level']:
        health[col] = pd.to_numeric(health[col], errors='coerce')

    return health


def _load_supplement_data(path):
    """Load and clean the daily supplement intake dataset."""
    supplements = pd.read_csv(path)
    supplements = supplements.drop_duplicates()

    supplements['user_id'] = supplements['user_id'].astype(str).str.strip()
    supplements['date'] = pd.to_datetime(supplements['date'], errors='coerce').dt.date
    supplements['supplement_name'] = supplements['supplement_name'].astype(str).str.strip()

    # Standardise dosage to grams regardless of source unit (g / mg)
    supplements['dosage'] = pd.to_numeric(supplements['dosage'], errors='coerce')
    unit = supplements['dosage_unit'].astype(str).str.strip().str.lower()
    supplements['dosage_grams'] = np.where(
        unit == 'mg', supplements['dosage'] / 1000,
        np.where(unit == 'g', supplements['dosage'], np.nan)
    )

    supplements['is_placebo'] = supplements['is_placebo'].apply(_to_bool)
    supplements['experiment_id'] = supplements['experiment_id'].astype(str).str.strip()

    return supplements[
        ['user_id', 'date', 'supplement_name', 'dosage_grams',
         'is_placebo', 'experiment_id']
    ]


def _to_bool(value):
    """Coerce assorted true/false encodings to a native bool (or NaN)."""
    if pd.isna(value):
        return np.nan
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ('true', '1', 'yes', 't'):
        return True
    if text in ('false', '0', 'no', 'f'):
        return False
    return np.nan


def _load_experiments(path):
    """Load and clean experiment metadata."""
    experiments = pd.read_csv(path)
    experiments = experiments.drop_duplicates()
    experiments['experiment_id'] = experiments['experiment_id'].astype(str).str.strip()
    experiments = experiments.rename(columns={'name': 'experiment_name'})
    return experiments[['experiment_id', 'experiment_name']]


def _load_profiles(path):
    """Load and clean user demographic/contact information."""
    profiles = pd.read_csv(path)
    profiles = profiles.drop_duplicates()
    profiles['user_id'] = profiles['user_id'].astype(str).str.strip()
    profiles['email'] = profiles['email'].astype(str).str.strip()
    profiles['age'] = pd.to_numeric(profiles['age'], errors='coerce')
    profiles['user_age_group'] = profiles['age'].apply(_age_group)
    return profiles[['user_id', 'email', 'user_age_group']]


def merge_all_data(health_path, supplement_path, experiments_path, profiles_path):
    """
    Clean and merge 1001-Experiments' four source datasets into a single
    comprehensive, daily-level DataFrame.

    Each row represents one user's combined health metrics and supplement
    usage for a single day. Days with multiple supplements logged produce
    multiple rows (one per supplement); days with no supplement intake are
    encoded as 'No intake'.

    Parameters
    ----------
    health_path : str
        Path to user_health_data.csv
    supplement_path : str
        Path to supplement_usage.csv
    experiments_path : str
        Path to experiments.csv
    profiles_path : str
        Path to user_profiles.csv

    Returns
    -------
    pandas.DataFrame
        Columns: user_id, date, email, user_age_group, experiment_name,
        supplement_name, dosage_grams, is_placebo, average_heart_rate,
        average_glucose, sleep_hours, activity_level
    """
    health = _load_health_data(health_path)
    supplements = _load_supplement_data(supplement_path)
    experiments = _load_experiments(experiments_path)
    profiles = _load_profiles(profiles_path)

    # Attach experiment names to each supplement entry
    supp_full = supplements.merge(experiments, on='experiment_id', how='left')
    supp_full = supp_full.drop(columns=['experiment_id'])

    # Outer-join health data with supplement usage on user_id + date, since
    # either side may have entries the other lacks (health-only or
    # supplement-only days), and a day may have multiple supplements logged.
    merged = health.merge(supp_full, on=['user_id', 'date'], how='outer')
    merged['supplement_name'] = merged['supplement_name'].fillna('No intake')

    # Attach demographic/contact info
    merged = merged.merge(profiles, on='user_id', how='left')

    # user_id, date, and email must never be missing
    merged = merged.dropna(subset=['user_id', 'date', 'email'])
    merged['user_age_group'] = merged['user_age_group'].fillna('Unknown')

    final_columns = [
        'user_id', 'date', 'email', 'user_age_group', 'experiment_name',
        'supplement_name', 'dosage_grams', 'is_placebo',
        'average_heart_rate', 'average_glucose', 'sleep_hours', 'activity_level'
    ]
    for col in final_columns:
        if col not in merged.columns:
            merged[col] = np.nan

    merged = merged[final_columns].drop_duplicates().reset_index(drop=True)
    return merged


if __name__ == '__main__':
    result = merge_all_data(
        'data/user_health_data.csv',
        'data/supplement_usage.csv',
        'data/experiments.csv',
        'data/user_profiles.csv',
    )
    print(result.shape)
    print(result.head())
