import { Route, Routes, Navigate } from "react-router-dom";
import NavBar from "@/components/NavBar";
import UploadPage from "@/pages/Upload";
import ResultsPage from "@/pages/Results";

function App() {
  return (
    <div className="min-h-screen bg-background-light text-white font-sans">
      <NavBar />
      <div className="p-6 max-w-5xl mx-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/results" element={<ResultsPage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App; 