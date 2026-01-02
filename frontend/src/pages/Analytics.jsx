import { useEffect, useState } from "react";
import { getAnalytics } from "../api/api";
import CategoryPieChart from "../components/Charts/CategoryPieChart";

export default function Analytics() {
  const [data, setData] = useState(null);

  useEffect(() => {
    getAnalytics().then(res => setData(res.data));
  }, []);

  if (!data) return null;

  return <CategoryPieChart data={data.categories} />;
}
