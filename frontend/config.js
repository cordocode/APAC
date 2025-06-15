/*
################################################################################
# FILE: config.js
# PURPOSE: Configuration settings for AutoTrader Dashboard
################################################################################
*/

// AutoTrader Dashboard Configuration

const CONFIG = {
  // API Base URL (adjust for production)
  API_BASE_URL: 'http://localhost:5001',
  
  // API Endpoints
  API_ENDPOINTS: {
    ALGORITHMS: '/api/algorithms',
    CREATE_ALGORITHM: '/api/algorithms',
    STOP_ALGORITHM: '/api/algorithms/{id}',
    VALIDATE_PIN: '/api/validate-pin',
    AVAILABLE_ALGORITHMS: '/api/available-algorithms',
    ACCOUNT_CASH: '/api/account/cash',
    VALIDATE_TICKER: '/api/validate-ticker'
  },
  
  // Polling Intervals (in milliseconds)
  POLL_INTERVAL_MARKET_OPEN: 30 * 1000,    // 30 seconds
  POLL_INTERVAL_MARKET_CLOSED: 60 * 60 * 1000,  // 60 minutes
  
  // Market Hours (for display purposes)
  MARKET_OPEN_HOUR: 9,
  MARKET_OPEN_MINUTE: 30,
  MARKET_CLOSE_HOUR: 16,
  MARKET_CLOSE_MINUTE: 0,
  
  // UI Settings
  MAX_PIN_ATTEMPTS: 999,  // No lockout as requested
  CARD_ANIMATION_DURATION: 300,  // milliseconds
  
  // Number Formatting
  CURRENCY_FORMAT: {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }
};

// Helper function to build full API URLs
function getApiUrl(endpoint, params = {}) {
  let url = CONFIG.API_BASE_URL + CONFIG.API_ENDPOINTS[endpoint];
  
  // Replace path parameters like {id}
  Object.keys(params).forEach(key => {
    url = url.replace(`{${key}}`, params[key]);
  });
  
  return url;
}