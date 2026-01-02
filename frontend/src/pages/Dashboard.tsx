import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { BalanceCard } from '@/components/dashboard/BalanceCard';
import { CategoryChart } from '@/components/dashboard/CategoryChart';
import { MonthlyTrendChart } from '@/components/dashboard/MonthlyTrendChart';
import { StatementsList } from '@/components/dashboard/StatementsList';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { formatINR } from '@/lib/currency';
import { TrendingDown, TrendingUp, Receipt, FileText } from 'lucide-react';
import { format } from 'date-fns';

interface DashboardStats {
  totalBalance: number;
  totalExpenses: number;
  totalCredit: number;
  totalDebit: number;
  transactionCount: number;
  statementCount: number;
}

interface CategoryData {
  name: string;
  value: number;
}

interface MonthlyData {
  month: string;
  credit: number;
  debit: number;
}

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats>({
    totalBalance: 0,
    totalExpenses: 0,
    totalCredit: 0,
    totalDebit: 0,
    transactionCount: 0,
    statementCount: 0,
  });
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([]);
  const [statements, setStatements] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      fetchDashboardData();
    }
  }, [user]);

  const fetchDashboardData = async () => {
    try {
      // Fetch statements
      const { data: statementsData, error: statementsError } = await supabase
        .from('bank_statements')
        .select('*')
        .order('upload_date', { ascending: false });

      if (statementsError) throw statementsError;
      setStatements(statementsData || []);

      // Fetch all transactions
      const { data: transactionsData, error: transactionsError } = await supabase
        .from('transactions')
        .select('*');

      if (transactionsError) throw transactionsError;

      const transactions = transactionsData || [];

      // Calculate total balance by summing the latest balance from each statement
      let totalBalance = 0;
      const statementIds = [...new Set(transactions.map(t => t.statement_id))];
      
      for (const statementId of statementIds) {
        const statementTxns = transactions
          .filter(t => t.statement_id === statementId)
          .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
        
        if (statementTxns.length > 0) {
          totalBalance += Number(statementTxns[0].balance) || 0;
        }
      }

      // Calculate stats
      const totalDebit = transactions.reduce((sum, t) => sum + (Number(t.debit) || 0), 0);
      const totalCredit = transactions.reduce((sum, t) => sum + (Number(t.credit) || 0), 0);

      setStats({
        totalBalance,
        totalExpenses: totalDebit,
        totalCredit,
        totalDebit,
        transactionCount: transactions.length,
        statementCount: statementsData?.length || 0,
      });

      // Calculate category data
      const categoryMap = new Map<string, number>();
      transactions.forEach((t) => {
        const category = t.category || 'Uncategorized';
        const debit = Number(t.debit) || 0;
        if (debit > 0) {
          categoryMap.set(category, (categoryMap.get(category) || 0) + debit);
        }
      });

      const sortedCategories = Array.from(categoryMap.entries())
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value);

      setCategoryData(sortedCategories);

      // Calculate monthly data
      const monthlyMap = new Map<string, { credit: number; debit: number }>();
      transactions.forEach((t) => {
        const month = format(new Date(t.date), 'MMM yyyy');
        const existing = monthlyMap.get(month) || { credit: 0, debit: 0 };
        monthlyMap.set(month, {
          credit: existing.credit + (Number(t.credit) || 0),
          debit: existing.debit + (Number(t.debit) || 0),
        });
      });

      const sortedMonthly = Array.from(monthlyMap.entries())
        .map(([month, data]) => ({ month, ...data }))
        .sort((a, b) => new Date(a.month).getTime() - new Date(b.month).getTime());

      setMonthlyData(sortedMonthly);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of all your uploaded bank statements
          </p>
        </div>

        {/* Total Balance Card */}
        <div className="animate-slide-up">
          <BalanceCard
            title="Overall Total Balance"
            balance={formatINR(stats.totalBalance)}
            subtitle={`Across ${stats.statementCount} bank statement${stats.statementCount !== 1 ? 's' : ''}`}
          />
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-up">
          <StatsCard
            title="Total Credit"
            value={formatINR(stats.totalCredit)}
            icon={<TrendingUp className="w-5 h-5" />}
            variant="success"
          />
          <StatsCard
            title="Total Debit"
            value={formatINR(stats.totalDebit)}
            icon={<TrendingDown className="w-5 h-5" />}
            variant="warning"
          />
          <StatsCard
            title="Transactions"
            value={stats.transactionCount.toLocaleString('en-IN')}
            icon={<Receipt className="w-5 h-5" />}
            variant="info"
          />
          <StatsCard
            title="Statements"
            value={stats.statementCount.toLocaleString('en-IN')}
            icon={<FileText className="w-5 h-5" />}
            variant="default"
          />
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CategoryChart data={categoryData} loading={loading} />
          <MonthlyTrendChart data={monthlyData} loading={loading} />
        </div>

        {/* Statements list */}
        <StatementsList statements={statements} loading={loading} />
      </div>
    </DashboardLayout>
  );
}
