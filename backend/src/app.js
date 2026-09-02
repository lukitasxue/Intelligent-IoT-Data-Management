const path = require('path');
const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config({ path: path.resolve(__dirname, '../.env') });

const mockRoutes = require('./routes/mock');
const apiRouter = require('./routes');
const authRoutes = require('./routes/auth');
const thingSpeakRoutes = require('./routes/thingspeak');

const app = express();

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.send('Backend is running');
});

app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptimeSeconds: process.uptime()
  });
});

app.use('/api', apiRouter);
app.use('/api', authRoutes);
app.use('/api', mockRoutes);
app.use('/api', thingSpeakRoutes);

module.exports = app;
