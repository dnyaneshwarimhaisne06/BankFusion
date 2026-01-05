import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { BalanceCard } from '@/components/dashboard/BalanceCard';
import { CategoryChart } from '@/components/dashboard/CategoryChart';
import { MonthlyTrendChart } from '@/components/dashboard/MonthlyTrendChart';
import { TransactionsTable } from '@/components/dashboard/TransactionsTable';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { flaskApi, Statement as ApiStatement, Transaction as ApiTransaction } from '@/lib/api/flask-api';
import { formatINR } from '@/lib/currency';
import { safeFormatDate } from '@/lib/utils';
import { format } from 'date-fns';
import { 
  ArrowLeft, 
  TrendingDown, 
  TrendingUp, 
  Receipt,
  Building2,
  Calendar,
  FileText,
  Loader2,
  Download,
  FileJson
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface Statement {
  id: string;
  bank_name: string;
  file_name: string;
  upload_date: string;
  status: string;
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

interface Stats {
  totalBalance: number;
  totalCredit: number;
  totalDebit: number;
  transactionCount: number;
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

const statusColors: Record<string, string> = {
  'processed': 'bg-success/10 text-success border-success/20',
  'processing': 'bg-warning/10 text-warning border-warning/20',
  'failed': 'bg-destructive/10 text-destructive border-destructive/20',
};

export default function StatementDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [statement, setStatement] = useState<Statement | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [stats, setStats] = useState<Stats>({
    totalBalance: 0,
    totalCredit: 0,
    totalDebit: 0,
    transactionCount: 0,
  });
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (user && id) {
      fetchStatementData();
    }
  }, [user, id]);

  const fetchStatementData = async () => {
    if (!id) {
      setLoading(false);
      return;
    }

    try {
      // Fetch statement from Flask API
      const statementResult = await flaskApi.getStatement(id);

      if (!statementResult.success || !statementResult.data) {
        console.error('Statement not found:', statementResult.error);
        setLoading(false);
        return;
      }
      
      const apiStatement = statementResult.data;
      
      // Transform API statement to component format
      setStatement({
        id: apiStatement._id,
        bank_name: apiStatement.bankType || 'Unknown',
        file_name: apiStatement.fileName || 'Untitled',
        upload_date: apiStatement.uploadDate || '',
        status: 'processed',
      });

      // Fetch transactions for this statement
      const transactionsResult = await flaskApi.getTransactionsByStatement(id);
      
      if (!transactionsResult.success) {
        throw new Error(transactionsResult.error || 'Failed to fetch transactions');
      }
      
      const apiTransactions = transactionsResult.data || [];
      
      // Transform API transactions to component format
      // MongoDB uses 'amount' and 'direction', so we need to convert to debit/credit
      const txns = apiTransactions.map((t: ApiTransaction) => {
        // Check if MongoDB format (amount + direction) or legacy format (debit/credit)
        const hasAmount = t.amount !== undefined && t.amount !== null;
        const hasDirection = t.direction !== undefined && t.direction !== null;
        
        let debit: number | null = null;
        let credit: number | null = null;
        
        if (hasAmount && hasDirection) {
          // MongoDB format: use amount and direction
          const amount = Number(t.amount) || 0;
          const direction = t.direction.toLowerCase();
          if (direction === 'debit') {
            debit = amount;
            credit = null;
          } else {
            debit = null;
            credit = amount;
          }
        } else {
          // Legacy format: use debit/credit fields
          debit = t.debit !== undefined && t.debit !== null ? Number(t.debit) : null;
          credit = t.credit !== undefined && t.credit !== null ? Number(t.credit) : null;
        }
        
        return {
          id: t._id,
          date: t.date,
          description: t.description || '',
          debit,
          credit,
          balance: t.balance,
          category: t.category,
        };
      });
      
      // Sort transactions by date (oldest first) to get correct last balance
      txns.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
      
      setTransactions(txns);

      // Calculate stats - balance is from the last transaction (most recent)
      const totalDebit = txns.reduce((sum, t) => sum + (Number(t.debit) || 0), 0);
      const totalCredit = txns.reduce((sum, t) => sum + (Number(t.credit) || 0), 0);
      const lastBalance = txns.length > 0 ? Number(txns[txns.length - 1].balance) || 0 : 0;

      setStats({
        totalBalance: lastBalance,
        totalCredit,
        totalDebit,
        transactionCount: txns.length,
      });

      // Calculate category data
      const categoryMap = new Map<string, number>();
      txns.forEach((t) => {
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
      txns.forEach((t) => {
        const month = safeFormatDate(t.date, 'MMM yyyy', 'Unknown');
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
    } catch (error: any) {
      console.error('Error fetching statement data:', error);
      const errorMessage = error?.message || error?.error || String(error) || 'Could not fetch statement data';
      toast({
        title: 'Failed to load statement',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const downloadJSON = (data: object, filename: string) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleQuickExport = async () => {
    if (!statement) return;
    
    setExporting(true);
    try {
      const summaryReport = {
        report_title: 'Bank Statement Summary',
        generated_at: new Date().toISOString(),
        bank_details: {
          bank_name: statement.bank_name,
          file_name: statement.file_name,
          upload_date: statement.upload_date,
        },
        financial_summary: {
          total_balance: stats.totalBalance,
          total_balance_formatted: formatINR(stats.totalBalance),
          total_credit: stats.totalCredit,
          total_credit_formatted: formatINR(stats.totalCredit),
          total_debit: stats.totalDebit,
          total_debit_formatted: formatINR(stats.totalDebit),
        },
        transactions: transactions.map(t => ({
          date: t.date,
          description: t.description,
          category: t.category || 'Uncategorized',
          debit: Number(t.debit) || 0,
          credit: Number(t.credit) || 0,
          balance: Number(t.balance) || 0,
        })),
      };

      downloadJSON(summaryReport, `${statement.bank_name}_summary_${format(new Date(), 'yyyy-MM-dd')}.json`);
      toast.success('Statement exported successfully');
    } catch (error) {
      toast.error('Failed to export');
    } finally {
      setExporting(false);
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

  if (!statement) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-foreground mb-2">
            Statement not found
          </h2>
          <p className="text-muted-foreground mb-6">
            The statement you're looking for doesn't exist or has been deleted.
          </p>
          <Link to="/statements">
            <Button>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Statements
            </Button>
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page header */}
        <div className="animate-fade-in">
          <Link
            to="/statements"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Statements
          </Link>
          
          <div className="flex flex-col lg:flex-row lg:items-center gap-4">
            <div className="flex items-center gap-4 flex-1">
              <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/10">
                <Building2 className="w-7 h-7 text-primary" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-foreground truncate max-w-md">
                  {statement.file_name}
                </h1>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-muted-foreground">{statement.bank_name}</span>
                  <Badge
                    variant="outline"
                    className={cn("capitalize", statusColors[statement.status] || statusColors['processing'])}
                  >
                    {statement.status}
                  </Badge>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="w-4 h-4" />
                Uploaded {safeFormatDate(statement.upload_date, 'dd MMM yyyy, hh:mm a')}
              </div>
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleQuickExport}
                disabled={exporting}
              >
                {exporting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Download className="w-4 h-4 mr-2" />
                )}
                Export
              </Button>
            </div>
          </div>
        </div>

        {/* Balance Card */}
        <div className="animate-slide-up">
          <BalanceCard
            title="Statement Balance"
            balance={formatINR(Math.abs(stats.totalBalance))}
            subtitle="Balance from last transaction"
          />
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-slide-up">
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
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CategoryChart data={categoryData} loading={false} />
          <MonthlyTrendChart data={monthlyData} loading={false} />
        </div>

        {/* Transactions table */}
        <div>
          <h2 className="text-lg font-semibold text-foreground mb-4">Transactions</h2>
          <TransactionsTable transactions={transactions} loading={false} />
        </div>
      </div>
    </DashboardLayout>
  );
}
