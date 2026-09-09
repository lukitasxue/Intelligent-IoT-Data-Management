"""
Tests for partial failure handling in the Analytics response.

Run with:
    python -m pytest analytics_integration/tests/test_failure_handling.py -v

These tests use stub components rather than the real Models or
Correlation pipelines, so they cover the failure matrix without needing
either service to be running.
"""

import json

import pytest

from analytics_integration.builders.failure_handling import (
    STATUS_ERROR,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    build_response_with_failures,
    validate_alerts,
)


# --- helpers ------------------------------------------------------------

def models_alert():
    return {
        "timestamp": "2026-08-18T10:00:00Z",
        "alert_type": "POINTWISE_ANOMALY",
        "target": {"entity_id": "sensor_node_01", "metrics": ["temperature"]},
        "method": "IsolationForest",
        "message": "Anomaly detected in temperature.",
        "source": {"component": "models"},
    }


def correlation_alert():
    return {
        "timestamp": "2026-08-18T10:05:00Z",
        "alert_type": "CORRELATION_CHANGE",
        "target": {"entity_id": None, "metrics": ["temperature", "pressure"]},
        "method": "Rolling_Pearson_Correlation",
        "message": "Correlation between temperature and pressure changed.",
        "source": {"component": "correlation"},
    }


def working(alerts):
    """A component that succeeds and returns the given alerts."""
    return lambda: list(alerts)


def failing(message="service unreachable"):
    """A component that raises."""
    def _call():
        raise RuntimeError(message)
    return _call


def codes(envelope):
    return [e["code"] for e in envelope["errors"]]


def components(envelope):
    return [e.get("component") for e in envelope["errors"]]


# --- both components healthy -------------------------------------------

def test_both_succeed_returns_success():
    envelope, http = build_response_with_failures(
        processed_items=100,
        models_call=working([models_alert()]),
        correlation_call=working([correlation_alert()]),
    )
    assert http == 200
    assert envelope["status"] == STATUS_SUCCESS
    assert envelope["summary"]["alert_count"] == 2
    assert envelope["errors"] == []


def test_empty_alert_list_is_success_not_error():
    """Finding nothing is a valid result, not a failure."""
    envelope, http = build_response_with_failures(
        processed_items=100,
        models_call=working([]),
        correlation_call=working([]),
    )
    assert http == 200
    assert envelope["status"] == STATUS_SUCCESS
    assert envelope["alerts"] == []
    assert envelope["summary"]["alert_count"] == 0
    assert envelope["errors"] == []
    assert envelope["summary"]["processed_items"] == 100


# --- one component fails ------------------------------------------------

def test_models_failure_keeps_correlation_alerts():
    envelope, http = build_response_with_failures(
        processed_items=50,
        models_call=failing(),
        correlation_call=working([correlation_alert()]),
    )
    assert http == 200
    assert envelope["status"] == STATUS_PARTIAL
    assert envelope["summary"]["alert_count"] == 1
    assert envelope["alerts"][0]["alert_type"] == "CORRELATION_CHANGE"
    assert codes(envelope) == ["COMPONENT_UNAVAILABLE"]
    assert components(envelope) == ["models"]


def test_correlation_failure_keeps_models_alerts():
    envelope, http = build_response_with_failures(
        processed_items=50,
        models_call=working([models_alert()]),
        correlation_call=failing(),
    )
    assert http == 200
    assert envelope["status"] == STATUS_PARTIAL
    assert envelope["summary"]["alert_count"] == 1
    assert envelope["alerts"][0]["alert_type"] == "POINTWISE_ANOMALY"
    assert components(envelope) == ["correlation"]


def test_partial_failure_names_the_failed_component():
    """Backend needs to know which component was lost, not just that one was."""
    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=failing("connection refused"),
        correlation_call=working([correlation_alert()]),
    )
    error = envelope["errors"][0]
    assert error["component"] == "models"
    assert error["details"]["exception"] == "RuntimeError"


# --- both components fail -----------------------------------------------

def test_both_fail_returns_error_and_503():
    envelope, http = build_response_with_failures(
        processed_items=50,
        models_call=failing(),
        correlation_call=failing(),
    )
    assert http == 503
    assert envelope["status"] == STATUS_ERROR
    assert envelope["alerts"] == []
    assert len(envelope["errors"]) == 2
    assert set(components(envelope)) == {"models", "correlation"}


def test_both_fail_still_reports_processed_items():
    envelope, _ = build_response_with_failures(
        processed_items=250,
        models_call=failing(),
        correlation_call=failing(),
    )
    assert envelope["summary"]["processed_items"] == 250


# --- malformed adapter output -------------------------------------------

