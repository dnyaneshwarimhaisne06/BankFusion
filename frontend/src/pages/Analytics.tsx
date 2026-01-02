import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { CategoryChart } from '@/components/dashboard/CategoryChart';
import { MonthlyTrendChart } from '@/components/dashboard/MonthlyTrendChart';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { formatINR } from '@/lib/currency';
import { format } from 'date-fns';
import { Loader2, PieChart, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Card } from '@/components/ui/card';

interface CategoryData {
  name: string;
  value: number;
}

interface MonthlyData {
  month: string;
  credit: number;
  debit: number;
}

export default function Analytics() {
  const { user } = useAuth();
  const [categoryData, setCategoryData] = useState<CategoryData[]>([]);
  const [monthlyData, setMonthlyData] = useState<MonthlyData[]>([]);
  const [topCategories, setTopCategories] = useState<CategoryData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      fetchAnalyticsData();
    }
  }, [user]);

  const fetchAnalyticsData = async () => {
    try {
      const { data: transactions, error } = await supabase
        .from('transactions')
        .select('*');

      if (error) throw error;

      const txns = transactions || [];

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
      setTopCategories(sortedCategories.slice(0, 5));

      // Calculate monthly data
      const monthlyMap = new Map<string, { credit: number; debit: number }>();
      txns.forEach((t) => {
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
      console.error('Error fetching analytics data:', error);
    } finally {
      setLoading(false);
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

  const totalSpending = categoryData.reduce((sum, c) => sum + c.value, 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Page header */}
        <div className="animate-fade-in">
          <h1 className="text-2xl font-bold text-foreground">Analytics</h1>
          <p className="text-muted-foreground">
            Detailed insights into your spending patterns
          </p>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CategoryChart data={categoryData} loading={false} />
          <MonthlyTrendChart data={monthlyData} loading={false} />
        </div>

        {/* Top spending categories */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <PieChart className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">Top Spending Categories</h2>
          </div>
          
          {topCategories.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No spending data available</p>
          ) : (
            <div className="space-y-4">
              {topCategories.map((category, index) => {
                const percentage = totalSpending > 0 
                  ? ((category.value / totalSpending) * 100).toFixed(1)
                  : '0';
                
                return (
                  <div key={category.name} className="flex items-center gap-4">
                    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 text-primary text-sm font-bold">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-foreground">{category.name}</span>
                        <span className="text-sm text-muted-foreground">{percentage}%</span>
                      </div>
                      <div className="w-full bg-secondary rounded-full h-2">
                        <div 
                          className="bg-primary h-2 rounded-full transition-all duration-500"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-right min-w-[100px]">
                      <p className="font-semibold text-foreground">{formatINR(category.value)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Monthly comparison */}
        {monthlyData.length >= 2 && (
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp className="w-5 h-5 text-primary" />
              <h2 className="text-lg font-semibold text-foreground">Monthly Comparison</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {monthlyData.slice(-3).map((month) => {
                const netFlow = month.credit - month.debit;
                const isPositive = netFlow >= 0;
                
                return (
                  <div 
                    key={month.month} 
                    className="p-4 rounded-xl bg-secondary/50 border border-border"
                  >
                    <p className="text-sm text-muted-foreground mb-2">{month.month}</p>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Credit</span>
                        <span className="text-success font-medium">{formatINR(month.credit)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">Debit</span>
                        <span className="text-warning font-medium">{formatINR(month.debit)}</span>
                      </div>
                      <div className="pt-2 border-t border-border flex items-center justify-between">
                        <span className="text-sm font-medium">Net Flow</span>
                        <div className={`flex items-center gap-1 ${isPositive ? 'text-success' : 'text-destructive'}`}>
                          {isPositive ? (
                            <ArrowUpRight className="w-4 h-4" />
                          ) : (
                            <ArrowDownRight className="w-4 h-4" />
                          )}
                          <span className="font-semibold">{formatINR(Math.abs(netFlow))}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
