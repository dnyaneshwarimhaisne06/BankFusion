export interface Transaction {
  id: string;
  date: string;
  description: string;
  amount: number;
  type: 'credit' | 'debit';
  category: TransactionCategory;
  bank: BankType;
  accountNumber: string;
  balance?: number;
  isEdited?: boolean;
}

export type TransactionCategory = 
  | 'food'
  | 'travel'
  | 'rent'
  | 'utilities'
  | 'shopping'
  | 'entertainment'
  | 'healthcare'
  | 'salary'
  | 'transfer'
  | 'investment'
  | 'other';

export type BankType = 'axis' | 'hdfc' | 'icici' | 'sbi' | 'kotak' | 'other';

export interface BankAccount {
  id: string;
  bank: BankType;
  accountNumber: string;
  accountHolder: string;
  lastUpdated: string;
  balance: number;
  transactionCount: number;
}

export interface UploadedFile {
  id: string;
  name: string;
  bank: BankType;
  uploadedAt: string;
  status: 'processing' | 'completed' | 'error';
  transactionsExtracted: number;
}

export interface CategorySummary {
  category: TransactionCategory;
  amount: number;
  count: number;
  percentage: number;
}

export interface MonthlyData {
  month: string;
  income: number;
  expense: number;
}
