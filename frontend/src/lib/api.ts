import axios from "axios";

// Base API URL - can be configured via environment variables
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

console.log('Using API_BASE_URL:', API_BASE_URL);

// Create axios instance with common configuration
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add authorization header if token exists
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('authToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for better error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.status, error.response?.data || error.message);
    
    // Additional logging for network issues
    if (!error.response) {
      console.error(`Network error: Make sure the backend server is running at ${API_BASE_URL}`);
    }
    
    return Promise.reject(error);
  }
);

// Document types
export interface Document {
  id: string;
  filename: string;
  status: string;
  total_pages: number;
  uploaded_at: string;
  latest_job?: JobStatus;
}

export interface JobStatus {
  id: string;
  document_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  pages_processed: number;
  total_pages: number;
  model_name: string;
}

export interface ExtractionResult {
  id: string;
  page_number: number;
  content: Record<string, any>;
  processing_time: number;
  confidence_score: number | null;
}

export interface XLSXExport {
  id: string;
  filename: string;
  message: string;
  download_url: string;
}

// Authentication functions
export async function login(email: string, password: string): Promise<{ token: string; user: any }> {
  // Use form-urlencoded format as required by OAuth2PasswordRequestForm
  const formData = new URLSearchParams();
  formData.append('username', email); // Backend expects 'username', not 'email'
  formData.append('password', password);
  
  const response = await apiClient.post('/auth/login', formData.toString(), {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  
  if (response.data.access_token) {
    localStorage.setItem('authToken', response.data.access_token);
  }
  
  return {
    token: response.data.access_token,
    user: response.data.user
  };
}

export async function register(email: string, password: string, name: string): Promise<{ token: string; user: any }> {
  const response = await apiClient.post('/auth/register', { email, password, name });
  
  if (response.data.token) {
    localStorage.setItem('authToken', response.data.token);
  }
  
  return response.data;
}

export function logout(): void {
  localStorage.removeItem('authToken');
}

export async function getCurrentUser(): Promise<any> {
  const response = await apiClient.get('/auth/me');
  return response.data;
}

// Document functions
export async function uploadDocument(file: File, apiKey?: string): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  
  if (apiKey) {
    formData.append('api_key', apiKey);
  }
  
  const response = await apiClient.post('/handwriting/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
}

export async function getDocument(documentId: string): Promise<Document> {
  const response = await apiClient.get(`/handwriting/documents/${documentId}`);
  return response.data;
}

export async function processDocument(documentId: string, apiKey?: string): Promise<JobStatus> {
  const url = `/handwriting/documents/${documentId}/process`;
  const config = apiKey ? { params: { api_key: apiKey } } : undefined;
  
  const response = await apiClient.post(url, {}, config);
  return response.data;
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await apiClient.get(`/handwriting/jobs/${jobId}`);
  return response.data;
}

export async function getJobResults(jobId: string): Promise<ExtractionResult[]> {
  const response = await apiClient.get(`/handwriting/jobs/${jobId}/results`);
  return response.data;
}

export async function generateXLSX(jobId: string): Promise<XLSXExport> {
  const response = await apiClient.post(`/handwriting/jobs/${jobId}/xlsx`);
  return response.data;
}

export function getXLSXDownloadURL(exportId: string): string {
  return `${API_BASE_URL}/handwriting/xlsx/${exportId}/download`;
}

// Export all functions as an object
export const api = {
  login,
  register,
  logout,
  getCurrentUser,
  uploadDocument,
  getDocument,
  processDocument,
  getJobStatus,
  getJobResults,
  generateXLSX,
  getXLSXDownloadURL
}; 