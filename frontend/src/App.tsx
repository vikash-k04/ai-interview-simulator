import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { ResumesPage } from './pages/ResumesPage';
import { InterviewSetupPage } from './pages/InterviewSetupPage';
import { BlueprintPreviewPage } from './pages/BlueprintPreviewPage';
import { InterviewRoomPage } from './pages/InterviewRoomPage';
import { ReportPage } from './pages/ReportPage';
import { PracticePage } from './pages/PracticePage';

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
          <Navbar />
          <main className="flex-1">
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />

              {/* Protected Candidate Routes */}
              <Route element={<ProtectedRoute />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/resumes" element={<ResumesPage />} />
                <Route path="/setup" element={<InterviewSetupPage />} />
                <Route path="/blueprint/:id" element={<BlueprintPreviewPage />} />
                <Route path="/interview/:id" element={<InterviewRoomPage />} />
                <Route path="/reports/:id" element={<ReportPage />} />
                <Route path="/practice" element={<PracticePage />} />
              </Route>

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
