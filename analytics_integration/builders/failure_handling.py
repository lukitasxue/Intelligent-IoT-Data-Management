"""
Partial failure handling for the shared Analytics response.

Extends the Week 5 envelope builder so that a failure in one analytics
component does not discard results from the other.

The Week 5 builder recognised two states: success and error. A failure
anywhere produced status "error" and, because the caller had nothing
usable to pass in, an empty alert list. That is wrong when only one of
the two components failed: the surviving component's alerts are valid
and the Backend should still receive them.

This module adds a third state, "partial_success", and a single entry
point that collects results from both components, tolerates a failure or
malformed output from either, and always produces a predictable envelope.

FAILURE MATRIX
--------------
    Models      Correlation   status            alerts          errors  http
    ok          ok            success           both            0       200
    failed      ok            partial_success   correlation     1       200
    ok          failed        partial_success   models          1       200
    failed      failed        error             none            2       503
    ok (empty)  ok (empty)    success           none            0       200
    malformed   ok            partial_success   correlation     1       200
    invalid input             error             none            1       400

An empty alert list is a successful analysis that found nothing. It is
never an error.
"""

from typing import Any, Callable

from analytics_integration.builders.envelope_builder import (
    build_analytics_response,
)

# Error codes. Clients branch on these, never on message text.
ERROR_CODES = {
    "COMPONENT_UNAVAILABLE":  503,  # component raised or could not be reached
    "MALFORMED_OUTPUT":       502,  # component returned something unusable
    "MISSING_REQUIRED_FIELD": 400,  # an alert is missing a contract field
    "INVALID_TIMESTAMP":      400,  # timestamp is absent or not ISO 8601
    "INVALID_INPUT":          400,  # the request itself is unusable
}

STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial_success"
STATUS_ERROR = "error"

# Fields every Draft V0.1 alert must carry.
REQUIRED_ALERT_FIELDS = ("timestamp", "alert_type", "target", "method", "source")

VALID_COMPONENTS = ("models", "correlation")


class AnalyticsFailure(Exception):
    """Raised when the request itself cannot be processed at all."""

    def __init__(self, code, message, field=None, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.details = details


def make_error(code, message, component=None, details=None):
    """Build one entry for the envelope's errors list."""
    entry = {"code": code, "message": message}
    if component is not None:
        entry["component"] = component
    if details is not None:
        entry["details"] = details
    return entry


def _is_iso_timestamp(value):
    """
    Return True if value is an ISO 8601 string Python can parse.

    Accepts a trailing Z, which fromisoformat does not handle directly
    before Python 3.11.
    """
    if not isinstance(value, str) or not value:
        return False
    from datetime import datetime
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_alerts(alerts, component):
    """
    Split a component's alerts into valid ones and errors.

    Returns (valid_alerts, errors). A malformed individual alert is
    dropped and recorded; it never raises, because one bad alert should
    not discard the rest of the batch.
    """
    if not isinstance(alerts, list):
        return [], [make_error(
            "MALFORMED_OUTPUT",
            f"The {component} adapter returned {type(alerts).__name__}, expected a list.",
            component=component,
            details={"received": type(alerts).__name__, "expected": "list"},
        )]

    valid = []
    errors = []

    for index, alert in enumerate(alerts):
        if not isinstance(alert, dict):
            errors.append(make_error(
                "MALFORMED_OUTPUT",
                f"Alert at index {index} is not an object.",
                component=component,
                details={"index": index, "received": type(alert).__name__},
            ))
            continue

        missing = [f for f in REQUIRED_ALERT_FIELDS if f not in alert]
        if missing:
            errors.append(make_error(
                "MISSING_REQUIRED_FIELD",
                f"Alert at index {index} is missing: {', '.join(missing)}.",
                component=component,
                details={"index": index, "missing": missing},
            ))
            continue

        if not _is_iso_timestamp(alert.get("timestamp")):
            errors.append(make_error(
                "INVALID_TIMESTAMP",
                f"Alert at index {index} has a timestamp that is not ISO 8601.",
                component=component,
                details={"index": index, "received": alert.get("timestamp")},
            ))
            continue

        valid.append(alert)

    return valid, errors


def collect_component(component, call, *args, **kwargs):
    """
    Run one component and never let it raise.

    Returns (alerts, errors). An exception becomes a COMPONENT_UNAVAILABLE
    entry so the other component's results survive.
    """
    if component not in VALID_COMPONENTS:
        raise ValueError(f"component must be one of {VALID_COMPONENTS}")

    if not callable(call):
        return [], [make_error(
            "COMPONENT_UNAVAILABLE",
            f"The {component} component is not callable.",
            component=component,
        )]

    try:
        raw = call(*args, **kwargs)
    except Exception as exc:                      # noqa: BLE001
        return [], [make_error(
            "COMPONENT_UNAVAILABLE",
            f"The {component} component failed: {exc}",
            component=component,
            details={"exception": type(exc).__name__},
        )]

    return validate_alerts(raw, component)


def resolve_status(models_ok, correlation_ok, errors):
    """
    Decide the envelope status.

    A component counts as ok if it returned without error, even when it
    returned no alerts. Finding nothing is a valid result.
    """
    if models_ok and correlation_ok:
        return STATUS_SUCCESS if not errors else STATUS_PARTIAL
    if models_ok or correlation_ok:
        return STATUS_PARTIAL
    return STATUS_ERROR


def resolve_http_status(status, errors):
    """Map the envelope status to an HTTP status code."""
    if status == STATUS_SUCCESS:
        return 200
    if status == STATUS_PARTIAL:
        return 200          # partial results are still usable
    # Total failure: report the most specific code present.
    codes = [ERROR_CODES.get(e.get("code"), 500) for e in errors]
    client_errors = [c for c in codes if 400 <= c < 500]
    if client_errors:
        return max(client_errors)
    return max(codes) if codes else 500


def build_response_with_failures(
    processed_items,
    models_call=None,
    correlation_call=None,
    models_args=None,
    correlation_args=None,
):
    """
    Run both components and build one predictable envelope.

    Neither component can prevent the other's results from being
    returned. Returns (envelope, http_status).
    """
    if (not isinstance(processed_items, int)
            or isinstance(processed_items, bool)
            or processed_items < 0):
        envelope = build_analytics_response(
            models_alerts=[],
            correlation_alerts=[],
            processed_items=0,
            errors=[make_error(
                "INVALID_INPUT",
                "processed_items must be a non-negative integer.",
                details={"received": repr(processed_items)},
            )],
        )
        envelope["status"] = STATUS_ERROR
        return envelope, 400

    models_args = models_args or {}
    correlation_args = correlation_args or {}

    models_alerts, models_errors = collect_component(
        "models", models_call, **models_args)
    correlation_alerts, correlation_errors = collect_component(
        "correlation", correlation_call, **correlation_args)

    # A component is "ok" only if it produced no errors at all.
    models_ok = not models_errors
    correlation_ok = not correlation_errors

    errors = models_errors + correlation_errors
    status = resolve_status(models_ok, correlation_ok, errors)

    envelope = build_analytics_response(
        models_alerts=models_alerts,
        correlation_alerts=correlation_alerts,
        processed_items=processed_items,
        errors=errors,
    )

    # The Week 5 builder only knows success and error. Overwrite with the
    # three-state value so a partial failure is distinguishable.
    envelope["status"] = status

    return envelope, resolve_http_status(status, errors)
