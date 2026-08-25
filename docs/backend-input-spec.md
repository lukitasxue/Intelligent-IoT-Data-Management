# Analytics Integration: Backend Analytics Input Specification (AI: 030)

## Target Endpoint

* **URL Path:** `/detect-correlation-alert`
* **HTTP Method:** `POST`
* **Content-Type:** `application/json` (Transitioning from `multipart/form-data` CSV uploads to support automated backend integration)

---

## Minimum Required JSON Request Schema

```json
{
  "sensor_id": "sensor_1350261",
  "time_window": {
    "start_time": "2026-08-24T10:00:00Z",
    "end_time": "2026-08-24T10:30:00Z"
  },
  "data_points": [
    { "timestamp": "2026-08-24T10:00:00Z", "value": 24.5 },
    { "timestamp": "2026-08-24T10:01:00Z", "value": 25.1 }
  ],
  "parameters": {
    "detectors": ["IsolationForestDetector"],
    "sensitivity": 0.8
  }

}
```

| Field | Type | Required? | Notes |
| :--- | :--- | :--- | :--- |
| `sensor_id` | String | Yes |  ID or channel name we're querying |
| `time_window` | Object | Yes | Holds `start_time` and `end_time` |
| `time_window.start_time` | String | Yes | ISO string timestamp (UTC) |
| `time_window.end_time` | String | Yes | ISO string timestamp (UTC) |
| `data_points` | Array | Yes | Array of `{ timestamp, value }` objects |
| `data_points[].timestamp` | String | Yes | Reading timestamp |
| `data_points[].value` | Number | Yes | Numeric reading. Needs null/NaN check from Express first |
| `parameters` | Object | No | Optional detector configs |
| `parameters.detectors` | Array | No | ML models to run. Defaults to `["IsolationForestDetector"]` |
| `parameters.sensitivity` | Number | No | Threshold multiplier between 0 and 1. Defaults to 0.8 |



## Backend Rules & Assumptions

* **Clean the Data First:** Express.js needs to strip out any `null`, `undefined`, or `NaN` values from `data_points` before sending the request. If bad data gets sent over, Flask models (like `VolatilityShiftADDetector`) will crash.
* **Standardize Timestamps:** Express.js must convert all database timestamps into clean UTC ISO 8601 strings (e.g., `2026-08-24T10:00:00Z`).
* **Keep Batches Under 1,000 Points:** Send a maximum of 1,000 data points per request to keep response times fast and avoid overloading the service.
* **Detector Fallback:** If Express doesn't send a specific detector name in `parameters.detectors`, Flask will just default to running `IsolationForestDetector`.