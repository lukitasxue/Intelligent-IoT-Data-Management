const assert = require('node:assert/strict');
const http = require('node:http');
const test = require('node:test');

const app = require('../src/app');
const timeseriesService = require('../src/services/timeseriesService');
const { normaliseRows } = require('../src/services/analyseService');

function listen(server) {
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server.address().port)));
}

function close(server) {
  return new Promise((resolve) => server.close(resolve));
}

test('1350261 ThingSpeak rows use the documented canonical metric names', () => {
  assert.deepEqual(
    normaliseRows([
      {
        created_at: '2026-08-27T00:00:00Z',
        field1: 650,
        field2: 120,
        field3: 21.5,
        field4: 1008.2,
        field5: 48.3,
        field6: 21.7,
        field7: 35.1,
        field8: 723,
      },
    ], 'thingspeak-1350261'),
    [{
      timestamp: '2026-08-27T00:00:00.000Z',
      eco2: 650,
      etvoc: 120,
      temperature: 21.5,
      air_pressure: 1008.2,
      humidity: 48.3,
      temperature_secondary: 21.7,
      controller_temperature: 35.1,
      conductance: 723,
    }],
  );
});

test('POST /api/analyse normalises Backend data and returns the AIntl response', async () => {
  let receivedPayload;
  const analyticsServer = http.createServer((req, res) => {
    assert.equal(req.method, 'POST');
    assert.equal(req.url, '/analytics/analyze');
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', () => {
      receivedPayload = JSON.parse(body);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({
        status: 'success',
        generated_at: '2026-08-27T00:00:00.000Z',
        alerts: [],
        summary: { processed_items: 2, alert_count: 0 },
        errors: [],
      }));
    });
  });
  const analyticsPort = await listen(analyticsServer);
  const backendServer = http.createServer(app);
  const backendPort = await listen(backendServer);
  const originalUrl = process.env.ANALYTICS_SERVICE_URL;
  const originalSeriesLoader = timeseriesService.getWideEntriesForDatasetName;
  process.env.ANALYTICS_SERVICE_URL = `http://127.0.0.1:${analyticsPort}`;
  timeseriesService.getWideEntriesForDatasetName = async () => [
    { created_at: '2026-08-27T00:00:00.000Z', entry_id: 1, field3: '50.5', field4: '24.2', field6: '29.91' },
    { created_at: '2026-08-27T00:01:00.000Z', entry_id: 2, field3: '51.0', field4: '24.4', field6: '29.92' },
  ];

  try {
    const response = await fetch(`http://127.0.0.1:${backendPort}/api/analyse`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        dataset: 'thingspeak-12397',
        model: { metric: 'temperature' },
        correlation: { streams: ['temperature', 'humidity'] },
      }),
    });
    const body = await response.json();

    assert.equal(response.status, 200);
    assert.equal(body.status, 'success');
    assert.equal(body.summary.processed_items, 2);
    assert.deepEqual(receivedPayload, {
      entity_id: 'thingspeak-12397',
      timestamp_col: 'timestamp',
      data: [
        { timestamp: '2026-08-27T00:00:00.000Z', humidity: 50.5, temperature: 24.2, pressure: 1012.8692490000001 },
        { timestamp: '2026-08-27T00:01:00.000Z', humidity: 51, temperature: 24.4, pressure: 1013.2078880000001 },
      ],
      model: { detector: 'isolationforest', metric: 'temperature', parameters: {} },
      correlation: { streams: ['temperature', 'humidity'], window_size: 20, step_size: 10, method: 'pearson' },
    });
  } finally {
    timeseriesService.getWideEntriesForDatasetName = originalSeriesLoader;
    if (originalUrl === undefined) delete process.env.ANALYTICS_SERVICE_URL;
    else process.env.ANALYTICS_SERVICE_URL = originalUrl;
    await close(backendServer);
    await close(analyticsServer);
  }
});

test('POST /api/analyse returns an actionable unavailable error when AIntl cannot be reached', async () => {
  const backendServer = http.createServer(app);
  const backendPort = await listen(backendServer);
  const originalUrl = process.env.ANALYTICS_SERVICE_URL;
  process.env.ANALYTICS_SERVICE_URL = 'http://127.0.0.1:1';

  try {
    const response = await fetch(`http://127.0.0.1:${backendPort}/api/analyse`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        data: [
          { timestamp: '2026-08-27T00:00:00.000Z', temperature: 24.2, humidity: 50.5 },
          { timestamp: '2026-08-27T00:01:00.000Z', temperature: 24.4, humidity: 51.0 },
        ],
        model: { metric: 'temperature' },
        correlation: { streams: ['temperature', 'humidity'] },
      }),
    });

    assert.equal(response.status, 503);
    assert.deepEqual(await response.json(), {
      error: 'Analytics service is unavailable',
      code: 'ANALYTICS_UNAVAILABLE',
    });
  } finally {
    if (originalUrl === undefined) delete process.env.ANALYTICS_SERVICE_URL;
    else process.env.ANALYTICS_SERVICE_URL = originalUrl;
    await close(backendServer);
  }
});
