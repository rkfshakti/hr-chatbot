import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Chat } from '../components/Chat';
import { Results } from '../components/Results';
import { useAuthStore } from '../store';

export function Dashboard() {
  const [activeTab, setActiveTab] = useState('chat');
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  
  const handleLogout = () => {
    logout();
    navigate('/login');
  };
  
  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Navigation Bar */}
      <nav className="bg-gray-800 text-white p-4 shadow-lg">
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-bold">HR Chatbot Dashboard</h1>
          <button
            onClick={handleLogout}
            className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg transition"
          >
            Logout
          </button>
        </div>
      </nav>
      
      {/* Tabs */}
      <div className="bg-white border-b border-gray-300">
        <div className="flex">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-6 py-3 font-medium transition ${
              activeTab === 'chat'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            💬 Chat
          </button>
          <button
            onClick={() => setActiveTab('results')}
            className={`px-6 py-3 font-medium transition ${
              activeTab === 'results'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📊 Results
          </button>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' ? <Chat /> : <Results />}
      </div>
    </div>
  );
}
