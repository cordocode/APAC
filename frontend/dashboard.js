/*
################################################################################
# FILE: dashboard.js
# PURPOSE: Main JavaScript logic for AutoTrader Dashboard
################################################################################
*/

////////////////////////////////////////////////////////////////////////////////
// GLOBAL STATE
////////////////////////////////////////////////////////////////////////////////

let algorithms = [];
let marketOpen = false;
let totalAccountValue = 0;
let availableCash = 0;
let availableAlgorithmTypes = [];
let currentPinAction = null;
let selectedAlgorithmId = null;
let pollingInterval = null;

// DOM Elements (will be populated after DOM loads)
let elements = {};

////////////////////////////////////////////////////////////////////////////////
// INITIALIZATION
////////////////////////////////////////////////////////////////////////////////

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  try {
    console.log(`[${new Date().toISOString()}] DOM loaded`);
    
    // Populate elements after DOM is loaded
    elements = {
      cardsContainer: document.getElementById('cardsContainer'),
      positionIndicators: document.getElementById('positionIndicators'),
      totalValue: document.getElementById('totalValue'),
      addCard: document.getElementById('addCard'),
      
      // PIN Modal
      pinModal: document.getElementById('pinModal'),
      pinDots: [
        document.getElementById('pinDot1'),
        document.getElementById('pinDot2'),
        document.getElementById('pinDot3'),
        document.getElementById('pinDot4')
      ],
      pinError: document.getElementById('pinError'),
      closePinModal: document.getElementById('closePinModal'),
      
      // Add Algorithm Modal
      addAlgorithmModal: document.getElementById('addAlgorithmModal'),
      tickerInput: document.getElementById('tickerInput'),
      algorithmSelect: document.getElementById('algorithmSelect'),
      allocationInput: document.getElementById('allocationInput'),
      availableCash: document.getElementById('availableCash'),
      formError: document.getElementById('formError'),
      createAlgorithmBtn: document.getElementById('createAlgorithmBtn'),
      cancelAddBtn: document.getElementById('cancelAddBtn'),
      closeAddModal: document.getElementById('closeAddModal'),
      
      // Stop Confirmation Modal
      stopConfirmModal: document.getElementById('stopConfirmModal'),
      stopConfirmText1: document.getElementById('stopConfirmText1'),
      stopConfirmText2: document.getElementById('stopConfirmText2'),
      confirmStopBtn: document.getElementById('confirmStopBtn'),
      cancelStopBtn: document.getElementById('cancelStopBtn')
    };
    
    console.log(`[${new Date().toISOString()}] Elements loaded`);
    
    init();
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Initialization error`, error);
  }
});

function init() {
  console.log(`[${new Date().toISOString()}] Dashboard initializing`);
  setupEventListeners();
  loadAvailableAlgorithms();
  loadData();
  startPolling();
  console.log(`[${new Date().toISOString()}] Dashboard initialized`);
}

// Event Listeners
function setupEventListeners() {
  console.log(`[${new Date().toISOString()}] Setting event listeners`);
  
  // Add Card Click
  elements.addCard.addEventListener('click', handleAddCardClick);
  
  // PIN Pad
  const pinButtons = document.querySelectorAll('.pin-btn');
  pinButtons.forEach(btn => {
    btn.addEventListener('click', handlePinButtonClick);
  });
  elements.closePinModal.addEventListener('click', closePinModal);
  
  // Add Algorithm Modal
  elements.createAlgorithmBtn.addEventListener('click', handleCreateAlgorithm);
  elements.cancelAddBtn.addEventListener('click', closeAddAlgorithmModal);
  elements.closeAddModal.addEventListener('click', closeAddAlgorithmModal);
  
  // Stop Confirmation Modal
  elements.confirmStopBtn.addEventListener('click', handleConfirmStop);
  elements.cancelStopBtn.addEventListener('click', closeStopConfirmModal);
  
  // Close modals on background click
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeAllModals();
      }
    });
  });
  
  console.log(`[${new Date().toISOString()}] Event listeners setup`);
}

////////////////////////////////////////////////////////////////////////////////
// DATA LOADING
////////////////////////////////////////////////////////////////////////////////

async function loadData() {
  try {
    const response = await fetch(getApiUrl('ALGORITHMS'));
    const data = await response.json();
    
    algorithms = data.algorithms || [];
    marketOpen = data.market_open || false;
    totalAccountValue = data.total_account_value || 0;
    
    updateDisplay();
    adjustPollingInterval();
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Data loading error`, error);
  }
}

