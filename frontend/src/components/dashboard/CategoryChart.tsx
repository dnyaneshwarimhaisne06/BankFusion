import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { formatINR } from '@/lib/currency';

interface CategoryData {
  name: string;
  value: number;
}

interface CategoryChartProps {
  data: CategoryData[];
  loading?: boolean;
}

const COLORS = [
  'hsl(220, 90%, 56%)',
  'hsl(160, 84%, 39%)',
  'hsl(38, 92%, 50%)',
  'hsl(0, 84%, 60%)',
  'hsl(280, 70%, 60%)',
  'hsl(180, 70%, 45%)',
  'hsl(330, 70%, 55%)',
  'hsl(60, 70%, 50%)',
];

export function CategoryChart({ data, loading }: CategoryChartProps) {
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
        <h3 className="text-lg font-semibold mb-4">Category-wise Spending</h3>
        <div className="flex items-center justify-center h-[300px]">
          <p className="text-muted-foreground">No category data available</p>
        </div>
      </div>
    );
  }

  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="rounded-2xl border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Category-wise Spending</h3>
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => formatINR(value)}
              contentStyle={{
                backgroundColor: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '0.75rem',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            />
            <Legend
              formatter={(value) => (
                <span className="text-sm text-foreground">{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 space-y-2">
        {data.slice(0, 4).map((item, index) => (
          <div key={item.name} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span className="text-sm text-muted-foreground">{item.name}</span>
            </div>
            <div className="text-right">
              <span className="text-sm font-medium">{formatINR(item.value)}</span>
              <span className="text-xs text-muted-foreground ml-2">
                ({((item.value / total) * 100).toFixed(1)}%)
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
