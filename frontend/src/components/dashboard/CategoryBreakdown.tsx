import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { CategorySummary } from '@/types';
import { categoryColors } from '@/lib/mockData';

interface CategoryBreakdownProps {
  data: CategorySummary[];
}

export function CategoryBreakdown({ data }: CategoryBreakdownProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg font-semibold">Spending by Category</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={2}
                dataKey="amount"
                nameKey="category"
              >
                {data.map((entry) => (
                  <Cell 
                    key={entry.category} 
                    fill={categoryColors[entry.category]}
                    stroke="transparent"
                  />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px'
                }}
                formatter={(value: number) => [`₹${value.toLocaleString('en-IN')}`, '']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-2 gap-2 mt-4">
          {data.slice(0, 6).map((item) => (
            <div key={item.category} className="flex items-center gap-2">
              <div 
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: categoryColors[item.category] }}
              />
              <span className="text-xs text-muted-foreground capitalize truncate">
                {item.category}
              </span>
              <span className="text-xs font-medium ml-auto">{item.percentage}%</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
