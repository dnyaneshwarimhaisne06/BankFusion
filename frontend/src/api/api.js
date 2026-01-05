import axios from "axios";

// Use environment variable only - no fallback to localhost
const API_BASE_URL = import.meta.env.VITE_FLASK_API_URL;

if (!API_BASE_URL) {
  console.error('VITE_FLASK_API_URL is not configured. Please set it in your .env file.');
}

const API = axios.create({
  baseURL: API_BASE_URL || '', // Will fail if not configured, preventing silent localhost fallback
});

export const uploadStatement = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return API.post("/upload", formData);
};

export const getTransactions = () => API.get("/transactions");

export const getAnalytics = () => API.get("/analytics");
