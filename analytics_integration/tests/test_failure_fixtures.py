"""
Additional failure-handling tests using reusable pytest fixtures.

These tests confirm that the shared Models and Correlation fixtures work
correctly with the Analytics partial-failure handling implementation.
"""

from analytics_integration.builders.failure_handling import (
    STATUS_PARTIAL,
    STATUS_SUCCESS,
    build_response_with_failures,
)


def test_reusable_fixtures_both_services_success(
    models_alert_fixture,
    correlation_alert_fixture,
):
    """Both reusable alert fixtures should produce a successful response."""

    envelope, http = build_response_with_failures(
        processed_items=20,
        models_call=lambda: [models_alert_fixture],
        correlation_call=lambda: [correlation_alert_fixture],
    )

    assert http == 200
    assert envelope["status"] == STATUS_SUCCESS
    assert envelope["summary"]["alert_count"] == 2
    assert envelope["errors"] == []


def test_reusable_fixture_models_failure(
    correlation_alert_fixture,
):
    """Correlation fixture should survive when the Models service fails."""

    def failed_models_call():
        raise RuntimeError("Models service unavailable")

    envelope, http = build_response_with_failures(
        processed_items=20,
        models_call=failed_models_call,
        correlation_call=lambda: [correlation_alert_fixture],
    )

    assert http == 200
    assert envelope["status"] == STATUS_PARTIAL
    assert envelope["summary"]["alert_count"] == 1
    assert envelope["alerts"][0]["alert_type"] == "CORRELATION_CHANGE"


def test_reusable_fixture_correlation_failure(
    models_alert_fixture,
):
    """Models fixture should survive when the Correlation service fails."""

    def failed_correlation_call():
        raise RuntimeError("Correlation service unavailable")

    envelope, http = build_response_with_failures(
        processed_items=20,
        models_call=lambda: [models_alert_fixture],
        correlation_call=failed_correlation_call,
    )

    assert http == 200
    assert envelope["status"] == STATUS_PARTIAL
    assert envelope["summary"]["alert_count"] == 1
    assert envelope["alerts"][0]["alert_type"] == "POINTWISE_ANOMALY"


def test_reusable_empty_fixture_is_success(
    empty_alerts_fixture,
):
    """Empty reusable fixtures should represent a successful no-alert result."""

    envelope, http = build_response_with_failures(
        processed_items=20,
        models_call=lambda: empty_alerts_fixture,
        correlation_call=lambda: empty_alerts_fixture,
    )

    assert http == 200
    assert envelope["status"] == STATUS_SUCCESS
    assert envelope["alerts"] == []
    assert envelope["summary"]["alert_count"] == 0
