import axios from 'axios';

const getBackendUrl = () => {
  const envUrl = process.env.REACT_APP_BACKEND_URL;
  const currentOrigin = window.location.origin;
  const isLocalClient = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

  if (!envUrl) return currentOrigin;

  // If we're on a live site but the env URL is localhost, 
  // we want to use the current host but keep the port from the env URL if it's there.
  if (!isLocalClient && (envUrl.includes('localhost') || envUrl.includes('127.0.0.1'))) {
    try {
      const url = new URL(envUrl);
      if (url.port) {
        return `${window.location.protocol}//${window.location.hostname}:${url.port}`;
      }
    } catch (e) {
      // Fallback if URL parsing fails
    }
    return currentOrigin;
  }

  return envUrl;
};

const BACKEND_URL = getBackendUrl();
export const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      // Clear auth data and redirect to login for both 401 and 403
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('userSection');
      console.error('Authentication error - redirecting to login');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
