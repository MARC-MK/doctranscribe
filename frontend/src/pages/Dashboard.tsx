import React from "react";
import { FileText, BarChart, FileSpreadsheet, Upload, Zap } from "lucide-react";
import { Link } from "react-router-dom";

const Dashboard = () => {
  return (
    <div className="space-y-10">
      {/* Hero section */}
      <section className="bg-gradient-to-br from-background to-background-light rounded-xl p-8 shadow-lg">
        <div className="max-w-3xl">
          <h1 className="text-4xl font-bold mb-4">Transform Handwritten Survey Data into Digital Insights</h1>
          <p className="text-xl text-gray-300 mb-8">
            Upload handwritten survey PDFs and convert them into structured, analyzable Excel spreadsheets 
            within minutes using advanced AI technology.
          </p>
          <div className="flex gap-4">
            <Link 
              to="/upload" 
              className="px-6 py-3 bg-primary text-white rounded-lg font-medium hover:bg-primary/90 transition flex items-center gap-2"
            >
              <Upload size={18} /> Upload Surveys
            </Link>
            <Link 
              to="/help" 
              className="px-6 py-3 bg-background border border-gray-700 rounded-lg font-medium hover:bg-background/80 transition flex items-center gap-2"
            >
              <FileText size={18} /> Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Features section */}
      <section>
        <h2 className="text-2xl font-semibold mb-6">How It Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard 
            icon={<Upload className="text-blue-400" />} 
            title="1. Upload Surveys" 
            description="Upload up to 100 handwritten survey PDFs in a single batch."
          />
          <FeatureCard 
            icon={<Zap className="text-yellow-400" />} 
            title="2. AI Processing" 
            description="Our AI reads and interprets handwritten responses, even handling messy handwriting."
          />
          <FeatureCard 
            icon={<FileSpreadsheet className="text-green-400" />} 
            title="3. Get Results" 
            description="Download organized Excel spreadsheets with all your survey data ready for analysis."
          />
        </div>
      </section>

      {/* Recent surveys section */}
      <section>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold">Recent Survey Batches</h2>
          <Link to="/results" className="text-primary hover:underline flex items-center gap-1">
            View All <BarChart size={16} />
          </Link>
        </div>
        
        <div className="bg-background rounded-lg border border-background-light overflow-hidden">
          {recentBatches.length > 0 ? (
            <table className="w-full text-sm">
              <thead className="bg-background-light">
                <tr>
                  <th className="py-3 px-4 text-left">Date</th>
                  <th className="py-3 px-4 text-left">Survey Name</th>
                  <th className="py-3 px-4 text-left">Documents</th>
                  <th className="py-3 px-4 text-left">Status</th>
                  <th className="py-3 px-4 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentBatches.map((batch, index) => (
                  <tr key={index} className="border-t border-background-light hover:bg-background/50 transition">
                    <td className="py-3 px-4">{batch.date}</td>
                    <td className="py-3 px-4">{batch.name}</td>
                    <td className="py-3 px-4">{batch.documents}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        batch.status === 'Completed' ? 'bg-green-400/10 text-green-400' : 
                        batch.status === 'Processing' ? 'bg-blue-400/10 text-blue-400' : 
                        'bg-yellow-400/10 text-yellow-400'
                      }`}>
                        {batch.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <Link to={`/results/${batch.id}`} className="text-primary hover:underline">
                        View Results
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-10 text-center text-gray-400">
              <FileText className="h-10 w-10 mx-auto mb-3 opacity-40" />
              <p>No survey batches processed yet</p>
              <Link to="/upload" className="inline-block mt-3 text-primary hover:underline">
                Upload your first survey batch
              </Link>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

const FeatureCard = ({ icon, title, description }) => (
  <div className="bg-background rounded-lg p-6 border border-background-light hover:border-primary/30 transition">
    <div className="h-10 w-10 mb-4 flex items-center justify-center rounded-full bg-background-light">
      {icon}
    </div>
    <h3 className="text-lg font-medium mb-2">{title}</h3>
    <p className="text-gray-400">{description}</p>
  </div>
);

// Sample data for recent batches
const recentBatches = [
  { id: 1, date: "May 12, 2023", name: "Customer Satisfaction Q2", documents: 45, status: "Completed" },
  { id: 2, date: "May 10, 2023", name: "Employee Feedback 2023", documents: 78, status: "Processing" },
  { id: 3, date: "May 5, 2023", name: "Product Survey March", documents: 32, status: "Completed" }
];

export default Dashboard; 