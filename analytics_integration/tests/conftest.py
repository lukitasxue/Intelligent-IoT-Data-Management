import pytest


@pytest.fixture
def valid_iot_payload():
    """Returns a valid sensor payload."""
    return {
        "sensor_id": "SENSOR_001",
        "readings": [22.4, 22.8, 23.1],
        "timestamps": [
            "2026-09-12T10:00:00Z",
            "2026-09-12T10:01:00Z",
            "2026-09-12T10:02:00Z",
        ],
    }


@pytest.fixture
def missing_fields_payload():
    """Returns a payload missing required keys for Person 1's validation tests."""
    return {"sensor_id": "SENSOR_001"}


@pytest.fixture
def corrupted_payload():
    """Returns invalid data types to test fallback handling."""
    return {"sensor_id": 12345, "readings": "invalid_string_instead_of_list"}