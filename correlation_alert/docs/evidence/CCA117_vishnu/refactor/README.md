# CCA117 Refactored API Validation Evidence

CCA117 was adapted to the merged CCA118 correlation service architecture rather than restoring the previous standalone implementation.

The work extends the existing `server.py`, `correlation.py`, and `tests/test_server.py` components.

Implemented behaviour includes:

- HTTP 400 for malformed caller input.
- Structured machine-readable error codes.
- CSV extension and parsing validation.
- Timestamp-column validation.
- Selected-stream validation.
- Supported correlation-method validation.
- Existing threshold and window validation.
- 5 MB request/upload limit.
- HTTP 422 when valid input cannot produce a correlation window.
- HTTP 200 when analysis succeeds, including successful zero-alert results.
- Existing safe Flask debug configuration remains unchanged.

Testing:

- CCA118 baseline: 66 passing tests.
- CCA117 refactored result: 74 passing tests.
- Tests use the existing `correlation_alert/tests/` pytest suite and the same command used by CI.
