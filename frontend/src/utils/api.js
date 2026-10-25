import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

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

export default api;
