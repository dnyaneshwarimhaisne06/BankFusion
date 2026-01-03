import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { TransactionsTable } from '@/components/dashboard/TransactionsTable';
import { useAuth } from '@/contexts/AuthContext';
import { flaskApi, Statement, Transaction } from '@/lib/api/flask-api';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Loader2, ListFilter, AlertCircle } from 'lucide-react';

interface DisplayStatement {
  id: string;
  bank_name: string;
  file_name: string;
}

interface DisplayTransaction {
  id: string;
  date: string;
  description: string;
  debit: number | null;
  credit: number | null;
  balance: number | null;
  category: string | null;
}

export default function Transactions() {
  const { user } = useAuth();
  const [statements, setStatements] = useState<DisplayStatement[]>([]);
  const [selectedStatement, setSelectedStatement] = useState<string>('');
  const [selectedBankType, setSelectedBankType] = useState<string>('');
  const [transactions, setTransactions] = useState<DisplayTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingTransactions, setLoadingTransactions] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      fetchStatements();
    }
  }, [user]);

  useEffect(() => {
    if (user && (selectedStatement || selectedBankType)) {
      fetchTransactions();
    }
  }, [user, selectedStatement, selectedBankType]);

  const fetchStatements = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await flaskApi.getStatements();
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch statements');
      }

      const transformed = (result.data || []).map(s => ({
        id: s._id,
        bank_name: s.bankType || 'Unknown',
        file_name: s.fileName || 'Untitled',
      }));
      
      setStatements(transformed);
      
      // Select first statement by default
      if (transformed.length > 0 && !selectedStatement) {
        setSelectedStatement(transformed[0].id);
      }
    } catch (err: any) {
      console.error('Error fetching statements:', err);
      setError(err.message || 'Failed to load statements');
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    if (!selectedStatement && !selectedBankType) return;
    
    setLoadingTransactions(true);
    try {
      const result = await flaskApi.getTransactions({
        statementId: selectedStatement || undefined,
        bankType: selectedBankType || undefined,
      });
      
      if (!result.success) {
        throw new Error(result.error || 'Failed to fetch transactions');
      }

      const transformed = (result.data || []).map(t => ({
        id: t._id,
        date: t.date,
        description: t.description,
        debit: t.debit,
        credit: t.credit,
        balance: t.balance,
        category: t.category,
      }));
      
      setTransactions(transformed);
    } catch (err: any) {
      console.error('Error fetching transactions:', err);
    } finally {
      setLoadingTransactions(false);
    }
  };

  const handleStatementChange = (value: string) => {
    setSelectedStatement(value);
    setSelectedBankType(''); // Clear bank filter when selecting statement
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Transactions</h1>
          <p className="text-muted-foreground">
            View and filter all your transactions
          </p>
        </div>

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-destructive/10 text-destructive">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <div>
              <p className="font-medium">Connection Error</p>
              <p className="text-sm opacity-80">{error}</p>
            </div>
          </div>
        )}

        {/* Statement selector */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-2 text-muted-foreground">
            <ListFilter className="w-5 h-5" />
            <span className="text-sm font-medium">Filter by Statement:</span>
          </div>
          <Select value={selectedStatement} onValueChange={handleStatementChange}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Select a statement" />
            </SelectTrigger>
            <SelectContent>
              {statements.map((statement) => (
                <SelectItem key={statement.id} value={statement.id}>
                  {statement.bank_name} - {statement.file_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Transactions table */}
        <TransactionsTable 
          transactions={transactions} 
          loading={loadingTransactions} 
        />
      </div>
    </DashboardLayout>
  );
}
