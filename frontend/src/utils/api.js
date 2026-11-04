import axios from 'axios';

const isLocalhost = typeof window !== 'undefined' && (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
);

const API_BASE_URL = import.meta.env.VITE_API_URL || (
  isLocalhost
    ? 'http://localhost:8000/api/v1'
    : 'https://vyapar-backend-gpow.onrender.com/api/v1'
);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to inject JWT bearer token
api.interceptors.request.use(
  (config) => {
    // If request payload is FormData, remove manual Content-Type so browser sets multipart/form-data with boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    // 1. Read Supabase auth token from local storage
    const storageKeys = Object.keys(localStorage);
    const authKey = storageKeys.find(key => key.startsWith('sb-') && key.endsWith('-auth-token'));
    
    if (authKey) {
      try {
        const sessionData = JSON.parse(localStorage.getItem(authKey));
        const token = sessionData?.access_token;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
          return config;
        }
      } catch (err) {
        console.error('Error parsing auth session token:', err);
      }
    }

    // 2. Check if mock user session exists in local storage (sandbox fallback)
    const mockUser = localStorage.getItem('mock_user');
    if (mockUser) {
      config.headers.Authorization = 'Bearer simulated-token';
      return config;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for user-friendly error diagnostics
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.message === 'Network Error') {
      const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
      const isLocalhostApi = API_BASE_URL.includes('localhost') || API_BASE_URL.includes('127.0.0.1');
      if (isHttps && isLocalhostApi) {
        error.message = 'Backend API is offline or unreachable. Frontend is deployed on HTTPS, but backend URL is pointing to localhost:8000. Start backend locally or deploy it to Render.';
      } else {
        error.message = 'Cannot connect to backend server. Please verify the backend is running at ' + API_BASE_URL;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
