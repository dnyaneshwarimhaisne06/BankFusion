import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:5000/api", // your backend
});

export const uploadStatement = (file) => {
  const formData = new FormData();
  formData.append("file", file);
  return API.post("/upload", formData);
};

export const getTransactions = () => API.get("/transactions");

export const getAnalytics = () => API.get("/analytics");
