"""
Additional failure-handling tests using reusable pytest fixtures.

These tests confirm that the shared Models and Correlation fixtures work
correctly with the Analytics partial-failure handling implementation.
"""

import pytest


# The failure-handling implementation is provided by PR #12.
# Until that implementation is available on main, these tests are skipped
# instead of failing during test collection.
failure_handling = pytest.importorskip(
    "analytics_integration.builders.failure_handling",
    reason="Requires the partial failure-handling implementation from PR #12",
)

STATUS_PARTIAL = failure_handling.STATUS_PARTIAL
STATUS_SUCCESS = failure_handling.STATUS_SUCCESS
build_response_with_failures = failure_handling.build_response_with_failures


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

    assert any(
        error.get("component") == "models"
        for error in envelope["errors"]
    )


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

    assert any(
        error.get("component") == "correlation"
        for error in envelope["errors"]
    )


def test_reusable_empty_fixture_is_success(
    empty_alert_fixture,
):
    """Empty outputs from both services should still be a valid success."""

    envelope, http = build_response_with_failures(
        processed_items=20,
        models_call=lambda: empty_alert_fixture,
        correlation_call=lambda: empty_alert_fixture,
    )

    assert http == 200
    assert envelope["status"] == STATUS_SUCCESS
    assert envelope["summary"]["alert_count"] == 0
    assert envelope["errors"] == []
