import pandas as pd
import pytest

from data_science.input_validator import InputValidationError, validate_input


def make_valid_data():
    return pd.DataFrame({
        "timestamp": pd.date_range(
            "2026-09-12 10:00:00",
            periods=20,
            freq="min"
        ),
        "sensor_value": range(20),
    })


def test_valid_input():
    result = validate_input(
        make_valid_data(),
        timestamp_col="timestamp",
        sensor_cols=["sensor_value"],
        min_readings=20,
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 20
    assert "sensor_value" in result.columns


def test_none_input():
    with pytest.raises(InputValidationError, match="DataFrame"):
        validate_input(None)


def test_empty_input():
    df = pd.DataFrame(columns=["timestamp", "sensor_value"])

    with pytest.raises(InputValidationError, match="empty"):
        validate_input(df)


def test_missing_sensor_column():
    df = make_valid_data().drop(columns=["sensor_value"])

    with pytest.raises(
        InputValidationError,
        match="Declared sensor columns",
    ):
        validate_input(
            df,
            sensor_cols=["sensor_value"],
        )


def test_missing_timestamp_column():
    df = make_valid_data().drop(columns=["timestamp"])

    result = validate_input(
        df,
        sensor_cols=["sensor_value"],
    )

    assert isinstance(result.index, pd.DatetimeIndex)


def test_insufficient_readings():
    with pytest.raises(
        InputValidationError,
        match="Not enough readings",
    ):
        validate_input(
            make_valid_data().head(5),
            sensor_cols=["sensor_value"],
            min_readings=20,
        )


def test_missing_sensor_value():
    df = make_valid_data()
    df.loc[5, "sensor_value"] = None

    with pytest.raises(InputValidationError, match="Missing"):
        validate_input(
            df,
            sensor_cols=["sensor_value"],
        )


def test_invalid_sensor_value():
    df = make_valid_data()
    df["sensor_value"] = "invalid"

    with pytest.raises(InputValidationError, match="not numeric"):
        validate_input(
            df,
            sensor_cols=["sensor_value"],
        )


def test_invalid_timestamp():
    df = make_valid_data()

    # Convert to object so pandas allows an invalid string value.
    df["timestamp"] = df["timestamp"].astype(object)
    df.loc[5, "timestamp"] = "invalid timestamp"

    with pytest.raises(
        InputValidationError,
        match="could not be parsed",
    ):
        validate_input(
            df,
            timestamp_col="timestamp",
            sensor_cols=["sensor_value"],
        )


def test_multiple_sensor_columns():
    df = make_valid_data()
    df["sensor_2"] = range(20, 40)

    result = validate_input(
        df,
        timestamp_col="timestamp",
        sensor_cols=["sensor_value", "sensor_2"],
        min_readings=20,
    )

    assert isinstance(result, pd.DataFrame)
    assert "sensor_value" in result.columns
    assert "sensor_2" in result.columns


def test_invalid_dataframe_type():
    with pytest.raises(InputValidationError, match="DataFrame"):
        validate_input(
            {"timestamp": [], "sensor_value": []}
        )