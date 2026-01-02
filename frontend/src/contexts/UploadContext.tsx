import { createContext, useContext, useState, ReactNode } from 'react';
import { BankType } from '@/types';

export interface ProcessedFile {
  id: string;
  name: string;
  bank: BankType | null;
  uploadedAt: string;
  status: 'uploading' | 'processing' | 'detecting' | 'completed' | 'error';
  transactionsExtracted: number;
  jsonData: object | null;
  errorMessage?: string;
}

interface UploadContextType {
  files: ProcessedFile[];
  addFile: (file: File) => void;
  getFileById: (id: string) => ProcessedFile | undefined;
  clearFiles: () => void;
}

const UploadContext = createContext<UploadContextType | undefined>(undefined);

// Mock JSON data for demo
const generateMockJson = (fileName: string, bank: BankType) => ({
  metadata: {
    fileName,
    bank,
    processedAt: new Date().toISOString(),
    currency: "INR",
    accountNumber: "XXXX" + Math.floor(1000 + Math.random() * 9000),
  },
  summary: {
    openingBalance: Math.floor(50000 + Math.random() * 100000),
    closingBalance: Math.floor(50000 + Math.random() * 100000),
    totalCredits: Math.floor(100000 + Math.random() * 200000),
    totalDebits: Math.floor(80000 + Math.random() * 150000),
    transactionCount: Math.floor(15 + Math.random() * 40),
  },
  transactions: Array.from({ length: Math.floor(10 + Math.random() * 20) }, (_, i) => ({
    id: `TXN${Date.now()}${i}`,
    date: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    description: ['Salary Credit', 'UPI Payment', 'NEFT Transfer', 'ATM Withdrawal', 'Online Shopping', 'Utility Bill', 'Rent Payment'][Math.floor(Math.random() * 7)],
    amount: Math.floor(500 + Math.random() * 50000),
    type: Math.random() > 0.4 ? 'debit' : 'credit',
    category: ['income', 'food', 'shopping', 'utilities', 'rent', 'travel', 'entertainment'][Math.floor(Math.random() * 7)],
    balance: Math.floor(50000 + Math.random() * 100000),
  })),
});

export function UploadProvider({ children }: { children: ReactNode }) {
  const [files, setFiles] = useState<ProcessedFile[]>([]);

  const detectBank = (): BankType => {
    const banks: BankType[] = ['hdfc', 'icici', 'axis', 'sbi', 'kotak'];
    return banks[Math.floor(Math.random() * banks.length)];
  };

  const addFile = (file: File) => {
    const fileId = Math.random().toString(36).substr(2, 9);
    
    const newFile: ProcessedFile = {
      id: fileId,
      name: file.name,
      bank: null,
      uploadedAt: new Date().toISOString(),
      status: 'uploading',
      transactionsExtracted: 0,
      jsonData: null,
    };

    setFiles(prev => [newFile, ...prev]);

    // Simulate upload progress
    setTimeout(() => {
      setFiles(prev => prev.map(f => 
        f.id === fileId ? { ...f, status: 'detecting' as const } : f
      ));
    }, 1000);

    // Simulate bank detection
    setTimeout(() => {
      const detectedBank = detectBank();
      setFiles(prev => prev.map(f => 
        f.id === fileId ? { ...f, bank: detectedBank, status: 'processing' as const } : f
      ));
    }, 2500);

    // Simulate processing complete
    setTimeout(() => {
      const detectedBank = detectBank();
      const transactionCount = Math.floor(15 + Math.random() * 35);
      setFiles(prev => prev.map(f => 
        f.id === fileId ? { 
          ...f, 
          bank: f.bank || detectedBank,
          status: 'completed' as const, 
          transactionsExtracted: transactionCount,
          jsonData: generateMockJson(file.name, f.bank || detectedBank),
        } : f
      ));
    }, 4500);
  };

  const getFileById = (id: string) => files.find(f => f.id === id);

  const clearFiles = () => setFiles([]);

  return (
    <UploadContext.Provider value={{ files, addFile, getFileById, clearFiles }}>
      {children}
    </UploadContext.Provider>
  );
}

export function useUpload() {
  const context = useContext(UploadContext);
  if (context === undefined) {
    throw new Error('useUpload must be used within an UploadProvider');
  }
  return context;
}