async function loadAvailableAlgorithms() {
  console.log(`[${new Date().toISOString()}] Loading available algorithms`);
  try {
    const response = await fetch(getApiUrl('AVAILABLE_ALGORITHMS'));
    const data = await response.json();
    
    // Handle both array and object response formats
    availableAlgorithmTypes = Array.isArray(data) ? data : (data.algorithms || []);
    
    // Populate dropdown
    elements.algorithmSelect.innerHTML = '<option value="">Select algorithm...</option>';
    availableAlgorithmTypes.forEach(algo => {
      const option = document.createElement('option');
      option.value = algo.type;
      option.textContent = algo.name;
      elements.algorithmSelect.appendChild(option);
    });
    console.log(`[${new Date().toISOString()}] Algorithm dropdown populated`);
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Algorithm loading error`, error);
  }
}

async function loadAvailableCash() {
  console.log(`[${new Date().toISOString()}] Loading available cash`);
  try {
    const url = getApiUrl('ACCOUNT_CASH');
    const response = await fetch(url);
    const data = await response.json();
    availableCash = data.available_cash || 0;
    elements.availableCash.textContent = formatCurrency(availableCash);
    console.log(`[${new Date().toISOString()}] Cash display updated`);
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Cash loading error`, error);
    throw error; // Re-throw to be caught by validatePin
  }
}

////////////////////////////////////////////////////////////////////////////////
// DISPLAY UPDATES
////////////////////////////////////////////////////////////////////////////////

function updateDisplay() {
  updatePositionIndicators();
  updateTotalValue();
  updateAlgorithmCards();
}

function updatePositionIndicators() {
  elements.positionIndicators.innerHTML = '';
  
  algorithms.forEach(algo => {
    const dot = document.createElement('div');
    dot.className = 'position-dot';
    
    if (algo.current_shares > 0) {
      dot.classList.add('has-shares');
    } else {
      dot.classList.add('no-shares');
    }
    
    elements.positionIndicators.appendChild(dot);
  });
}

function updateTotalValue() {
  elements.totalValue.textContent = formatCurrency(totalAccountValue);
}

function updateAlgorithmCards() {
  // Clear existing cards (except add card)
  const existingCards = elements.cardsContainer.querySelectorAll('.card:not(.add-card)');
  existingCards.forEach(card => card.remove());
  
  // Add algorithm cards
  algorithms.forEach(algo => {
    const card = createAlgorithmCard(algo);
    elements.cardsContainer.appendChild(card);
  });
}

function createAlgorithmCard(algo) {
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.algorithmId = algo.id;
  
  // Determine P&L status for border color
  if (algo.pnl > 0) {
    card.classList.add('profitable');
  } else if (algo.pnl < 0) {
    card.classList.add('losing');
  }
  
  // Format P&L with + or - sign
  const pnlFormatted = formatPnL(algo.pnl);
  const pnlClass = algo.pnl >= 0 ? 'positive' : 'negative';
  
  // Format last updated time
  const lastUpdated = formatTime(algo.last_updated);
  
  card.innerHTML = `
    <div class="card-header">
      <div class="card-ticker">${algo.ticker}</div>
      <div class="card-pnl ${pnlClass}">${pnlFormatted}</div>
    </div>
    <div class="card-algorithm">${algo.algorithm_type}</div>
    
    <div class="card-stats">
      <div class="stat-row">
        <span class="stat-label">Current Total Value:</span>
        <span class="stat-value">${formatCurrency(algo.current_value)}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Original Capital:</span>
        <span class="stat-value">${formatCurrency(algo.initial_capital)}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Current Shares:</span>
        <span class="stat-value">${algo.current_shares}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Transactions:</span>
        <span class="stat-value">${algo.trade_count}</span>
      </div>
    </div>
    
    <div class="card-updated">Last Updated: ${lastUpdated}</div>
    
    <div class="card-actions">
      <button class="stop-btn" onclick="handleStopClick(${algo.id})">STOP</button>
    </div>
  `;
  
  return card;
}

////////////////////////////////////////////////////////////////////////////////
// PIN MODAL FUNCTIONS
////////////////////////////////////////////////////////////////////////////////

let pinEntry = '';

function handleAddCardClick() {
  console.log(`[${new Date().toISOString()}] Add card clicked`);
  currentPinAction = 'add';
  showPinModal();
}

function handleStopClick(algorithmId) {
  console.log(`[${new Date().toISOString()}] Stop button clicked`);
  currentPinAction = 'stop';
  selectedAlgorithmId = algorithmId;
  showPinModal();
}

