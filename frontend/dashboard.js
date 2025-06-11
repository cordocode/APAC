// AutoTrader Dashboard JavaScript
console.log('Dashboard.js loaded');

// Global State
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('DOMContentLoaded fired');
        
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
        
        console.log('Elements loaded:', Object.keys(elements).length);
        console.log('Add Algorithm Modal element:', elements.addAlgorithmModal);
        
        init();
    } catch (error) {
        console.error('Error during initialization:', error);
    }
});

function init() {
    console.log('Dashboard initializing...');
    setupEventListeners();
    loadAvailableAlgorithms();
    loadData();
    startPolling();
    console.log('Dashboard initialized');
}

// Event Listeners
function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Add Card Click
    elements.addCard.addEventListener('click', handleAddCardClick);
    console.log('Add card click listener attached');
    
    // PIN Pad
    const pinButtons = document.querySelectorAll('.pin-btn');
    console.log('Found PIN buttons:', pinButtons.length);
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
    
    console.log('Event listeners setup complete');
}

// Data Loading
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
        console.error('Error loading data:', error);
    }
}

async function loadAvailableAlgorithms() {
    console.log('Loading available algorithms...');
    try {
        const response = await fetch(getApiUrl('AVAILABLE_ALGORITHMS'));
        const data = await response.json();
        console.log('Available algorithms response:', data);
        
        // Handle both array and object response formats
        availableAlgorithmTypes = Array.isArray(data) ? data : (data.algorithms || []);
        console.log('Processed algorithm types:', availableAlgorithmTypes);
        
        // Log each algorithm found
        availableAlgorithmTypes.forEach((algo, index) => {
            console.log(`Algorithm ${index}: type="${algo.type}", name="${algo.name}"`);
        });
        
        // Populate dropdown
        elements.algorithmSelect.innerHTML = '<option value="">Select algorithm...</option>';
        availableAlgorithmTypes.forEach(algo => {
            const option = document.createElement('option');
            option.value = algo.type;
            option.textContent = algo.name;
            elements.algorithmSelect.appendChild(option);
        });
        console.log('Algorithm dropdown populated with', availableAlgorithmTypes.length, 'algorithms');
    } catch (error) {
        console.error('Error loading available algorithms:', error);
    }
}

async function loadAvailableCash() {
    console.log('loadAvailableCash called');
    try {
        const url = getApiUrl('ACCOUNT_CASH');
        console.log('Account cash URL:', url);
        const response = await fetch(url);
        console.log('Account cash response status:', response.status);
        const data = await response.json();
        console.log('Account cash data:', data);
        availableCash = data.available_cash || 0;
        console.log('Available cash set to:', availableCash);
        elements.availableCash.textContent = formatCurrency(availableCash);
        console.log('Available cash display updated');
    } catch (error) {
        console.error('Error loading available cash:', error);
        throw error; // Re-throw to be caught by validatePin
    }
}

// Display Updates
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

// PIN Modal Functions
let pinEntry = '';

function handleAddCardClick() {
    console.log('Add card clicked');
    currentPinAction = 'add';
    showPinModal();
}

function handleStopClick(algorithmId) {
    console.log('Stop clicked for algorithm ID:', algorithmId);
    currentPinAction = 'stop';
    selectedAlgorithmId = algorithmId;
    console.log('Set selectedAlgorithmId to:', selectedAlgorithmId);
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
    console.log('PIN button clicked:', digit);
    
    if (pinEntry.length < 4) {
        pinEntry += digit;
        updatePinDisplay();
        
        if (pinEntry.length === 4) {
            console.log('PIN complete, validating...');
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
    console.log('Validating PIN:', pinEntry);
    console.log('Current action:', currentPinAction);
    
    try {
        const url = getApiUrl('VALIDATE_PIN');
        console.log('PIN validation URL:', url);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin: pinEntry })
        });
        
        console.log('PIN validation response status:', response.status);
        const data = await response.json();
        console.log('PIN validation response data:', data);
        
        if (data.valid === true) {
            console.log('PIN is valid');
            
            // Close PIN modal first
            elements.pinModal.style.display = 'none';
            pinEntry = '';
            
            if (currentPinAction === 'add') {
                console.log('Action is ADD, loading cash...');
                try {
                    await loadAvailableCash();
                } catch (e) {
                    console.error('Failed to load cash:', e);
                }
                console.log('Showing add modal...');
                elements.addAlgorithmModal.style.display = 'flex';
            } else if (currentPinAction === 'stop') {
                console.log('Action is STOP, showing confirm modal...');
                console.log('Selected algo ID:', selectedAlgorithmId);
                
                const algo = algorithms.find(a => a.id === selectedAlgorithmId);
                if (!algo) {
                    console.error('Algorithm not found!');
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
            console.log('PIN is invalid');
            elements.pinError.style.display = 'block';
            pinEntry = '';
            updatePinDisplay();
        }
    } catch (error) {
        console.error('Error validating PIN:', error);
        elements.pinError.style.display = 'block';
        pinEntry = '';
        updatePinDisplay();
    }
}

