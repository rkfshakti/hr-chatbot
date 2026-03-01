import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('token') || null,
  role: localStorage.getItem('role') || null,
  
  setUser: (user, token, role) => {
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    set({ user, token, role });
  },
  
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    set({ user: null, token: null, role: null });
  },
}));

export const useChatStore = create((set) => ({
  messages: [],
  currentJob: null,
  top3Candidates: [],
  isLoading: false,
  error: null,
  
  addMessage: (role, content) =>
    set((state) => ({
      messages: [...state.messages, { role, content, timestamp: new Date() }],
    })),
  
  setCurrentJob: (job) => set({ currentJob: job }),
  
  setTop3Candidates: (candidates) => set({ top3Candidates: candidates }),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setError: (error) => set({ error }),
  
  clearChat: () => set({ messages: [], currentJob: null, top3Candidates: [] }),
}));

export const useResumeStore = create((set) => ({
  resumes: [],
  uploadedResumes: [],
  isLoading: false,
  
  setResumes: (resumes) => set({ resumes }),
  
  addUploadedResume: (resume) =>
    set((state) => ({
      uploadedResumes: [...state.uploadedResumes, resume],
    })),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  clearUploadedResumes: () => set({ uploadedResumes: [] }),
}));
