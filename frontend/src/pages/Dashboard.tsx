import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { BalanceCard } from '@/components/dashboard/BalanceCard';
import { CategoryChart } from '@/components/dashboard/CategoryChart';
import { MonthlyTrendChart } from '@/components/dashboard/MonthlyTrendChart';
import { StatementsList } from '@/components/dashboard/StatementsList';
import { useAuth } from '@/contexts/AuthContext';
import { flaskApi, Statement, CategorySpend, AnalyticsSummary } from '@/lib/api/flask-api';
import { formatINR } from '@/lib/currency';
import { TrendingDown, TrendingUp, Receipt, FileText, AlertCircle } from 'lucide-react';
import { safeFormatDate } from '@/lib/utils';

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
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      fetchDashboardData();
    }
  }, [user]);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch all data from Flask backend in parallel
      const [statementsResult, summaryResult, categoryResult] = await Promise.all([
        flaskApi.getStatements(),
        flaskApi.getSummary(),
        flaskApi.getCategorySpend(),
      ]);

      // Process statements
      if (statementsResult.success && statementsResult.data) {
        const stmts = statementsResult.data;
        
        // Transform to format expected by StatementsList
        const transformedStatements = stmts.map(s => ({
          id: s._id,
          bank_name: s.bankType || 'Unknown',
          file_name: s.fileName || 'Untitled',
          upload_date: s.uploadDate || s.createdAt || '',
          status: 'processed',
        }));
        
        setStatements(transformedStatements);

        // Calculate total balance from last transaction of the most recent statement
        // For multiple statements, we use the most recent one's balance
        let totalBalance = 0;
        if (stmts.length > 0) {
          try {
            // Get the most recent statement (first in the list as they're sorted by createdAt desc)
            const mostRecentStatementId = stmts[0]._id;
            const txnsResult = await flaskApi.getTransactionsByStatement(mostRecentStatementId);
            if (txnsResult.success && txnsResult.data && txnsResult.data.length > 0) {
              // Get last transaction balance (transactions are sorted by date ascending)
              const lastTxn = txnsResult.data[txnsResult.data.length - 1];
              totalBalance = Math.abs(Number(lastTxn.balance) || 0);
            }
          } catch (e) {
            console.warn('Failed to fetch balance:', e);
            totalBalance = 0;
          }
        }
        
        setStats(prev => ({
          ...prev,
          totalBalance,
          statementCount: stmts.length,
        }));
      }

      // Process summary analytics
      if (summaryResult.success && summaryResult.data) {
        const summary = summaryResult.data;
        setStats(prev => ({
          ...prev,
          totalCredit: summary.totalCredit || 0,
          totalDebit: summary.totalDebit || 0,
          totalExpenses: summary.totalDebit || 0,
          transactionCount: summary.totalTransactions || summary.transactionCount || 0,
        }));
      }

      // Process category data
      if (categoryResult.success && categoryResult.data) {
        const categories = categoryResult.data.map(c => ({
          name: c.category,
          value: c.totalAmount,
        })).sort((a, b) => b.value - a.value);
        
        setCategoryData(categories);
      }

      // Fetch transactions for monthly trend (need all transactions)
      const allStatementsIds = statementsResult.data?.map(s => s._id) || [];
      
      if (allStatementsIds.length > 0) {
        // Get transactions for monthly chart
        const transactionsPromises = allStatementsIds.slice(0, 5).map(id => 
          flaskApi.getTransactionsByStatement(id)
        );
        
        const transactionsResults = await Promise.all(transactionsPromises);
        const allTransactions = transactionsResults
          .filter(r => r.success && r.data)
          .flatMap(r => r.data || []);

        // Calculate monthly data
        // Convert transactions from MongoDB format (amount + direction) to debit/credit
        const monthlyMap = new Map<string, { credit: number; debit: number }>();
        allTransactions.forEach((t: any) => {
          try {
            const month = safeFormatDate(t.date, 'MMM yyyy', 'Unknown');
            if (month !== 'Unknown') {
            const existing = monthlyMap.get(month) || { credit: 0, debit: 0 };
              
              // Handle MongoDB format (amount + direction) or legacy format (debit/credit)
              let debit = 0;
              let credit = 0;
              
              if (t.amount !== undefined && t.direction) {
                // MongoDB format
                const amount = Number(t.amount) || 0;
                const direction = t.direction.toLowerCase();
                if (direction === 'debit') {
                  debit = amount;
                } else {
                  credit = amount;
                }
              } else {
                // Legacy format
                debit = Number(t.debit) || 0;
                credit = Number(t.credit) || 0;
              }
              
            monthlyMap.set(month, {
                credit: existing.credit + credit,
                debit: existing.debit + debit,
            });
            }
          } catch (e) {
            // Skip invalid dates
          }
        });

        const sortedMonthly = Array.from(monthlyMap.entries())
          .map(([month, data]) => ({ month, ...data }))
          .sort((a, b) => new Date(a.month).getTime() - new Date(b.month).getTime());

        setMonthlyData(sortedMonthly);
      }
    } catch (err: any) {
      console.error('Error fetching dashboard data:', err);
      setError(err.message || 'Failed to load dashboard data. Is the Flask server running?');
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

        {/* Total Balance Card */}
        <div className="animate-slide-up">
          <BalanceCard
            title="Overall Total Balance"
            balance={formatINR(Math.abs(stats.totalBalance))}
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
