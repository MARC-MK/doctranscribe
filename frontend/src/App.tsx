import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import NavBar from "@/components/NavBar";
import Upload from "@/pages/Upload";
import DocumentView from "@/pages/DocumentView";
import Results from "@/pages/Results";
import Dashboard from "@/pages/Dashboard";
import Settings from "@/pages/Settings";
import Help from "@/pages/Help";
import Assistant from "@/pages/Assistant";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import { Toaster } from "sonner";
import { useAuth } from "@/lib/auth";

// Protected route component
function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="h-10 w-10 border-4 border-primary/30 border-t-primary rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login but save the current location they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

function App() {
  return (
    <div className="min-h-screen bg-background-light text-white font-sans flex flex-col">
      <NavBar />
      <main className="flex-1 py-8">
        <div className="container mx-auto px-4">
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/help" element={<Help />} />
            
            {/* Protected routes */}
            <Route path="/" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/upload" element={
              <ProtectedRoute>
                <Upload />
              </ProtectedRoute>
            } />
            <Route path="/document/:documentId" element={
              <ProtectedRoute>
                <DocumentView />
              </ProtectedRoute>
            } />
            <Route path="/results" element={
              <ProtectedRoute>
                <Results />
              </ProtectedRoute>
            } />
            <Route path="/settings" element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            } />
            <Route path="/assistant" element={
              <ProtectedRoute>
                <Assistant />
              </ProtectedRoute>
            } />
          </Routes>
        </div>
      </main>
      <footer className="bg-background border-t border-background-light py-4 text-center text-gray-400 text-sm">
        <p>DocTranscribe &copy; {new Date().getFullYear()} - Convert handwritten surveys to digital data</p>
      </footer>
      <Toaster position="top-right" />
    </div>
  );
}

export default App; 