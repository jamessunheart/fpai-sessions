/**
 * FP Credits SDK - JavaScript/TypeScript Client
 * 
 * Easy integration for any frontend or Node.js service to use the FP Credits system.
 * 
 * Usage:
 *   import { FPCredits } from './fp-credits.js';
 *   
 *   const credits = new FPCredits({ apiKey: 'fps_your_key_here' });
 *   
 *   // Check balance
 *   const balance = await credits.getBalance('user:123');
 *   console.log(`FP Credits: ${balance.fp_credits}`);
 *   
 *   // Charge for service
 *   await credits.debit('user:123', 10.0, 'AI Chat Session');
 */

class FPCreditsError extends Error {
  constructor(message, statusCode = null, details = null) {
    super(message);
    this.name = 'FPCreditsError';
    this.statusCode = statusCode;
    this.details = details;
  }
}

class FPCredits {
  static PRODUCTION_URL = 'https://fullpotential.ai/services/credits';
  static SERVER_URL = 'http://198.54.123.234:8765';
  static LOCAL_URL = 'http://localhost:8765';

  /**
   * Initialize the FP Credits client.
   * @param {Object} options Configuration options
   * @param {string} options.apiKey Your service API key
   * @param {string} [options.baseUrl] Gateway URL (defaults to server URL)
   * @param {number} [options.timeout] Request timeout in ms (default 30000)
   */
  constructor(options = {}) {
    this.apiKey = options.apiKey || (typeof process !== 'undefined' ? process.env.FP_CREDITS_API_KEY : null);
    if (!this.apiKey) {
      throw new FPCreditsError('API key required. Set apiKey option or FP_CREDITS_API_KEY env var');
    }

    this.baseUrl = (options.baseUrl || FPCredits.SERVER_URL).replace(/\/$/, '');
    this.timeout = options.timeout || 30000;
  }

  /**
   * Make an API request
   * @private
   */
  async _request(method, endpoint, body = null) {
    const url = `${this.baseUrl}${endpoint}`;
    const options = {
      method,
      headers: {
        'X-API-Key': this.apiKey,
        'Content-Type': 'application/json'
      }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      options.signal = controller.signal;

      const response = await fetch(url, options);
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorMessage;
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || response.statusText;
        } catch {
          errorMessage = response.statusText;
        }
        throw new FPCreditsError(errorMessage, response.status);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof FPCreditsError) throw error;
      throw new FPCreditsError(`Request failed: ${error.message}`);
    }
  }

  // ================================================================
  // BALANCE OPERATIONS
  // ================================================================

  /**
   * Get the current balance for an account.
   * @param {string} accountId The account identifier
   * @returns {Promise<Object>} Balance object with fp_credits, cora_credits, and usd
   */
  async getBalance(accountId) {
    const data = await this._request('GET', `/api/balance/${encodeURIComponent(accountId)}`);
    return {
      accountId: data.account_id,
      fpCredits: data.balances?.fp_credits || 0,
      coraCredits: data.balances?.cora_credits || 0,
      usd: data.balances?.usd || 0,
      pending: data.pending || {},
      lastUpdated: data.last_updated
    };
  }

  /**
   * Check if an account has sufficient balance.
   * @param {string} accountId The account identifier
   * @param {number} amount Amount to check
   * @param {string} [creditType='fp_credits'] Type of credits to check
   * @returns {Promise<boolean>} True if balance is sufficient
   */
  async hasSufficientBalance(accountId, amount, creditType = 'fp_credits') {
    const balance = await this.getBalance(accountId);
    const typeMap = {
      'fp_credits': 'fpCredits',
      'cora_credits': 'coraCredits',
      'usd': 'usd'
    };
    const current = balance[typeMap[creditType] || 'fpCredits'] || 0;
    return current >= amount;
  }

  // ================================================================
  // CREDIT OPERATIONS
  // ================================================================

  /**
   * Add credits to an account.
   * @param {string} accountId The account to credit
   * @param {number} amount Amount to add (must be positive)
   * @param {string} reason Description of why credits are being added
   * @param {Object} [options] Additional options
   * @param {string} [options.creditType='fp_credits'] Type of credits
   * @param {string} [options.referenceId] Optional reference
   * @param {Object} [options.metadata] Optional additional data
   * @returns {Promise<Object>} Transaction record
   */
  async credit(accountId, amount, reason, options = {}) {
    return await this._request('POST', '/api/credit', {
      account_id: accountId,
      amount,
      credit_type: options.creditType || 'fp_credits',
      reason,
      reference_id: options.referenceId,
      metadata: options.metadata || {}
    });
  }

  /**
   * Deduct credits from an account.
   * @param {string} accountId The account to debit
   * @param {number} amount Amount to deduct (must be positive)
   * @param {string} reason Description of why credits are being deducted
   * @param {Object} [options] Additional options
   * @returns {Promise<Object>} Transaction record
   */
  async debit(accountId, amount, reason, options = {}) {
    return await this._request('POST', '/api/debit', {
      account_id: accountId,
      amount,
      credit_type: options.creditType || 'fp_credits',
      reason,
      reference_id: options.referenceId,
      metadata: options.metadata || {}
    });
  }

  /**
   * Convenience method to charge a user for a service.
   * @param {string} accountId The user's account
   * @param {number} amount Amount to charge
   * @param {string} serviceName Name of the service being used
   * @param {string} [description] Additional description
   * @returns {Promise<Object>} Transaction record
   */
  async charge(accountId, amount, serviceName, description = '') {
    const reason = description ? `${serviceName}: ${description}` : serviceName;
    return await this.debit(accountId, amount, reason);
  }

  // ================================================================
  // TRANSFER OPERATIONS
  // ================================================================

  /**
   * Transfer credits between accounts.
   * @param {string} fromAccount Source account
   * @param {string} toAccount Destination account
   * @param {number} amount Amount to transfer
   * @param {Object} [options] Additional options
   * @returns {Promise<Object>} Transfer result
   */
  async transfer(fromAccount, toAccount, amount, options = {}) {
    return await this._request('POST', '/api/transfer', {
      from_account: fromAccount,
      to_account: toAccount,
      amount,
      credit_type: options.creditType || 'fp_credits',
      reason: options.reason || '',
      metadata: options.metadata || {}
    });
  }

  // ================================================================
  // EXCHANGE OPERATIONS
  // ================================================================

  /**
   * Exchange between credit types.
   * @param {string} accountId The account performing the exchange
   * @param {string} fromType Credit type to exchange from
   * @param {string} toType Credit type to exchange to
   * @param {number} amount Amount to exchange
   * @returns {Promise<Object>} Exchange result with amounts and rate
   */
  async exchange(accountId, fromType, toType, amount) {
    return await this._request('POST', '/api/exchange', {
      account_id: accountId,
      from_type: fromType,
      to_type: toType,
      amount
    });
  }

  /**
   * Convert FP Credits to Cora Credits
   */
  async fpToCora(accountId, fpAmount) {
    return await this.exchange(accountId, 'fp_credits', 'cora_credits', fpAmount);
  }

  /**
   * Convert Cora Credits to FP Credits
   */
  async coraToFp(accountId, coraAmount) {
    return await this.exchange(accountId, 'cora_credits', 'fp_credits', coraAmount);
  }

  // ================================================================
  // TRANSACTION HISTORY
  // ================================================================

  /**
   * Get transaction history for an account.
   * @param {string} accountId The account to get history for
   * @param {number} [limit=50] Maximum number of transactions
   * @returns {Promise<Array>} List of transaction records
   */
  async getTransactions(accountId, limit = 50) {
    const data = await this._request('GET', `/api/transactions/${encodeURIComponent(accountId)}?limit=${limit}`);
    return data.transactions || [];
  }

  // ================================================================
  // UTILITY METHODS
  // ================================================================

  /**
   * Check if the credits gateway is healthy
   */
  async healthCheck() {
    return await this._request('GET', '/health');
  }

  /**
   * Get account details
   */
  async getAccount(accountId) {
    return await this._request('GET', `/api/accounts/${encodeURIComponent(accountId)}`);
  }
}

