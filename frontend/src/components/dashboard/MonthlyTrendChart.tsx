import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { formatINRCompact } from '@/lib/currency';

interface MonthlyData {
  month: string;
  credit: number;
  debit: number;
}

interface MonthlyTrendChartProps {
  data: MonthlyData[];
  loading?: boolean;
}

export function MonthlyTrendChart({ data, loading }: MonthlyTrendChartProps) {
  if (loading) {
    return (
      <div className="rounded-2xl border bg-card p-6 h-[400px]">
        <div className="flex items-center justify-center h-full">
          <div className="animate-pulse text-muted-foreground">Loading chart...</div>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-2xl border bg-card p-6 h-[400px]">
        <h3 className="text-lg font-semibold mb-4">Monthly Credit vs Debit</h3>
        <div className="flex items-center justify-center h-[300px]">
          <p className="text-muted-foreground">No monthly data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Monthly Credit vs Debit</h3>
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="creditGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(160, 84%, 39%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(160, 84%, 39%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="debitGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0.3} />
                <stop offset="95%" stopColor="hsl(0, 84%, 60%)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="month"
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: 'hsl(var(--border))' }}
            />
            <YAxis
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickFormatter={(value) => formatINRCompact(value)}
            />
            <Tooltip
              formatter={(value: number, name: string) => [
                formatINRCompact(value),
                name.charAt(0).toUpperCase() + name.slice(1),
              ]}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.75rem',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Legend
              formatter={(value) => (
                <span className="text-sm text-foreground capitalize">{value}</span>
              )}
            />
            <Area
              type="monotone"
              dataKey="credit"
              stroke="hsl(160, 84%, 39%)"
              strokeWidth={2}
              fill="url(#creditGradient)"
            />
            <Area
              type="monotone"
              dataKey="debit"
              stroke="hsl(0, 84%, 60%)"
              strokeWidth={2}
              fill="url(#debitGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
