from __future__ import annotations

from datetime import datetime
from typing import Any

# Standardized Enums & Constants
REQUIRED_FIELDS = {
    "timestamp",
    "alert_type",
    "target",
    "method",
    "message",
    "source",
}

ALERT_TYPES = {"POINTWISE_ANOMALY", "CORRELATION_CHANGE"}
SEVERITY_LEVELS = {"LOW", "MEDIUM", "HIGH"}


def is_iso8601_utc(timestamp_str: Any) -> bool:
    """Validate if a timestamp string is valid ISO 8601 UTC."""
    if not isinstance(timestamp_str, str):
        return False
    try:
        # Normalize Z to +00:00 for datetime parsing
        ts = timestamp_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        # Verify it has UTC timezone offset (+00:00)
        return dt.tzinfo is not None and dt.utcoffset().total_seconds() == 0
    except (ValueError, TypeError):
        return False


def validate_target(target: Any) -> list[str]:
    """Validate target payload structure."""
    errors = []
    if not isinstance(target, dict):
        return ["target must be an object"]

    if "metrics" not in target or not isinstance(target["metrics"], list) or len(target["metrics"]) == 0:
        errors.append("target.metrics must be a non-empty list of strings")

    return errors


def validate_source(source: Any) -> list[str]:
    """Validate source payload structure."""
    errors = []
    if not isinstance(source, dict):
        return ["source must be an object"]

    if "component" not in source or not isinstance(source["component"], str) or not source["component"].strip():
        errors.append("source.component must be a non-empty string")

    return errors


def validate_time_window(time_window: Any) -> list[str]:
    """Validate optional time_window payload structure."""
    errors = []
    if time_window is None:
        return errors

    if not isinstance(time_window, dict):
        return ["time_window must be an object or null"]

    start = time_window.get("start")
    end = time_window.get("end")

    if start is not None and not is_iso8601_utc(start):
        errors.append("time_window.start must be a valid ISO 8601 UTC timestamp")

    if end is not None and not is_iso8601_utc(end):
        errors.append("time_window.end must be a valid ISO 8601 UTC timestamp")

    return errors


def validate_alert(alert: Any) -> list[str]:
    """
    Validate Draft V0.1 Alert dictionary object.
    """
    errors = []

    if not isinstance(alert, dict):
        return ["alert must be an object"]

    # Check for presence of required envelope fields
    missing_fields = [field for field in REQUIRED_FIELDS if field not in alert]
    if missing_fields:
        for field in missing_fields:
            errors.append(f"{field} is required")
        return errors

    # Core attribute validation
    if not is_iso8601_utc(alert["timestamp"]):
        errors.append("timestamp must be a valid ISO 8601 UTC timestamp")

    # String normalization prevents case/whitespace mismatch bugs
    alert_type = str(alert["alert_type"]).strip().upper() if alert["alert_type"] is not None else None
    if alert_type not in ALERT_TYPES:
        errors.append("alert_type must be POINTWISE_ANOMALY or CORRELATION_CHANGE")

    errors.extend(validate_target(alert["target"]))

    if not isinstance(alert["method"], str) or not alert["method"].strip():
        errors.append("method must be a non-empty string")

    if not isinstance(alert["message"], str) or not alert["message"].strip():
        errors.append("message must be a non-empty string")

    errors.extend(validate_source(alert["source"]))

    # Optional attribute validation
    if "score" in alert:
        score = alert["score"]
        if score is not None and (
            not isinstance(score, (int, float)) or isinstance(score, bool)
        ):
            errors.append("score must be numeric or null")

    if "score_metadata" in alert:
        score_metadata = alert["score_metadata"]
        if score_metadata is not None and not isinstance(score_metadata, dict):
            errors.append("score_metadata must be an object or null")

    if "severity" in alert:
        severity = alert["severity"]
        if severity is not None:
            normalized_severity = str(severity).strip().upper() if isinstance(severity, str) else None
            if normalized_severity not in SEVERITY_LEVELS:
                errors.append("severity must be LOW, MEDIUM, HIGH or null")

    if "time_window" in alert:
        errors.extend(validate_time_window(alert["time_window"]))

    if "supporting_values" in alert:
        supporting_values = alert["supporting_values"]
        if supporting_values is not None and not isinstance(supporting_values, dict):
            errors.append("supporting_values must be an object or null")

    if "alert_id" in alert:
        alert_id = alert["alert_id"]
        if alert_id is not None and not isinstance(alert_id, str):
            errors.append("alert_id must be a string or null")

    return errors


def validate_response(response: Any) -> list[str]:
    """
    Validate an overall Draft V0.1 Analytics response payload or alert collection.
    """
    errors = []

    if not isinstance(response, dict):
        if isinstance(response, list):
            for idx, item in enumerate(response):
                alert_errors = validate_alert(item)
                for err in alert_errors:
                    errors.append(f"alert[{idx}]: {err}")
            return errors
        return ["response must be an object or list"]

    # Top-level pipeline envelope validation
    if "alerts" in response:
        alerts = response["alerts"]
        if not isinstance(alerts, list):
            errors.append("response.alerts must be a list")
        else:
            for idx, alert in enumerate(alerts):
                alert_errors = validate_alert(alert)
                for err in alert_errors:
                    errors.append(f"alert[{idx}]: {err}")
    else:
        # If response is a single alert dictionary directly
        errors.extend(validate_alert(response))

    if "status" in response and not isinstance(response["status"], str):
        errors.append("response.status must be a string")

    if "summary" in response and not isinstance(response["summary"], dict):
        errors.append("response.summary must be an object")

    return errors