import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Brain } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

interface AssistantNavLinkProps {
  className?: string;
}

// Fetch data to determine if there are any completed jobs with anomalies
const useCompletedJobs = () => {
  return useQuery({
    queryKey: ['completedJobs'],
    queryFn: async () => {
      try {
        const response = await api.get('/results');
        // Filter for completed jobs with anomalies
        return response.data.filter((job: any) => job.anomalies > 0);
      } catch (error) {
        console.error('Error fetching completed jobs:', error);
        return [];
      }
    },
    staleTime: 30000, // Consider data fresh for 30 seconds
  });
};

const AssistantNavLink: React.FC<AssistantNavLinkProps> = ({ className }) => {
  const { data: completedJobs, isLoading } = useCompletedJobs();
  const [anomalyCount, setAnomalyCount] = useState(0);
  
  useEffect(() => {
    if (completedJobs?.length) {
      // Calculate total anomalies across all jobs
      const totalAnomalies = completedJobs.reduce(
        (sum: number, job: any) => sum + (job.anomalies || 0), 
        0
      );
      setAnomalyCount(totalAnomalies);
    }
  }, [completedJobs]);

  const isDisabled = isLoading || anomalyCount === 0;

  // Generic link class from NavBar
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-4 py-2 rounded-md transition-colors duration-200 ${
      isActive ? "bg-primary/10 text-primary font-medium" : "text-gray-300 hover:bg-background hover:text-white"
    } ${isDisabled ? "opacity-50 cursor-not-allowed" : ""}`;

  return (
    <NavLink 
      to="/assistant" 
      className={linkClass}
      onClick={(e) => isDisabled && e.preventDefault()}
      title={isDisabled ? "No anomalies to review" : "Anomaly Assistant"}
    >
      <Brain size={18} />
      Assistant
      {anomalyCount > 0 && (
        <span className="ml-1 px-1.5 py-0.5 text-xs bg-red-500 text-white rounded-full">
          {anomalyCount}
        </span>
      )}
    </NavLink>
  );
};

export default AssistantNavLink; 