function showPinModal() {
  pinEntry = '';
  updatePinDisplay();
  elements.pinError.style.display = 'none';
  elements.pinModal.style.display = 'flex';
}

function closePinModal() {
  elements.pinModal.style.display = 'none';
  currentPinAction = null;
  selectedAlgorithmId = null;
}

function handlePinButtonClick(e) {
  const digit = e.target.dataset.digit;
  
  if (pinEntry.length < 4) {
    pinEntry += digit;
    updatePinDisplay();
    
    if (pinEntry.length === 4) {
      console.log(`[${new Date().toISOString()}] PIN validation started`);
      validatePin();
    }
  }
}

function updatePinDisplay() {
  elements.pinDots.forEach((dot, index) => {
    dot.textContent = index < pinEntry.length ? '●' : '○';
  });
}

async function validatePin() {
  console.log(`[${new Date().toISOString()}] Validating PIN`);
  
  try {
    const url = getApiUrl('VALIDATE_PIN');
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin: pinEntry })
    });
    
    const data = await response.json();
    
    if (data.valid === true) {
      console.log(`[${new Date().toISOString()}] PIN validated`);
      
      // Close PIN modal first
      elements.pinModal.style.display = 'none';
      pinEntry = '';
      
      if (currentPinAction === 'add') {
        console.log(`[${new Date().toISOString()}] Loading cash data`);
        try {
          await loadAvailableCash();
        } catch (e) {
          console.error(`[${new Date().toISOString()}] Cash loading failed`, e);
        }
        console.log(`[${new Date().toISOString()}] Showing add modal`);
        elements.addAlgorithmModal.style.display = 'flex';
      } else if (currentPinAction === 'stop') {
        console.log(`[${new Date().toISOString()}] Showing stop modal`);
        
        const algo = algorithms.find(a => a.id === selectedAlgorithmId);
        if (!algo) {
          console.error(`[${new Date().toISOString()}] Algorithm not found`);
          return;
        }
        
        const profitLoss = algo.pnl >= 0 ? 'profit' : 'loss';
        elements.stopConfirmText1.textContent = 
          `Stopping ${algo.ticker} algorithm will sell all ${algo.current_shares} shares`;
        elements.stopConfirmText2.textContent = 
          `This will realize a ${profitLoss} of ${formatCurrency(Math.abs(algo.pnl))}`;
        
        elements.stopConfirmModal.style.display = 'flex';
      }
    } else {
      console.log(`[${new Date().toISOString()}] Invalid PIN`);
      elements.pinError.style.display = 'block';
      pinEntry = '';
      updatePinDisplay();
    }
  } catch (error) {
    console.error(`[${new Date().toISOString()}] PIN validation error`, error);
    elements.pinError.style.display = 'block';
    pinEntry = '';
    updatePinDisplay();
  }
}

////////////////////////////////////////////////////////////////////////////////
// ADD ALGORITHM MODAL FUNCTIONS
////////////////////////////////////////////////////////////////////////////////

function showAddAlgorithmModal() {
  console.log(`[${new Date().toISOString()}] Showing add modal`);
  
  elements.tickerInput.value = '';
  elements.algorithmSelect.value = '';
  elements.allocationInput.value = '';
  elements.formError.style.display = 'none';
  elements.addAlgorithmModal.style.display = 'flex';
}

function closeAddAlgorithmModal() {
  elements.addAlgorithmModal.style.display = 'none';
}

