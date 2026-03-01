import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  register: (email, password, role, fullName) =>
    api.post('/auth/register', { email, password, role, full_name: fullName }),
  login: (email, password) =>
    api.post('/auth/login', { email, password }),
};

export const resumeAPI = {
  uploadResume: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload-resume', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  listResumes: () => api.get('/resumes'),
};

export const jdAPI = {
  analyzeJD: (jobDescription, jobTitle) =>
    api.post('/analyze-jd', { job_description: jobDescription, job_title: jobTitle }),
  matchResumes: (jobId) => api.post('/match-resumes', null, { params: { job_id: jobId } }),
  getTop3Results: (jobId) => api.get(`/top-3-results/${jobId}`),
};

export const interviewAPI = {
  sendInvite: (candidateEmails, googleMeetLink, jobId) =>
    api.post('/send-interview-invite', {
      candidate_emails: candidateEmails,
      google_meet_link: googleMeetLink,
      job_id: jobId,
    }),
};

export const chatAPI = {
  sendMessage: (message, jobDescription, resumeFileIds) =>
    api.post('/chat', {
      message,
      job_description: jobDescription,
      resume_file_ids: resumeFileIds,
    }),
};

export default api;
