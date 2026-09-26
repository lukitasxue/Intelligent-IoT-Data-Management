import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const colors = ['#2563eb', '#16a34a', '#9333ea', '#ea580c', '#0891b2', '#dc2626'];

const formatTimestamp = (timestamp) => {
  const date = new Date(timestamp);

  return Number.isNaN(date.getTime())
    ? timestamp
    : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const Chart = ({ data, selectedStreams }) => {
  if (selectedStreams.length === 0) {
    return <p className="chart-empty-state">Select one or more streams to view sensor trends.</p>;
  }

  if (data.length === 0) {
    return <p className="chart-empty-state">No readings are available for the selected streams and time range.</p>;
  }

  return (
    <div className="sensor-trends-chart" role="img" aria-label="Selected sensor trends line chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 18, right: 16, bottom: 16, left: 4 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="created_at"
            minTickGap={28}
            tickFormatter={formatTimestamp}
            tick={{ fill: '#64748b', fontSize: 12 }}
            label={{ value: 'Time', position: 'insideBottom', offset: -8, fill: '#334155', fontSize: 12, fontWeight: 700 }}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 12 }}
            label={{ value: 'Value', angle: -90, position: 'insideLeft', offset: 0, fill: '#334155', fontSize: 12, fontWeight: 700 }}
          />
          <Tooltip
            labelFormatter={(label) => new Date(label).toLocaleString()}
            contentStyle={{ borderRadius: 10, borderColor: '#dbeafe' }}
          />
          <Legend wrapperStyle={{ paddingTop: 8, fontSize: 12 }} />
          {selectedStreams.map((stream, index) => (
            <Line
              key={stream}
              type="monotone"
              dataKey={stream}
              name={stream}
              stroke={colors[index % colors.length]}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Chart;
