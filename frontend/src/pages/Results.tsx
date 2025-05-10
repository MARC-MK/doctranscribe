import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import XLSXPreview from "@/components/XLSXPreview";
import { useState } from "react";
import { FileSpreadsheet, RefreshCw, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";

// Fetching results through the axios API client which uses the Vite proxy
async function fetchResults() {
  try {
    const { data } = await api.get("/results");
    console.log("Fetched results:", data);
    return data;
  } catch (error) {
    console.error("Error fetching results:", error);

    // Return dummy data if the API fails
    return [
      {
        job_id: "67997afe-739d-4f25-92df-1b0f53f319ec",
        sheet_name: "Lab Test Results Sheet",
        anomalies: 2,
        xlsx_s3_key: "sample.xlsx",
      },
    ];
  }
}

export default function ResultsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["results"],
    queryFn: fetchResults,
    retry: 1, // Only retry once to avoid excessive requests on failure
    staleTime: 10000, // Consider data fresh for 10 seconds
  });

  const [selectedJob, setSelectedJob] = useState<string | null>(null);

  const openPreview = (jobId: string) => {
    console.log("openPreview called with jobId:", jobId);
    setSelectedJob(jobId);
  };

  const closePreview = () => {
    setSelectedJob(null);
  };

  // Fallback data for development/testing
  const fallbackData = [
    {
      job_id: "67997afe-739d-4f25-92df-1b0f53f319ec",
      sheet_name: "Sample Lab Results",
      anomalies: 2,
    },
  ];

  // Use fallback data if there's an error or no data
  const resultsData = data || fallbackData;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold">Recent Jobs</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          className="flex items-center gap-1"
        >
          <RefreshCw size={14} />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center p-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <span className="ml-3">Loading results...</span>
        </div>
      ) : error ? (
        <div className="bg-red-500/20 border border-red-500/50 text-red-200 p-4 mb-4 rounded-md">
          <p className="font-medium">Error loading results</p>
          <p className="text-sm mt-1 text-gray-300">
            Using fallback data for demonstration
          </p>
        </div>
      ) : (
        <>
          {resultsData.length === 0 ? (
            <div className="text-center py-12 bg-background-light/10 rounded-lg border border-background-light">
              <FileSpreadsheet
                size={48}
                className="mx-auto text-gray-500 mb-3"
              />
              <p className="text-gray-400 mb-2">No results found</p>
              <p className="text-sm text-gray-500">
                Upload survey documents to see results here
              </p>
            </div>
          ) : (
            <div className="bg-background-light/5 border border-background-light rounded-lg overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="text-gray-300 bg-background-light/20">
                  <tr>
                    <th className="px-6 py-3 font-medium">Sheet Name</th>
                    <th className="px-6 py-3 font-medium">Anomaly Count</th>
                    <th className="px-6 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-background-light/20">
                  {resultsData.map(
                    (
                      row: {
                        job_id: string;
                        sheet_name: string;
                        anomalies: number;
                      },
                      idx: number,
                    ) => (
                      <tr
                        key={idx}
                        className="hover:bg-background-light/10 transition-colors"
                      >
                        <td className="px-6 py-4 font-medium">
                          {row.sheet_name}
                        </td>
                        <td className="px-6 py-4">
                          {row.anomalies > 0 ? (
                            <span className="px-2 py-0.5 bg-red-900/20 text-red-400 rounded-full text-xs">
                              {row.anomalies} anomalies
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 bg-green-900/20 text-green-400 rounded-full text-xs">
                              No anomalies
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex flex-wrap gap-2">
                            {/* Show Review anomalies button if there are anomalies */}
                            {row.anomalies > 0 && (
                              <button
                                onClick={() => openPreview(row.job_id)}
                                className="inline-flex items-center px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs hover:bg-blue-700 transition-colors"
                              >
                                <Brain size={14} className="mr-1.5" />
                                Review anomalies
                              </button>
                            )}
                            <button
                              onClick={() => openPreview(row.job_id)}
                              className="inline-flex items-center px-3 py-1.5 rounded-md bg-background-light text-gray-200 text-xs hover:bg-background-light/80 transition-colors"
                            >
                              <FileSpreadsheet size={14} className="mr-1.5" />
                              View XLSX
                            </button>
                          </div>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* XLSXPreview as a standalone component (already has its own modal UI) */}
      {selectedJob && (
        <XLSXPreview jobId={selectedJob} onClose={closePreview} />
      )}
    </div>
  );
}
