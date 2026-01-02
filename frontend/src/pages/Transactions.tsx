import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { TransactionsTable } from '@/components/dashboard/TransactionsTable';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Loader2, ListFilter } from 'lucide-react';

interface Statement {
  id: string;
  bank_name: string;
  file_name: string;
}

interface Transaction {
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
  const [statements, setStatements] = useState<Statement[]>([]);
  const [selectedStatement, setSelectedStatement] = useState<string>('all');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingTransactions, setLoadingTransactions] = useState(false);

  useEffect(() => {
    if (user) {
      fetchStatements();
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      fetchTransactions();
    }
  }, [user, selectedStatement]);

  const fetchStatements = async () => {
    try {
      const { data, error } = await supabase
        .from('bank_statements')
        .select('id, bank_name, file_name')
        .order('upload_date', { ascending: false });

      if (error) throw error;
      setStatements(data || []);
    } catch (error) {
      console.error('Error fetching statements:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    setLoadingTransactions(true);
    try {
      let query = supabase
        .from('transactions')
        .select('*')
        .order('date', { ascending: false });

      if (selectedStatement !== 'all') {
        query = query.eq('statement_id', selectedStatement);
      }

      const { data, error } = await query;
      if (error) throw error;
      setTransactions(data || []);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoadingTransactions(false);
    }
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

        {/* Statement selector */}
        <div className="flex items-center gap-4 p-4 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-2 text-muted-foreground">
            <ListFilter className="w-5 h-5" />
            <span className="text-sm font-medium">Filter by Statement:</span>
          </div>
          <Select value={selectedStatement} onValueChange={setSelectedStatement}>
            <SelectTrigger className="w-[300px]">
              <SelectValue placeholder="Select a statement" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statements</SelectItem>
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
