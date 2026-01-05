/**
 * Flask Backend API Client
 * Connects to the Flask backend via Render or other deployment
 * 
 * Configure the API_BASE_URL in your .env file:
 * VITE_FLASK_API_URL=https://your-backend.onrender.com/api
 */

import { supabase } from '@/integrations/supabase/client';

// Use environment variable only - no fallback to localhost
const API_BASE_URL = import.meta.env.VITE_FLASK_API_URL;

if (!API_BASE_URL) {
  console.error('VITE_FLASK_API_URL is not configured. Please set it in your .env file.');
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface Statement {
  _id: string;
  id?: string;
  bankType?: string;
  fileName?: string;
  uploadDate?: string;
  createdAt?: string;
  accountNumber?: string;
  accountHolder?: string;
  transactionCount?: number;
  totalDebit?: number;
  totalCredit?: number;
  openingBalance?: number;
  closingBalance?: number;
}

export interface Transaction {
  _id: string;
  id?: string;
  statementId: string;
  date: string;
  description: string;
  amount?: number;
  direction?: 'debit' | 'credit';
  balance: number | null;
  category: string | null;
  merchant?: string;
  channel?: string;
  // Legacy fields for backward compatibility
  debit?: number | null;
  credit?: number | null;
}

export interface UploadResult {
  statementId: string;
  bankType: string;
  transactionsInserted: number;
  accountNumber?: string;
  accountHolder?: string;
  openingBalance?: number;
  closingBalance?: number;
}

export interface CategorySpend {
  category: string;
  totalAmount: number;
  transactionCount: number;
  percentage?: number;
}

export interface BankWiseSpend {
  bankType: string;
  totalDebit: number;
  totalCredit: number;
  transactionCount: number;
}

export interface AnalyticsSummary {
  totalDebit: number;
  totalCredit: number;
  netFlow: number;
  transactionCount?: number;
  totalTransactions?: number;
  averageTransaction?: number;
}

class FlaskApiClient {
  private baseUrl: string | undefined;

  constructor(baseUrl: string | undefined) {
    this.baseUrl = baseUrl;
    if (!baseUrl) {
      console.error('[Flask API] API_BASE_URL is undefined. Set VITE_FLASK_API_URL in environment variables.');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    // Validate baseUrl is configured
    if (!this.baseUrl) {
      return {
        success: false,
        error: 'Backend API URL not configured. Please set VITE_FLASK_API_URL environment variable.',
      };
    }

    try {
      // Get Supabase session token for authentication
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      // Build headers with authentication
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...options.headers,
      };
      
      // Add Authorization header if token exists
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const url = `${this.baseUrl}${endpoint}`;
      console.log(`[Flask API] ${options.method || 'GET'} ${url}`);

      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || `Request failed with status ${response.status}`,
        };
      }

      return data;
    } catch (error: any) {
      console.error('[Flask API] Request failed:', error);
      console.error('[Flask API] Endpoint:', endpoint);
      console.error('[Flask API] Full URL:', `${this.baseUrl}${endpoint}`);
      
      // Provide more specific error messages
      let errorMessage = 'Network error. Cannot connect to backend server.';
      if (error.message) {
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
          errorMessage = 'Cannot connect to backend server.';
        } else {
          errorMessage = error.message;
        }
      }
      
      return {
        success: false,
        error: errorMessage,
      };
    }
  }

  // ==================== UPLOAD ====================
  
  async uploadPdf(file: File): Promise<ApiResponse<UploadResult>> {
    try {
      // Validate baseUrl is configured
      if (!this.baseUrl) {
        console.error('[Flask API] VITE_FLASK_API_URL is not configured');
        return {
          success: false,
          error: 'Backend API URL not configured. Please set VITE_FLASK_API_URL environment variable.',
        };
      }

      // Get Supabase session token for authentication
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (!token) {
        return {
          success: false,
          error: 'Authentication required. Please log in.',
        };
      }
      
      const formData = new FormData();
      formData.append('pdf', file);

      const url = `${this.baseUrl}/upload`;
      console.log(`[Flask API] POST ${url} (file: ${file.name})`);

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          // Don't set Content-Type for FormData - browser handles it
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error || `Upload failed with status ${response.status}`,
        };
      }

      return data;
    } catch (error: any) {
      console.error('[Flask API] Upload failed:', error);
      return {
        success: false,
        error: error.message || 'Failed to upload PDF. Is the Flask server running?',
      };
    }
  }

  // ==================== STATEMENTS ====================

  async getStatements(bankType?: string): Promise<ApiResponse<Statement[]>> {
    const params = bankType ? `?bankType=${bankType}` : '';
    return this.request<Statement[]>(`/statements${params}`);
  }

  async getStatement(statementId: string): Promise<ApiResponse<Statement>> {
    return this.request<Statement>(`/statements/${statementId}`);
  }

  async deleteStatement(statementId: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/statements/${statementId}`, {
      method: 'DELETE',
    });
  }

  // ==================== TRANSACTIONS ====================

  async getTransactions(params: {
    statementId?: string;
    bankType?: string;
    limit?: number;
  }): Promise<ApiResponse<Transaction[]>> {
    const queryParams = new URLSearchParams();
    if (params.statementId) queryParams.set('statementId', params.statementId);
    if (params.bankType) queryParams.set('bankType', params.bankType);
    if (params.limit) queryParams.set('limit', params.limit.toString());

    const queryString = queryParams.toString();
    return this.request<Transaction[]>(`/transactions${queryString ? `?${queryString}` : ''}`);
  }

  async getTransactionsByStatement(statementId: string): Promise<ApiResponse<Transaction[]>> {
    return this.getTransactions({ statementId });
  }

  // ==================== ANALYTICS ====================

  async getCategorySpend(bankType?: string): Promise<ApiResponse<CategorySpend[]>> {
    const params = bankType ? `?bankType=${bankType}` : '';
    return this.request<CategorySpend[]>(`/analytics/category-spend${params}`);
  }

  async getBankWiseSpend(): Promise<ApiResponse<BankWiseSpend[]>> {
    return this.request<BankWiseSpend[]>(`/analytics/bank-wise-spend`);
  }

  async getSummary(bankType?: string): Promise<ApiResponse<AnalyticsSummary>> {
    const params = bankType ? `?bankType=${bankType}` : '';
    return this.request<AnalyticsSummary>(`/analytics/summary${params}`);
  }

  // ==================== JSON EXPORT ====================

  async getNormalizedJson(statementId: string): Promise<ApiResponse<any>> {
    const statementResult = await this.getStatement(statementId);
    const transactionsResult = await this.getTransactionsByStatement(statementId);

    if (!statementResult.success || !transactionsResult.success) {
      return {
        success: false,
        error: statementResult.error || transactionsResult.error,
      };
    }

    const statement = statementResult.data!;
    const transactions = transactionsResult.data || [];

    // Convert transactions from MongoDB format (amount + direction) to debit/credit
    const convertedTransactions = transactions.map((tx: Transaction) => {
      let debit: number | null = null;
      let credit: number | null = null;
      
      if (tx.amount !== undefined && tx.direction) {
        // MongoDB format: use amount and direction
        const amount = Number(tx.amount) || 0;
        const direction = tx.direction.toLowerCase();
        if (direction === 'debit') {
          debit = amount;
          credit = null;
        } else {
          debit = null;
          credit = amount;
        }
      } else {
        // Legacy format: use debit/credit fields
        debit = tx.debit !== undefined && tx.debit !== null ? Number(tx.debit) : null;
        credit = tx.credit !== undefined && tx.credit !== null ? Number(tx.credit) : null;
      }
      
      return {
        date: tx.date,
        description: tx.description || '',
        debit,
        credit,
        balance: tx.balance,
        category: tx.category || 'Uncategorized',
        merchant: tx.merchant || null,
        channel: tx.channel || null,
      };
    });

    return {
      success: true,
      data: {
        statement: {
          id: statement._id,
          bank_name: statement.bankType || 'Unknown',
          file_name: statement.fileName || 'Untitled',
          upload_date: statement.uploadDate || statement.createdAt || new Date().toISOString(),
          account_number: statement.accountNumber || null,
          account_holder: statement.accountHolder || null,
        },
        transactions: convertedTransactions,
        summary: {
          total_transactions: convertedTransactions.length,
          total_debit: convertedTransactions.reduce((sum, tx) => sum + (tx.debit || 0), 0),
          total_credit: convertedTransactions.reduce((sum, tx) => sum + (tx.credit || 0), 0),
          final_balance: convertedTransactions.length > 0 ? (convertedTransactions[convertedTransactions.length - 1].balance || 0) : 0,
        },
      },
    };
  }

  async getCategorizedJson(statementId: string): Promise<ApiResponse<any>> {
    const statementResult = await this.getStatement(statementId);
    const transactionsResult = await this.getTransactionsByStatement(statementId);

    if (!statementResult.success || !transactionsResult.success) {
      return {
        success: false,
        error: statementResult.error || transactionsResult.error,
      };
    }

    const statement = statementResult.data!;
    const transactions = transactionsResult.data || [];

    // Convert transactions from MongoDB format (amount + direction) to debit/credit
    const convertedTransactions = transactions.map((tx: Transaction) => {
      let debit: number | null = null;
      let credit: number | null = null;
      
      if (tx.amount !== undefined && tx.direction) {
        // MongoDB format: use amount and direction
        const amount = Number(tx.amount) || 0;
        const direction = tx.direction.toLowerCase();
        if (direction === 'debit') {
          debit = amount;
          credit = null;
        } else {
          debit = null;
          credit = amount;
        }
      } else {
        // Legacy format: use debit/credit fields
        debit = tx.debit !== undefined && tx.debit !== null ? Number(tx.debit) : null;
        credit = tx.credit !== undefined && tx.credit !== null ? Number(tx.credit) : null;
      }
      
      return {
        date: tx.date,
        description: tx.description || '',
        debit,
        credit,
        balance: tx.balance,
        category: tx.category || 'Uncategorized',
        merchant: tx.merchant || null,
        channel: tx.channel || null,
      };
    });

    const grouped: Record<string, any[]> = {};
    convertedTransactions.forEach(tx => {
      const category = tx.category || 'Uncategorized';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push({
        date: tx.date,
        description: tx.description,
        debit: tx.debit,
        credit: tx.credit,
        balance: tx.balance,
        merchant: tx.merchant,
        channel: tx.channel,
      });
    });

    const categorySummary = Object.entries(grouped).map(([category, txs]) => ({
      category,
      transaction_count: txs.length,
      total_debit: txs.reduce((sum, tx) => sum + (tx.debit || 0), 0),
      total_credit: txs.reduce((sum, tx) => sum + (tx.credit || 0), 0),
    }));

    return {
      success: true,
      data: {
        statement: {
          id: statement._id,
          bank_name: statement.bankType || 'Unknown',
          file_name: statement.fileName || 'Untitled',
          account_number: statement.accountNumber || null,
          account_holder: statement.accountHolder || null,
        },
        categories: grouped,
        category_summary: categorySummary,
      },
    };
  }

  // ==================== AI SUMMARY ====================

  async getAISummary(statementId: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/analytics/ai-summary/${statementId}`);
  }

  // ==================== HEALTH CHECK ====================

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl.replace('/api', '')}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Export singleton instance
export const flaskApi = new FlaskApiClient(API_BASE_URL);

// Export utility to check if Flask is configured
export const isFlaskConfigured = () => {
  return !!import.meta.env.VITE_FLASK_API_URL;
};
