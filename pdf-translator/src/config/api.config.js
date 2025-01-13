const API_CONFIG = {
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'multipart/form-data',
    'Accept': 'application/json'
  }
};

export default API_CONFIG;