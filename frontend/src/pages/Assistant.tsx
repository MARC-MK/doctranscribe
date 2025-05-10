import React, { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { Brain } from "lucide-react";
import AssistantDrawer from "@/components/AssistantDrawer";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const AssistantPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const jobId = searchParams.get("job_id");

  // If no job_id is specified, fetch the first job with anomalies
  const { data: completedJobs, isLoading } = useQuery({
    queryKey: ["completedJobsWithAnomalies"],
    queryFn: async () => {
      if (jobId) return null; // Skip if we already have a jobId
      try {
        const response = await api.get("/results");
        // Filter for jobs with anomalies
        return response.data.filter((job: unknown) => job.anomalies > 0);
      } catch (error) {
        console.error("Error fetching jobs with anomalies:", error);
        return [];
      }
    },
    enabled: !jobId, // Only run if no jobId is specified
  });

  // Redirect to the first job with anomalies if none is specified
  useEffect(() => {
    if (!jobId && completedJobs?.length > 0) {
      navigate(`/assistant?job_id=${completedJobs[0].job_id}`);
    }
  }, [jobId, completedJobs, navigate]);

  // Handle closing the assistant drawer
  const handleCloseDrawer = () => {
    navigate("/results");
  };

  // If we're still loading, or no jobId and no completedJobs, show a loading state
  if (
    (isLoading && !jobId) ||
    (!jobId && (!completedJobs || completedJobs.length === 0))
  ) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-gray-400">
        <Brain size={48} className="mb-4 text-primary/50" />
        <p className="text-lg">
          {isLoading
            ? "Loading Anomaly Assistant..."
            : "No anomalies found. Upload documents to get started."}
        </p>
      </div>
    );
  }

  // Once we have a jobId, show the assistant drawer
  return jobId ? (
    <AssistantDrawer jobId={jobId} onClose={handleCloseDrawer} />
  ) : null;
};

export default AssistantPage;
