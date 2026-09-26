import pytest

import analytics_integration.pipeline as pipeline


def test_models_runtime_failure(monkeypatch):
    """
    Check that AIntg detects a Models engine failure
    and raises a clear RuntimeError.
    """

    def fake_run_detector(*args, **kwargs):
        return {
            "status": "error",
            "error": "simulated models failure",
        }

    monkeypatch.setattr(
        pipeline,
        "run_detector",
        fake_run_detector,
    )

    df = pipeline.pd.DataFrame(
        {
            "time": pipeline.pd.date_range(
                start="2026-09-14 10:00:00",
                periods=25,
                freq="min",
            ),
            "sensor_1": [20.0] * 25,
        }
    )

    with pytest.raises(
        RuntimeError,
        match="Models runtime failed",
    ):
        pipeline.run_models_path(
            df=df,
            timestamp_col="time",
            model_metric="sensor_1",
        )


def test_correlation_service_failure(monkeypatch):
    """
    Check that AIntg detects a Correlation API failure
    and raises a clear RuntimeError.
    """

    class FakeResponse:
        status_code = 500

        def get_json(self):
            return {
                "status": "error",
                "error": "simulated correlation failure",
            }

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeApp:
        def __init__(self):
            self.config = {}

        def test_client(self):
            return FakeClient()

    monkeypatch.setattr(
        pipeline,
        "create_app",
        lambda *args, **kwargs: FakeApp(),
    )

    df = pipeline.pd.DataFrame(
        {
            "time": pipeline.pd.date_range(
                start="2026-09-14 10:00:00",
                periods=25,
                freq="min",
            ),
            "sensor_1": [20.0] * 25,
            "sensor_2": [30.0] * 25,
        }
    )

    with pytest.raises(
        RuntimeError,
        match="Correlation API failed",
    ):
        pipeline.run_correlation_path(
            df=df,
            timestamp_col="time",
            correlation_streams=["sensor_1", "sensor_2"],
        )


def test_malformed_models_response(monkeypatch):
    """
    Check that AIntg rejects a malformed Models response
    instead of treating it as a successful analytics result.
    """

    def fake_run_detector(*args, **kwargs):
        return {
            "unexpected_field": "invalid models response",
        }

    monkeypatch.setattr(
        pipeline,
        "run_detector",
        fake_run_detector,
    )

    df = pipeline.pd.DataFrame(
        {
            "time": pipeline.pd.date_range(
                start="2026-09-14 10:00:00",
                periods=25,
                freq="min",
            ),
            "sensor_1": [20.0] * 25,
        }
    )

    with pytest.raises(
        RuntimeError,
        match="Models runtime failed",
    ):
        pipeline.run_models_path(
            df=df,
            timestamp_col="time",
            model_metric="sensor_1",
        )


def test_malformed_correlation_response(monkeypatch):
    """
    Check that AIntg rejects a malformed Correlation response
    instead of treating it as a valid analytics result.
    """

    class FakeResponse:
        status_code = 200

        def get_json(self):
            return {
                "unexpected_field": "invalid correlation response",
            }

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeApp:
        def __init__(self):
            self.config = {}

        def test_client(self):
            return FakeClient()

    monkeypatch.setattr(
        pipeline,
        "create_app",
        lambda *args, **kwargs: FakeApp(),
    )

    df = pipeline.pd.DataFrame(
        {
            "time": pipeline.pd.date_range(
                start="2026-09-14 10:00:00",
                periods=25,
                freq="min",
            ),
            "sensor_1": [20.0] * 25,
            "sensor_2": [30.0] * 25,
        }
    )

    with pytest.raises(
        RuntimeError,
        match="Correlation API returned an unexpected response",
    ):
        pipeline.run_correlation_path(
            df=df,
            timestamp_col="time",
            correlation_streams=["sensor_1", "sensor_2"],
        )
def test_models_adapter_failure(monkeypatch):
    """
    Check that AIntg surfaces a Models adapter failure
    instead of silently continuing.
    """

    def fake_run_detector(*args, **kwargs):
        return {
            "status": "success",
            "results": [],
        }

    def fake_adapt_models_output(*args, **kwargs):
        raise ValueError("simulated models adapter failure")

    monkeypatch.setattr(
        pipeline,
        "run_detector",
        fake_run_detector,
    )

    monkeypatch.setattr(
        pipeline,
        "adapt_models_output",
        fake_adapt_models_output,
    )

    df = pipeline.pd.DataFrame(
        {
            "time": pipeline.pd.date_range(
                start="2026-09-14 10:00:00",
                periods=25,
                freq="min",
            ),
            "sensor_1": [20.0] * 25,
        }
    )

    with pytest.raises(
        ValueError,
        match="simulated models adapter failure",
    ):
        pipeline.run_models_path(
            df=df,
            timestamp_col="time",
            model_metric="sensor_1",
        )
def test_unexpected_models_exception(monkeypatch):
    """
    Check that an unexpected Models service exception
    is not silently ignored by AIntg.
    """

    def fake_run_detector(*args, **kwargs):
        raise RuntimeError("simulated unexpected models exception")

    monkeypatch.setattr(
        pipeline,
        "run_detector",
        fake_run_detector,
    )

    df = pipeline.pd.DataFrame(
        {
            "time": pipeline.pd.date_range(
                start="2026-09-14 10:00:00",
                periods=25,
                freq="min",
            ),
            "sensor_1": [20.0] * 25,
        }
    )

    with pytest.raises(
        RuntimeError,
        match="simulated unexpected models exception",
    ):
        pipeline.run_models_path(
            df=df,
            timestamp_col="time",
            model_metric="sensor_1",
        )
