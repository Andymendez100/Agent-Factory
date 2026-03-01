import axios from "axios";

/** Axios instance pre-configured for the backend API. */
const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export default api;
