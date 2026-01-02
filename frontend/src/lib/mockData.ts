import { Transaction, BankAccount, CategorySummary, MonthlyData } from '@/types';

export const mockTransactions: Transaction[] = [
  { id: '1', date: '2024-01-15', description: 'Swiggy Order', amount: 450, type: 'debit', category: 'food', bank: 'hdfc', accountNumber: '****4521' },
  { id: '2', date: '2024-01-14', description: 'Salary Credit', amount: 85000, type: 'credit', category: 'salary', bank: 'hdfc', accountNumber: '****4521' },
  { id: '3', date: '2024-01-13', description: 'Amazon Purchase', amount: 2499, type: 'debit', category: 'shopping', bank: 'axis', accountNumber: '****7832' },
  { id: '4', date: '2024-01-12', description: 'Uber Ride', amount: 380, type: 'debit', category: 'travel', bank: 'icici', accountNumber: '****9012' },
  { id: '5', date: '2024-01-11', description: 'Netflix Subscription', amount: 649, type: 'debit', category: 'entertainment', bank: 'hdfc', accountNumber: '****4521' },
  { id: '6', date: '2024-01-10', description: 'Electricity Bill', amount: 1850, type: 'debit', category: 'utilities', bank: 'axis', accountNumber: '****7832' },
  { id: '7', date: '2024-01-09', description: 'House Rent', amount: 25000, type: 'debit', category: 'rent', bank: 'hdfc', accountNumber: '****4521' },
  { id: '8', date: '2024-01-08', description: 'Freelance Payment', amount: 15000, type: 'credit', category: 'salary', bank: 'icici', accountNumber: '****9012' },
  { id: '9', date: '2024-01-07', description: 'Pharmacy', amount: 890, type: 'debit', category: 'healthcare', bank: 'axis', accountNumber: '****7832' },
  { id: '10', date: '2024-01-06', description: 'Mutual Fund SIP', amount: 5000, type: 'debit', category: 'investment', bank: 'hdfc', accountNumber: '****4521' },
];

export const mockBankAccounts: BankAccount[] = [
  { id: '1', bank: 'hdfc', accountNumber: '****4521', accountHolder: 'John Doe', lastUpdated: '2024-01-15', balance: 125450, transactionCount: 45 },
  { id: '2', bank: 'axis', accountNumber: '****7832', accountHolder: 'John Doe', lastUpdated: '2024-01-14', balance: 45780, transactionCount: 28 },
  { id: '3', bank: 'icici', accountNumber: '****9012', accountHolder: 'John Doe', lastUpdated: '2024-01-13', balance: 32100, transactionCount: 15 },
];

export const mockCategorySummary: CategorySummary[] = [
  { category: 'rent', amount: 25000, count: 1, percentage: 35 },
  { category: 'food', amount: 8500, count: 25, percentage: 12 },
  { category: 'shopping', amount: 12000, count: 15, percentage: 17 },
  { category: 'travel', amount: 5400, count: 18, percentage: 8 },
  { category: 'utilities', amount: 4500, count: 5, percentage: 6 },
  { category: 'entertainment', amount: 2500, count: 8, percentage: 4 },
  { category: 'healthcare', amount: 3200, count: 4, percentage: 5 },
  { category: 'investment', amount: 10000, count: 2, percentage: 14 },
];

export const mockMonthlyData: MonthlyData[] = [
  { month: 'Aug', income: 95000, expense: 62000 },
  { month: 'Sep', income: 88000, expense: 58000 },
  { month: 'Oct', income: 102000, expense: 71000 },
  { month: 'Nov', income: 91000, expense: 64000 },
  { month: 'Dec', income: 115000, expense: 78000 },
  { month: 'Jan', income: 100000, expense: 71100 },
];

export const categoryColors: Record<string, string> = {
  food: 'hsl(35, 92%, 50%)',
  travel: 'hsl(210, 100%, 50%)',
  rent: 'hsl(160, 84%, 39%)',
  utilities: 'hsl(280, 70%, 50%)',
  shopping: 'hsl(340, 80%, 55%)',
  entertainment: 'hsl(45, 90%, 50%)',
  healthcare: 'hsl(0, 70%, 55%)',
  salary: 'hsl(160, 84%, 45%)',
  transfer: 'hsl(200, 70%, 50%)',
  investment: 'hsl(120, 60%, 45%)',
  other: 'hsl(220, 10%, 50%)',
};

export const bankLogos: Record<string, { name: string; color: string }> = {
  hdfc: { name: 'HDFC Bank', color: 'hsl(210, 100%, 35%)' },
  axis: { name: 'Axis Bank', color: 'hsl(340, 80%, 45%)' },
  icici: { name: 'ICICI Bank', color: 'hsl(25, 90%, 50%)' },
  sbi: { name: 'SBI', color: 'hsl(210, 80%, 45%)' },
  kotak: { name: 'Kotak Bank', color: 'hsl(0, 75%, 45%)' },
  other: { name: 'Other', color: 'hsl(220, 10%, 50%)' },
};
