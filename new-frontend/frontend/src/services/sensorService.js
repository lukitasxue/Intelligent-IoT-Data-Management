import {
  sensor1Response,
  sensor2Response,
  sensor3Response,
  emptyResponse,
  validationErrorResponse,
  malformedSensorDataResponse,
  errorResponse,
  insufficientDataResponse,
} from '../data';

export const getSensorData = async (datasetId, options = {}) => {
  const {
    useMock = false,
    baseUrl = '/api',
  } = options;


  if (useMock) {
    await new Promise((resolve) => setTimeout(resolve, 500));

    switch (datasetId) {
      case 'sensor1':
        return sensor1Response;

      case 'sensor2':
        return sensor2Response;

      case 'sensor3':
        return sensor3Response;

      case 'empty':
        return emptyResponse;

      case 'validation-error':
        return validationErrorResponse;

      case 'malformed':
        return malformedSensorDataResponse;

      case 'error':
        return errorResponse;

      case 'insufficient':
        return insufficientDataResponse;

      default:
        throw new Error(`Unknown dataset ID: ${datasetId}`);
    }
  }

  // LIVE BACKEND MODE
  

  if (!datasetId) {
    throw new Error('Dataset ID is required');
  }

  const response = await fetch(
    `${baseUrl}/datasets/${encodeURIComponent(datasetId)}/series`
  );

  if (!response.ok) {
    throw new Error(
      `Failed to fetch data: ${response.status} ${response.statusText}`
    );
  }

  const rows = await response.json();

  // Backend live endpoint currently returns
  // a flat array of sensor readings
  if (!Array.isArray(rows)) {
    throw new Error(
      'Invalid Backend response: expected an array of sensor readings'
    );
  }

  // ---------------------------------
  // EMPTY DATASET
  // ---------------------------------

  if (rows.length === 0) {
    return {
      dataset: datasetId,
      rowCount: 0,

      metadata: {
        streams: [],
      },

      rows: [],
    };
  }

  // ---------------------------------
  // FIND SENSOR STREAMS
  // ---------------------------------

  // These fields are metadata,
  // not actual sensor streams
  const excludedFields = new Set([
    'dataset_id',
    'created_at',
    'entry_id',
  ]);

  // Check every row instead of only the first row,
  // because some readings may have missing fields
  const streamIds = [
    ...new Set(
      rows.flatMap((row) =>
        Object.keys(row).filter(
          (key) => !excludedFields.has(key)
        )
      )
    ),
  ];

  // Convert stream IDs into the structure
  // expected by the existing Dashboard
  const streams = streamIds.map((id) => ({
    id,
    name: id,
  }));

  // ---------------------------------
  // NORMALISED FRONTEND RESPONSE
  // ---------------------------------

  return {
    dataset: datasetId,

    rowCount: rows.length,

    metadata: {
      streams,
    },

    rows,
  };
};