def test_adapter_returning_dict_is_malformed():
    envelope, http = build_response_with_failures(
        processed_items=10,
        models_call=lambda: {"not": "a list"},
        correlation_call=working([correlation_alert()]),
    )
    assert http == 200
    assert envelope["status"] == STATUS_PARTIAL
    assert codes(envelope) == ["MALFORMED_OUTPUT"]
    assert envelope["summary"]["alert_count"] == 1


def test_adapter_returning_none_is_malformed():
    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=lambda: None,
        correlation_call=working([]),
    )
    assert envelope["status"] == STATUS_PARTIAL
    assert codes(envelope) == ["MALFORMED_OUTPUT"]


def test_non_object_alert_is_dropped_not_fatal():
    """One bad alert must not discard the good ones beside it."""
    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=lambda: [models_alert(), "not an alert"],
        correlation_call=working([]),
    )
    assert envelope["summary"]["alert_count"] == 1
    assert codes(envelope) == ["MALFORMED_OUTPUT"]


# --- required fields and timestamps -------------------------------------

def test_missing_required_field_is_reported():
    broken = models_alert()
    del broken["method"]

    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=lambda: [broken],
        correlation_call=working([]),
    )
    assert codes(envelope) == ["MISSING_REQUIRED_FIELD"]
    assert envelope["errors"][0]["details"]["missing"] == ["method"]
    assert envelope["summary"]["alert_count"] == 0


def test_missing_several_fields_lists_all_of_them():
    broken = models_alert()
    del broken["method"]
    del broken["source"]

    _, errors = validate_alerts([broken], "models")
    assert set(errors[0]["details"]["missing"]) == {"method", "source"}


def test_invalid_timestamp_is_reported():
    broken = correlation_alert()
    broken["timestamp"] = "not-a-date"

    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=working([]),
        correlation_call=lambda: [broken],
    )
    assert codes(envelope) == ["INVALID_TIMESTAMP"]
    assert envelope["errors"][0]["details"]["received"] == "not-a-date"


def test_null_timestamp_is_reported():
    broken = correlation_alert()
    broken["timestamp"] = None

    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=working([]),
        correlation_call=lambda: [broken],
    )
    assert codes(envelope) == ["INVALID_TIMESTAMP"]


def test_valid_alert_survives_beside_an_invalid_one():
    broken = models_alert()
    broken["timestamp"] = "13/08/2026"

    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=lambda: [models_alert(), broken],
        correlation_call=working([]),
    )
    assert envelope["summary"]["alert_count"] == 1
    assert codes(envelope) == ["INVALID_TIMESTAMP"]


# --- invalid input ------------------------------------------------------

def test_negative_processed_items_returns_400():
    envelope, http = build_response_with_failures(
        processed_items=-1,
        models_call=working([models_alert()]),
        correlation_call=working([]),
    )
    assert http == 400
    assert envelope["status"] == STATUS_ERROR
    assert codes(envelope) == ["INVALID_INPUT"]


def test_processed_items_wrong_type_returns_400():
    envelope, http = build_response_with_failures(
        processed_items="one hundred",
        models_call=working([]),
        correlation_call=working([]),
    )
    assert http == 400
    assert codes(envelope) == ["INVALID_INPUT"]


# --- envelope shape is always predictable -------------------------------

@pytest.mark.parametrize("models_call,correlation_call", [
    (working([models_alert()]), working([correlation_alert()])),
    (failing(), working([correlation_alert()])),
    (working([models_alert()]), failing()),
    (failing(), failing()),
    (working([]), working([])),
    (lambda: "junk", working([])),
])
def test_envelope_shape_is_stable_across_every_outcome(models_call, correlation_call):
    """
    Whatever happens, Backend receives the same keys with the same types.
    """
    envelope, http = build_response_with_failures(
        processed_items=10,
        models_call=models_call,
        correlation_call=correlation_call,
    )

    assert set(envelope) == {"status", "generated_at", "alerts", "summary", "errors"}
    assert envelope["status"] in (STATUS_SUCCESS, STATUS_PARTIAL, STATUS_ERROR)
    assert isinstance(envelope["alerts"], list)
    assert isinstance(envelope["errors"], list)
    assert set(envelope["summary"]) == {"processed_items", "alert_count"}
    assert envelope["summary"]["alert_count"] == len(envelope["alerts"])
    assert isinstance(http, int)

    # Must survive strict JSON serialisation on the Node side.
    json.dumps(envelope)


def test_every_error_entry_has_a_code_and_message():
    envelope, _ = build_response_with_failures(
        processed_items=10,
        models_call=failing(),
        correlation_call=lambda: {"bad": "shape"},
    )
    for error in envelope["errors"]:
        assert isinstance(error["code"], str) and error["code"]
        assert isinstance(error["message"], str) and error["message"]
