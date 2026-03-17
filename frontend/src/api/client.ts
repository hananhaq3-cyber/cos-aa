/**
 * Axios API client with JWT interceptor and base URL configuration.
 */
import axios from "axios";

// Use VITE_API_URL env variable, or fallback to relative path for localhost
const baseURL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : "/api/v1";

const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
  timeout: 120_000,
  withCredentials: true,  // Include cookies with CORS requests
});

// Attach JWT token from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("cos_aa_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 — redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("cos_aa_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