// ================================================================
// WEBSOCKET CLIENT FOR REAL-TIME UPDATES
// ================================================================

class FPCreditsWebSocket {
  /**
   * Create a WebSocket connection for real-time balance updates.
   * @param {string} accountId The account to subscribe to
   * @param {Object} [options] Configuration options
   * @param {string} [options.baseUrl] Gateway WebSocket URL
   * @param {Function} [options.onBalance] Callback for balance updates
   * @param {Function} [options.onError] Callback for errors
   * @param {Function} [options.onClose] Callback for connection close
   */
  constructor(accountId, options = {}) {
    this.accountId = accountId;
    this.baseUrl = (options.baseUrl || FPCredits.SERVER_URL).replace('http', 'ws');
    this.onBalance = options.onBalance || (() => {});
    this.onError = options.onError || console.error;
    this.onClose = options.onClose || (() => {});
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  /**
   * Connect to the WebSocket
   */
  connect() {
    const url = `${this.baseUrl}/ws/${encodeURIComponent(this.accountId)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('[FPCredits WS] Connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'balance_update' || data.type === 'connected') {
          this.onBalance(data.balances, data);
        }
      } catch (e) {
        console.error('[FPCredits WS] Parse error:', e);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[FPCredits WS] Error:', error);
      this.onError(error);
    };

    this.ws.onclose = () => {
      console.log('[FPCredits WS] Disconnected');
      this.onClose();
      
      // Attempt reconnection
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        console.log(`[FPCredits WS] Reconnecting in ${delay}ms...`);
        setTimeout(() => this.connect(), delay);
      }
    };
  }

  /**
   * Send a ping to keep connection alive
   */
  ping() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send('ping');
    }
  }

  /**
   * Close the WebSocket connection
   */
  close() {
    this.maxReconnectAttempts = 0; // Prevent reconnection
    if (this.ws) {
      this.ws.close();
    }
  }
}

// ================================================================
// EXPORTS
// ================================================================

// ES Module exports
export { FPCredits, FPCreditsError, FPCreditsWebSocket };

// CommonJS compatibility
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { FPCredits, FPCreditsError, FPCreditsWebSocket };
}

