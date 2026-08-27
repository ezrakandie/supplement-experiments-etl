"""
Unit tests for merge_all_data.py

Run with:  pytest tests/
"""

import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from merge_all_data import merge_all_data, _age_group, _to_bool


@pytest.fixture
def sample_files(tmp_path):
    """Write small sample CSVs matching the real schema and return their paths."""
    health = pd.DataFrame({
        'user_id': ['u1', 'u1', 'u2'],
        'date': ['2024-01-01', '2024-01-02', '2024-01-01'],
        'average_heart_rate': [70.0, 72.5, 65.0],
        'average_glucose': [90.0, 95.0, 88.0],
        'sleep_hours': ['7.5h', '8.0H', '6.2h'],
        'activity_level': [3, 2, 4],
    })

    supplements = pd.DataFrame({
        'user_id': ['u1', 'u1'],
        'date': ['2024-01-01', '2024-01-01'],
        'supplement_name': ['Vitamin C', 'Zinc'],
        'dosage': [500.0, 0.25],
        'dosage_unit': ['mg', 'g'],
        'is_placebo': [False, True],
        'experiment_id': ['e1', 'e2'],
    })

    experiments = pd.DataFrame({
        'experiment_id': ['e1', 'e2'],
        'name': ['Focus', 'Sleep Quality'],
        'description': ['desc1', 'desc2'],
    })

    profiles = pd.DataFrame({
        'user_id': ['u1', 'u2'],
        'email': ['user1@example.com', 'user2@example.com'],
        'age': [30, None],
    })

    paths = {}
    for name, df in [
        ('health', health), ('supplements', supplements),
        ('experiments', experiments), ('profiles', profiles),
    ]:
        p = tmp_path / f'{name}.csv'
        df.to_csv(p, index=False)
        paths[name] = str(p)

    return paths


def test_age_group_boundaries():
    assert _age_group(17) == 'Under 18'
    assert _age_group(18) == '18-25'
    assert _age_group(25) == '18-25'
    assert _age_group(26) == '26-35'
    assert _age_group(65) == '56-65'
    assert _age_group(66) == 'Over 65'
    assert _age_group(None) == 'Unknown'
    assert _age_group(float('nan')) == 'Unknown'


def test_to_bool_handles_variants():
    assert _to_bool(True) is True
    assert _to_bool('False') is False
    assert _to_bool('yes') is True
    assert _to_bool(None) is None or pd.isna(_to_bool(None))


def test_merge_returns_dataframe(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    assert isinstance(result, pd.DataFrame)


def test_required_columns_present(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    expected_cols = [
        'user_id', 'date', 'email', 'user_age_group', 'experiment_name',
        'supplement_name', 'dosage_grams', 'is_placebo',
        'average_heart_rate', 'average_glucose', 'sleep_hours', 'activity_level'
    ]
    assert list(result.columns) == expected_cols


def test_no_missing_required_fields(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    assert result['user_id'].isna().sum() == 0
    assert result['date'].isna().sum() == 0
    assert result['email'].isna().sum() == 0


def test_days_without_supplement_marked_no_intake(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    # u1 on 2024-01-02 and u2 on 2024-01-01 took no supplements
    no_intake_rows = result[result['supplement_name'] == 'No intake']
    assert len(no_intake_rows) == 2


def test_dosage_converted_to_grams(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    vit_c_row = result[result['supplement_name'] == 'Vitamin C'].iloc[0]
    assert vit_c_row['dosage_grams'] == pytest.approx(0.5)  # 500mg -> 0.5g

    zinc_row = result[result['supplement_name'] == 'Zinc'].iloc[0]
    assert zinc_row['dosage_grams'] == pytest.approx(0.25)  # already in g


def test_missing_age_maps_to_unknown(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    u2_rows = result[result['user_id'] == 'u2']
    assert (u2_rows['user_age_group'] == 'Unknown').all()


def test_multiple_supplements_produce_multiple_rows(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    u1_day1_rows = result[
        (result['user_id'] == 'u1') & (result['date'].astype(str) == '2024-01-01')
    ]
    assert len(u1_day1_rows) == 2  # Vitamin C and Zinc, both logged that day


def test_no_duplicate_rows(sample_files):
    result = merge_all_data(
        sample_files['health'], sample_files['supplements'],
        sample_files['experiments'], sample_files['profiles'],
    )
    assert result.duplicated().sum() == 0