async function handleCreateAlgorithm() {
  console.log(`[${new Date().toISOString()}] Creating algorithm`);
  
  const ticker = elements.tickerInput.value.toUpperCase().trim();
  const algorithmType = elements.algorithmSelect.value;
  const allocation = parseFloat(elements.allocationInput.value);
  
  // Validation
  if (!ticker || !algorithmType || !allocation) {
    showFormError('Please fill in all fields');
    return;
  }
  
  if (allocation > availableCash) {
    showFormError('Allocation exceeds available cash');
    return;
  }
  
  try {
    // Validate ticker
    const tickerUrl = getApiUrl('VALIDATE_TICKER') + '?symbol=' + ticker;
    console.log(`[${new Date().toISOString()}] Validating ticker`);
    const tickerResponse = await fetch(tickerUrl);
    const tickerData = await tickerResponse.json();
    
    if (!tickerData.valid) {
      showFormError('Invalid ticker symbol');
      return;
    }
    
    // Create algorithm
    const createUrl = getApiUrl('CREATE_ALGORITHM');
    console.log(`[${new Date().toISOString()}] Creating algorithm`);
    const response = await fetch(createUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ticker: ticker,
        algorithm_type: algorithmType,
        initial_capital: allocation
      })
    });
    
    if (response.ok) {
      console.log(`[${new Date().toISOString()}] Algorithm created`);
      closeAddAlgorithmModal();
      
      // Immediately update the display
      console.log(`[${new Date().toISOString()}] Reloading data`);
      await loadData();
    } else {
      const error = await response.json();
      console.error(`[${new Date().toISOString()}] Create error`, error);
      showFormError(error.message || 'Failed to create algorithm');
    }
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Algorithm creation error`, error);
    showFormError('Failed to create algorithm');
  }
}

function showFormError(message) {
  elements.formError.textContent = message;
  elements.formError.style.display = 'block';
}

////////////////////////////////////////////////////////////////////////////////
// STOP CONFIRMATION MODAL FUNCTIONS
////////////////////////////////////////////////////////////////////////////////

function showStopConfirmModal() {
  console.log(`[${new Date().toISOString()}] Showing stop modal`);
  
  const algo = algorithms.find(a => a.id === selectedAlgorithmId);
  
  if (!algo) {
    console.error(`[${new Date().toISOString()}] Algorithm not found`);
    return;
  }
  
  const profitLoss = algo.pnl >= 0 ? 'profit' : 'loss';
  
  elements.stopConfirmText1.textContent = 
    `Stopping ${algo.ticker} algorithm will sell all ${algo.current_shares} shares`;
  elements.stopConfirmText2.textContent = 
    `This will realize a ${profitLoss} of ${formatCurrency(Math.abs(algo.pnl))}`;
  
  elements.stopConfirmModal.style.display = 'flex';
}

function closeStopConfirmModal() {
  elements.stopConfirmModal.style.display = 'none';
  selectedAlgorithmId = null;
}

async function handleConfirmStop() {
  console.log(`[${new Date().toISOString()}] Confirming stop`);
  
  if (!selectedAlgorithmId) {
    console.error(`[${new Date().toISOString()}] No algorithm selected`);
    return;
  }
  
  try {
    const url = getApiUrl('STOP_ALGORITHM', { id: selectedAlgorithmId });
    console.log(`[${new Date().toISOString()}] Stopping algorithm`);
    
    const response = await fetch(url, { method: 'DELETE' });
    
    if (response.ok) {
      console.log(`[${new Date().toISOString()}] Algorithm stopped`);
      closeStopConfirmModal();
      
      // Immediately update the display
      console.log(`[${new Date().toISOString()}] Reloading data`);
      await loadData();
    } else {
      console.error(`[${new Date().toISOString()}] Stop failed`);
      const errorData = await response.json();
      console.error(`[${new Date().toISOString()}] Error details`, errorData);
    }
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Stop error`, error);
  }
}

////////////////////////////////////////////////////////////////////////////////
// POLLING FUNCTIONS
////////////////////////////////////////////////////////////////////////////////

// NOTE: The dashboard polls every 30 seconds during market hours (60 minutes when closed)
// to update card data. User actions (create/stop) immediately refresh the display.
function startPolling() {
  adjustPollingInterval();
}

function adjustPollingInterval() {
  if (pollingInterval) {
    clearInterval(pollingInterval);
  }
  
  const interval = marketOpen ? 
    CONFIG.POLL_INTERVAL_MARKET_OPEN : 
    CONFIG.POLL_INTERVAL_MARKET_CLOSED;
  
  pollingInterval = setInterval(loadData, interval);
}

////////////////////////////////////////////////////////////////////////////////
// UTILITY FUNCTIONS
////////////////////////////////////////////////////////////////////////////////

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', CONFIG.CURRENCY_FORMAT).format(amount);
}

function formatPnL(amount) {
  const formatted = formatCurrency(Math.abs(amount));
  return amount >= 0 ? `+${formatted}` : `-${formatted.substring(1)}`;
}

function formatTime(timestamp) {
  if (!timestamp) return 'Never';
  
  // Parse the UTC timestamp
  const date = new Date(timestamp);
  
  // Convert to local time (browser's timezone)
  const hours = date.getHours();
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;
  
  // You can also add date if needed
  // const month = date.getMonth() + 1;
  // const day = date.getDate();
  
  return `${displayHours}:${minutes} ${ampm}`;
}

function closeAllModals() {
  closePinModal();
  closeAddAlgorithmModal();
  closeStopConfirmModal();
}

// Make stop handler globally accessible
window.handleStopClick = handleStopClick;