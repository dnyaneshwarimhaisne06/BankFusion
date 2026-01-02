import { Link } from "react-router-dom";

export default function Sidebar() {
  return (
    <div
      style={{
        width: "220px",
        height: "100vh",
        backgroundColor: "#0f172a",
        color: "white",
        padding: "20px"
      }}
    >
      <h2 style={{ marginBottom: "20px" }}>BankFusion</h2>

      <nav style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <Link to="/" style={{ color: "white", textDecoration: "none" }}>
          Dashboard
        </Link>

        <Link to="/transactions" style={{ color: "white", textDecoration: "none" }}>
          Transactions
        </Link>

        <Link to="/analytics" style={{ color: "white", textDecoration: "none" }}>
          Analytics
        </Link>
      </nav>
    </div>
  );
}
