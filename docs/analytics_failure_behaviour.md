# AI: 025 – Analytics Integration Failure Behaviour & Contract Impact

## 1. Objective

Define the operational and schema contract behaviour of the Analytics Integration layer when handling upstream service errors, malformed responses, empty outputs, and partial service availability across Models and Correlation microservices.

---

## 2. Failure-Behaviour Matrix

| Scenario Code | Failure Scenario | Trigger Condition | HTTP Status | Response Status | System Behaviour & Envelope Response |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SC-01** | Upstream Service Unavailable | Models or Correlation microservice offline, connection refused, or gateway timeout (>5s). | `503 Service Unavailable` / `504 Gateway Timeout` | `"error"` | Log critical network failure. Return error envelope with service name, timestamp, and clear diagnostic message. Do not return mock data. |
| **SC-02** | Partial Microservice Failure | One microservice (e.g., Models) succeeds, but another (e.g., Correlation) fails or times out. | `207 Multi-Status` or `200 OK` (with partial envelope) | `"partial_success"` | Log warning. Return successful component alerts in `alerts[]`. Populate `errors[]` with failed service diagnostic details. Backend can render available alerts with a degraded banner. |
| **SC-03** | Upstream Bad Request / Schema Violation | Upstream microservice returns 400, malformed JSON, or fails internal schema validation. | `502 Bad Gateway` | `"error"` | Catch parsing error, log payload discrepancy, and return error envelope without crashing the Express adapter pipeline. |
| **SC-04** | Empty Input / Insufficient Sensor Records | Ingestion payload contains no rows or fewer records than required by rolling window/baseline. | `400 Bad Request` | `"error"` | Pre-validate inputs at adapter layer before dispatching upstream. Return actionable error message to user (e.g., "Insufficient data points"). |
| **SC-05** | No Anomalies or Correlations Detected | Analytics services execute successfully, but no thresholds are breached. | `200 OK` | `"success"` | Return empty `alerts: []` array with standard metadata. This is normal execution, not an error state. |
| **SC-06** | Internal Adapter Runtime Exception | Unhandled runtime exception within the Analytics Integration parsing or aggregation logic. | `500 Internal Server Error` | `"error"` | Wrap with top-level error handler. Return generic sanitized error message to client; log stack trace internally. |

---

## 3. Contract Envelope Specifications

### 3.1 Partial Success Response Envelope (`SC-02`)

```json
{
  "status": "partial_success",
  "alerts": [
    {
      "id": "alert-models-001",
      "type": "ANOMALY_POINTWISE",
      "severity": "CRITICAL",
      "stream_id": "sensor_temp_01",
      "timestamp": "2026-09-02T14:30:00Z",
      "details": {
        "score": -0.82,
        "description": "Temperature exceeded operational threshold."
      }
    }
  ],
  "errors": [
    {
      "service": "correlation",
      "status": 503,
      "message": "Correlation service timed out after 5000ms."
    }
  ]
}
