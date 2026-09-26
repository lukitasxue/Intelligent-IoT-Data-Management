const timeseriesService = require('./timeseriesService');

const DEFAULT_TIMEOUT_MS = 15_000;

// Keep source-specific field names at the Backend boundary. Analytics only
// receives canonical sensor names.
const CHANNEL_FIELD_MAPPINGS = {
  '12397': {
    field3: 'humidity',
    field4: 'temperature',
    // The source value is inches of mercury; the canonical Backend metric is hPa.
    field6: { name: 'pressure', transform: (value) => value * 33.8639 },
  },
  '1350261': {
    field1: 'eco2',
    field2: 'etvoc',
    field3: 'temperature',
    field4: 'air_pressure',
    field5: 'humidity',
    field6: 'temperature_secondary',
    field7: 'controller_temperature',
    field8: 'conductance',
  },  
};

function mappingForDataset(dataset) {
  // `thingspeak-live` is the active ingestion dataset. Named channel aliases
  // make historical/parallel datasets deterministic without exposing fields to AIntl.
  if (dataset === 'thingspeak-live') {
    return CHANNEL_FIELD_MAPPINGS[process.env.THINGSPEAK_CHANNEL_ID] || {};
  }
  const channelId = /^thingspeak-(\d+)$/.exec(dataset || '')?.[1];
  return CHANNEL_FIELD_MAPPINGS[channelId] || {};
}

class AnalysisServiceError extends Error {
  constructor(message, { status, code, details } = {}) {
    super(message);
    this.name = 'AnalysisServiceError';
    this.status = status || 500;
    this.code = code || 'INTERNAL_ERROR';
    this.details = details;
  }
}

function analyticsUrl() {
  return (process.env.ANALYTICS_SERVICE_URL || 'http://localhost:5002').replace(/\/$/, '');
}

function analyticsTimeoutMs() {
  const configured = Number(process.env.ANALYTICS_TIMEOUT_MS);
  return Number.isFinite(configured) && configured > 0 ? configured : DEFAULT_TIMEOUT_MS;
}

function assertObject(value, name) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new AnalysisServiceError(`${name} must be an object`, {
      status: 400,
      code: 'VALIDATION_ERROR',
    });
  }
}

function normaliseRows(rows, dataset) {
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new AnalysisServiceError('No sensor data is available for analysis', {
      status: 404,
      code: 'DATA_NOT_FOUND',
    });
  }

  const mapping = mappingForDataset(dataset);

  return rows.map((row) => {
    const normalised = {};
    const timestamp = row.timestamp ?? row.created_at;

    if (timestamp !== undefined && timestamp !== null) {
      const parsedTimestamp = new Date(timestamp);
      if (Number.isNaN(parsedTimestamp.getTime())) {
        throw new AnalysisServiceError('Each sensor row must contain a valid timestamp', {
          status: 400,
          code: 'VALIDATION_ERROR',
        });
      }
      normalised.timestamp = parsedTimestamp.toISOString();
    }

    for (const [key, value] of Object.entries(row)) {
      if (['timestamp', 'created_at', 'entry_id', 'dataset_id'].includes(key)) continue;
      const fieldMapping = mapping[key];
      const canonicalName = typeof fieldMapping === 'object' ? fieldMapping.name : fieldMapping || key;

      // Do not allow un-mapped ThingSpeak field names across the service boundary.
      if (/^field\d+$/i.test(canonicalName)) continue;
      const numericValue = value === null || value === '' ? null : Number(value);
      if (numericValue !== null && !Number.isFinite(numericValue)) {
        throw new AnalysisServiceError(`Metric '${canonicalName}' must be numeric or null`, {
          status: 400,
          code: 'VALIDATION_ERROR',
        });
      }
      normalised[canonicalName] = numericValue === null || !fieldMapping?.transform
        ? numericValue
        : fieldMapping.transform(numericValue);
    }

    return normalised;
  });
}

function buildAnalyticsPayload(request, rows) {
  assertObject(request, 'Request body');
  assertObject(request.model, 'model');
  assertObject(request.correlation, 'correlation');

  const { model, correlation } = request;
  if (typeof model.metric !== 'string' || !model.metric.trim()) {
    throw new AnalysisServiceError('model.metric must be a non-empty canonical metric name', {
      status: 400,
      code: 'VALIDATION_ERROR',
    });
  }
  if (!Array.isArray(correlation.streams) || correlation.streams.length < 2) {
    throw new AnalysisServiceError('correlation.streams must contain at least two canonical metric names', {
      status: 400,
      code: 'VALIDATION_ERROR',
    });
  }

  const data = normaliseRows(rows, request.dataset);
  const columns = new Set(data.flatMap((row) => Object.keys(row)));
  const requestedMetrics = [model.metric, ...correlation.streams];
  const unknownMetric = requestedMetrics.find((metric) => !columns.has(metric));
  if (unknownMetric) {
    throw new AnalysisServiceError(`Canonical metric '${unknownMetric}' is not available in the selected data`, {
      status: 400,
      code: 'VALIDATION_ERROR',
    });
  }

  return {
    entity_id: request.entity_id ?? request.dataset ?? null,
    timestamp_col: 'timestamp',
    data,
    model: {
      detector: model.detector ?? 'isolationforest',
      metric: model.metric,
      parameters: model.parameters ?? {},
    },
    correlation: {
      streams: correlation.streams,
      window_size: correlation.window_size ?? 20,
      step_size: correlation.step_size ?? 10,
      method: correlation.method ?? 'pearson',
    },
  };
}

async function loadRows(request) {
  if (Array.isArray(request.data)) return request.data;
  if (typeof request.dataset !== 'string' || !request.dataset.trim()) {
    throw new AnalysisServiceError('dataset is required when data is not supplied', {
      status: 400,
      code: 'VALIDATION_ERROR',
    });
  }

  const rows = await timeseriesService.getWideEntriesForDatasetName(request.dataset);
  if (!rows) {
    throw new AnalysisServiceError('Dataset not found or contains no sensor data', {
      status: 404,
      code: 'DATASET_NOT_FOUND',
    });
  }
  return rows;
}

async function callAnalytics(payload) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), analyticsTimeoutMs());
  let response;

  try {
    response = await fetch(`${analyticsUrl()}/analytics/analyze`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new AnalysisServiceError('Analytics service timed out', {
        status: 504,
        code: 'ANALYTICS_TIMEOUT',
      });
    }
    throw new AnalysisServiceError('Analytics service is unavailable', {
      status: 503,
      code: 'ANALYTICS_UNAVAILABLE',
    });
  } finally {
    clearTimeout(timeout);
  }

  let body;
  try {
    body = await response.json();
  } catch (_) {
    throw new AnalysisServiceError('Analytics service returned an invalid response', {
      status: 502,
      code: 'ANALYTICS_INVALID_RESPONSE',
    });
  }

  if (!response.ok) {
    const invalidRequest = response.status >= 400 && response.status < 500;
    throw new AnalysisServiceError(
      invalidRequest ? 'Analytics rejected the analysis request' : 'Analytics processing failed',
      {
        status: invalidRequest ? 400 : 502,
        code: invalidRequest ? 'ANALYTICS_INVALID_REQUEST' : 'ANALYTICS_UPSTREAM_ERROR',
        details: body.errors,
      },
    );
  }
  return body;
}

async function runAnalysis(request) {
  assertObject(request, 'Request body');
  const rows = await loadRows(request);
  const payload = buildAnalyticsPayload(request, rows);
  return callAnalytics(payload);
}

module.exports = { runAnalysis, buildAnalyticsPayload, normaliseRows, AnalysisServiceError };
