import React, { useState } from 'react';
import { chatAPI, jdAPI } from '../api';
import { useChatStore } from '../store';
import { format } from 'date-fns';

export function Chat() {
  const [input, setInput] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [showJDInput, setShowJDInput] = useState(false);
  const [jobTitle, setJobTitle] = useState('');
  
  const messages = useChatStore((state) => state.messages);
  const isLoading = useChatStore((state) => state.isLoading);
  const error = useChatStore((state) => state.error);
  
  const addMessage = useChatStore((state) => state.addMessage);
  const setLoading = useChatStore((state) => state.setLoading);
  const setError = useChatStore((state) => state.setError);
  const setCurrentJob = useChatStore((state) => state.setCurrentJob);
  
  const handleSendMessage = async () => {
    if (!input.trim() && !jobDescription.trim()) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Add user message
      addMessage('user', input || `JD: ${jobDescription.substring(0, 100)}...`);
      
      // If job description provided, analyze it first
      if (jobDescription.trim()) {
        const jdResponse = await jdAPI.analyzeJD(jobDescription, jobTitle);
        setCurrentJob(jdResponse.data);
        
        const skills = (jdResponse.data.required_skills || []).join(', ') || 'None extracted';
        const mustHave = (jdResponse.data.must_have_requirements || []).join(', ') || 'See job description';
        const expYears = jdResponse.data.experience_years || 'Not specified';
        
        // Add job analysis to chat
        addMessage('assistant', `✅ Job Analysis Complete!\n\nJob ID: ${jdResponse.data.job_id}\nRequired Skills: ${skills}\nExperience: ${expYears} years\nMust-Have: ${mustHave}`);
        
        setShowJDInput(false);
        setJobDescription('');
      } else {
        // Send regular chat message
        const response = await chatAPI.sendMessage(input, null, null);
        addMessage('assistant', response.data.response);
      }
      
      setInput('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Error processing request');
      addMessage('assistant', `Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="flex flex-col h-full bg-gray-100">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4 shadow-lg">
        <h1 className="text-2xl font-bold">HR Chatbot - Resume Matching</h1>
        <p className="text-blue-100">Agentic RAG System</p>
      </div>
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-10">
            <p className="text-lg mb-4">👋 Welcome to HR Chatbot</p>
            <p>Start by entering a job description or uploading resumes</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-lg px-4 py-2 rounded-lg ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-300'
                }`}
              >
                <p className="text-sm">{msg.content}</p>
                <p className="text-xs mt-1 opacity-70">
                  {format(new Date(msg.timestamp), 'HH:mm')}
                </p>
              </div>
            </div>
          ))
        )}
        
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}
      </div>
      
      {/* Input Area */}
      <div className="bg-white border-t border-gray-300 p-4 space-y-4">
        {/* Job Description Input */}
        {showJDInput && (
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Job Title (optional)"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <textarea
              placeholder="Paste job description here..."
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 h-32"
            />
            <button
              onClick={() => setShowJDInput(false)}
              className="text-sm text-gray-600 hover:text-gray-800"
            >
              ✕ Cancel
            </button>
          </div>
        )}
        
        {/* Message Input */}
        <div className="flex gap-2">
          <div className="flex-1 flex gap-2">
            <input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              disabled={isLoading || showJDInput}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={handleSendMessage}
              disabled={isLoading || (!input.trim() && !jobDescription.trim())}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition disabled:opacity-50"
            >
              {isLoading ? '...' : 'Send'}
            </button>
          </div>
          
          <button
            onClick={() => setShowJDInput(!showJDInput)}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition"
            title="Add Job Description"
          >
            📄
          </button>
        </div>
      </div>
    </div>
  );
}
