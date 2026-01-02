import { uploadStatement } from "../api/api";

export default function UploadStatement({ onSuccess }) {
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    await uploadStatement(file);
    onSuccess(); // refresh dashboard
  };

  return (
    <div className="card">
      <h3>Upload Bank Statement</h3>
      <input type="file" accept=".pdf,.csv,.xls,.xlsx" onChange={handleUpload} />
    </div>
  );
}
