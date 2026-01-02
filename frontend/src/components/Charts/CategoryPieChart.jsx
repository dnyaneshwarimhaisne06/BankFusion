import { PieChart, Pie, Tooltip, Cell } from "recharts";

const COLORS = ["#22c55e", "#3b82f6", "#f97316", "#ec4899", "#8b5cf6"];

export default function CategoryPieChart({ data }) {
  return (
    <PieChart width={350} height={300}>
      <Pie data={data} dataKey="value" nameKey="category" outerRadius={120}>
        {data.map((_, i) => (
          <Cell key={i} fill={COLORS[i % COLORS.length]} />
        ))}
      </Pie>
      <Tooltip />
    </PieChart>
  );
}
