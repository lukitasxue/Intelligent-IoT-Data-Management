"""
Reusable pytest fixtures for Analytics Integration failure-handling tests.
"""

import pytest


@pytest.fixture
def models_alert_fixture():
    return {
        "timestamp": "2026-08-18T10:00:00Z",
        "alert_type": "POINTWISE_ANOMALY",
        "target": {
            "entity_id": "sensor_node_01",
            "metrics": ["temperature"],
        },
        "method": "IsolationForest",
        "message": "Anomaly detected in temperature.",
        "source": {
            "component": "models",
        },
    }


@pytest.fixture
def correlation_alert_fixture():
    return {
        "timestamp": "2026-08-18T10:05:00Z",
        "alert_type": "CORRELATION_CHANGE",
        "target": {
            "entity_id": None,
            "metrics": ["temperature", "pressure"],
        },
        "method": "Rolling_Pearson_Correlation",
        "message": "Correlation between temperature and pressure changed.",
        "source": {
            "component": "correlation",
        },
    }


@pytest.fixture
def empty_alerts_fixture():
    return []
