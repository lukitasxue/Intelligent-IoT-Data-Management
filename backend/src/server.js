//handles server setup and configuration for the Express backend

const app = require('./app');


const { startThingSpeakPolling } = require('./services/thingspeakService');

// Debug-only imports (commented out for production)
/// const authMiddleware = require("./middleware/authMiddleware");
/// const { hashPassword, comparePassword } = require("./utils/hashUtils");
/// const { generateToken } = require("./utils/tokenUtils");

// Start server
const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
  startThingSpeakPolling();
});
