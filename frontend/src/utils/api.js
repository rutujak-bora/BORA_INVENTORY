import axios from 'axios';

const BACKEND_URL =  process.env.REACT_APP_BACKEND_URL || window.location.origin;
const API_BASE = `${BACKEND_URL}/api`;

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
