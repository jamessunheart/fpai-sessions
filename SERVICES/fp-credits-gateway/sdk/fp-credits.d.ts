/**
 * FP Credits SDK - TypeScript Type Definitions
 */

export interface FPCreditsOptions {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export interface Balance {
  accountId: string;
  fpCredits: number;
  coraCredits: number;
  usd: number;
  pending: {
    fp_credits?: number;
    cora_credits?: number;
    usd?: number;
  };
  lastUpdated: string;
}

export interface Transaction {
  transaction_id: string;
  account_id: string;
  type: string;
  amount: number;
  credit_type: string;
  balance_after: number;
  reason: string;
  reference_id?: string;
  created_at: string;
}

export interface CreditOptions {
  creditType?: 'fp_credits' | 'cora_credits' | 'usd';
  referenceId?: string;
  metadata?: Record<string, any>;
}

export interface TransferOptions extends CreditOptions {
  reason?: string;
}

export interface ExchangeResult {
  success: boolean;
  from_amount: number;
  from_type: string;
  to_amount: number;
  to_type: string;
  exchange_rate: number;
}

export interface HealthCheck {
  status: string;
  service: string;
  version: string;
  accounts: number;
  transactions_total: number;
  timestamp: string;
}

export declare class FPCreditsError extends Error {
  statusCode: number | null;
  details: any;
  constructor(message: string, statusCode?: number | null, details?: any);
}

export declare class FPCredits {
  static PRODUCTION_URL: string;
  static SERVER_URL: string;
  static LOCAL_URL: string;

  constructor(options?: FPCreditsOptions);

  // Balance operations
  getBalance(accountId: string): Promise<Balance>;
  hasSufficientBalance(accountId: string, amount: number, creditType?: string): Promise<boolean>;

  // Credit operations
  credit(accountId: string, amount: number, reason: string, options?: CreditOptions): Promise<Transaction>;
  debit(accountId: string, amount: number, reason: string, options?: CreditOptions): Promise<Transaction>;
  charge(accountId: string, amount: number, serviceName: string, description?: string): Promise<Transaction>;

  // Transfer operations
  transfer(fromAccount: string, toAccount: string, amount: number, options?: TransferOptions): Promise<any>;

  // Exchange operations
  exchange(accountId: string, fromType: string, toType: string, amount: number): Promise<ExchangeResult>;
  fpToCora(accountId: string, fpAmount: number): Promise<ExchangeResult>;
  coraToFp(accountId: string, coraAmount: number): Promise<ExchangeResult>;

  // Transaction history
  getTransactions(accountId: string, limit?: number): Promise<Transaction[]>;

  // Utility
  healthCheck(): Promise<HealthCheck>;
  getAccount(accountId: string): Promise<any>;
}

export interface FPCreditsWebSocketOptions {
  baseUrl?: string;
  onBalance?: (balances: Record<string, number>, data: any) => void;
  onError?: (error: any) => void;
  onClose?: () => void;
}

export declare class FPCreditsWebSocket {
  constructor(accountId: string, options?: FPCreditsWebSocketOptions);
  connect(): void;
  ping(): void;
  close(): void;
}