// Add Algorithm Modal Functions
function showAddAlgorithmModal() {
    console.log('showAddAlgorithmModal called');
    console.log('Available algorithms:', availableAlgorithmTypes);
    console.log('Algorithm select element:', elements.algorithmSelect);
    console.log('Add algorithm modal element:', elements.addAlgorithmModal);
    
    elements.tickerInput.value = '';
    elements.algorithmSelect.value = '';
    elements.allocationInput.value = '';
    elements.formError.style.display = 'none';
    elements.addAlgorithmModal.style.display = 'flex';
    
    console.log('Add algorithm modal display style:', elements.addAlgorithmModal.style.display);
}

function closeAddAlgorithmModal() {
    elements.addAlgorithmModal.style.display = 'none';
}

async function handleCreateAlgorithm() {
    console.log('handleCreateAlgorithm called');
    
    const ticker = elements.tickerInput.value.toUpperCase().trim();
    const algorithmType = elements.algorithmSelect.value;
    const allocation = parseFloat(elements.allocationInput.value);
    
    console.log('Create algorithm inputs:', { ticker, algorithmType, allocation });
    
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
        console.log('Validating ticker at:', tickerUrl);
        const tickerResponse = await fetch(tickerUrl);
        const tickerData = await tickerResponse.json();
        console.log('Ticker validation result:', tickerData);
        
        if (!tickerData.valid) {
            showFormError('Invalid ticker symbol');
            return;
        }
        
        // Create algorithm
        const createUrl = getApiUrl('CREATE_ALGORITHM');
        console.log('Creating algorithm at:', createUrl);
        const response = await fetch(createUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticker: ticker,
                algorithm_type: algorithmType,
                initial_capital: allocation
            })
        });
        
        console.log('Create response status:', response.status);
        
        if (response.ok) {
            console.log('Algorithm created successfully');
            closeAddAlgorithmModal();
            
            // Immediately update the display
            console.log('Reloading data after create...');
            await loadData();
        } else {
            const error = await response.json();
            console.error('Create error:', error);
            showFormError(error.message || 'Failed to create algorithm');
        }
    } catch (error) {
        console.error('Error creating algorithm:', error);
        showFormError('Failed to create algorithm');
    }
}

function showFormError(message) {
    elements.formError.textContent = message;
    elements.formError.style.display = 'block';
}

// Stop Confirmation Modal Functions
function showStopConfirmModal() {
    console.log('showStopConfirmModal called');
    console.log('Selected algorithm ID:', selectedAlgorithmId);
    console.log('Algorithms array:', algorithms);
    
    const algo = algorithms.find(a => a.id === selectedAlgorithmId);
    console.log('Found algorithm:', algo);
    
    if (!algo) {
        console.error('Algorithm not found with ID:', selectedAlgorithmId);
        return;
    }
    
    const profitLoss = algo.pnl >= 0 ? 'profit' : 'loss';
    
    elements.stopConfirmText1.textContent = 
        `Stopping ${algo.ticker} algorithm will sell all ${algo.current_shares} shares`;
    elements.stopConfirmText2.textContent = 
        `This will realize a ${profitLoss} of ${formatCurrency(Math.abs(algo.pnl))}`;
    
    console.log('Stop confirm modal element:', elements.stopConfirmModal);
    elements.stopConfirmModal.style.display = 'flex';
    console.log('Stop confirm modal display style:', elements.stopConfirmModal.style.display);
}

function closeStopConfirmModal() {
    elements.stopConfirmModal.style.display = 'none';
    selectedAlgorithmId = null;
}

async function handleConfirmStop() {
    console.log('handleConfirmStop called');
    console.log('Stopping algorithm ID:', selectedAlgorithmId);
    
    if (!selectedAlgorithmId) {
        console.error('No algorithm ID selected');
        return;
    }
    
    try {
        const url = getApiUrl('STOP_ALGORITHM', { id: selectedAlgorithmId });
        console.log('Stop algorithm URL:', url);
        
        const response = await fetch(url, { method: 'DELETE' });
        console.log('Stop response status:', response.status);
        
        if (response.ok) {
            console.log('Algorithm stopped successfully');
            closeStopConfirmModal();
            
            // Immediately update the display
            console.log('Reloading data after stop...');
            await loadData();
        } else {
            console.error('Failed to stop algorithm:', response.status);
            const errorData = await response.json();
            console.error('Error details:', errorData);
        }
    } catch (error) {
        console.error('Error stopping algorithm:', error);
    }
}

// Polling Functions
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

// Utility Functions
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