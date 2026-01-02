import { useEffect, useState } from "react";
import { getTransactions, getAnalytics } from "../api/api";
import UploadStatement from "../components/UploadStatement";
import IncomeExpenseChart from "../components/Charts/IncomeExpenseChart";
import CategoryPieChart from "../components/Charts/CategoryPieChart";

export default function Dashboard() {
  const [transactions, setTransactions] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  const loadData = async () => {
    const txRes = await getTransactions();
    const anRes = await getAnalytics();
    setTransactions(txRes.data);
    setAnalytics(anRes.data);
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <>
      <UploadStatement onSuccess={loadData} />

      {analytics && (
        <>
          <IncomeExpenseChart data={analytics.monthly} />
          <CategoryPieChart data={analytics.categories} />
        </>
      )}
    </>
  );
}
