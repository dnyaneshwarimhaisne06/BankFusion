import { LineChart, Line, XAxis, YAxis, Tooltip, Legend } from "recharts";

export default function IncomeExpenseChart({ data }) {
  return (
    <LineChart width={600} height={300} data={data}>
      <XAxis dataKey="month" />
      <YAxis />
      <Tooltip />
      <Legend />
      <Line type="monotone" dataKey="income" stroke="#22c55e" />
      <Line type="monotone" dataKey="expense" stroke="#f97316" />
    </LineChart>
  );
}
