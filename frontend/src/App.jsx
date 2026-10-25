import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider, useAuth } from './context/AuthContext';
import Chatbot from './components/Chatbot';

import Dashboard from './pages/Dashboard';
import BusinessProfile from './pages/BusinessProfile';
import RecommendationsList from './pages/RecommendationsList';
import DocumentVerification from './pages/DocumentVerification';
import Analytics from './pages/Analytics';
import AdminPanel from './pages/AdminPanel';

function AppContent() {
  const { profile } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [recsVersion, setRecsVersion] = useState(0);

  const refreshRecs = () => setRecsVersion(v => v + 1);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="flex-1 overflow-y-auto bg-[#f8fafc]">
          <div className="mx-auto max-w-6xl px-6 py-6">
            <div className={activeTab === 'dashboard' ? '' : 'hidden'}><Dashboard setActiveTab={setActiveTab} setSelectedScheme={setSelectedScheme} profile={profile} /></div>
            <div className={activeTab === 'profile' ? '' : 'hidden'}><BusinessProfile setActiveTab={setActiveTab} refreshRecs={refreshRecs} /></div>
            <div className={activeTab === 'recommendations' ? '' : 'hidden'}><RecommendationsList selectedScheme={selectedScheme} setSelectedScheme={setSelectedScheme} setActiveTab={setActiveTab} key={recsVersion} /></div>
            <div className={activeTab === 'verification' ? '' : 'hidden'}><DocumentVerification /></div>
            <div className={activeTab === 'analytics' ? '' : 'hidden'}><Analytics /></div>
            <div className={activeTab === 'admin' ? '' : 'hidden'}><AdminPanel /></div>
          </div>
        </main>
      </div>
      <Chatbot />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <AppContent />
      </ProtectedRoute>
    </AuthProvider>
  );
}

export default App;
