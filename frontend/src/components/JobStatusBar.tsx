import React, { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { motion } from "framer-motion";

interface JobStatusBarProps {
  jobId: string;
}

interface JobStatus {
  status: string;
  progress: number;
  message?: string;
}

export const JobStatusBar: React.FC<JobStatusBarProps> = ({ jobId }) => {
  const [status, setStatus] = useState<JobStatus>({
    status: "queued",
    progress: 0,
  });

  useEffect(() => {
    const wsUrl = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/results/ws/jobs/${jobId}`;
    const socket = new WebSocket(wsUrl);
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus(data);
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };
    return () => {
      socket.close();
    };
  }, [jobId]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-4"
    >
      <div className="flex items-center gap-4">
        <span className="font-medium text-base">
          {status.status === "done"
            ? "✅ Complete"
            : status.status === "error"
              ? "❌ Error"
              : status.status === "processing"
                ? `Processing (${status.progress}%)`
                : "Queued"}
        </span>
        <div className="flex-1">
          <Progress value={status.progress} max={100} className="h-2" />
        </div>
      </div>
      {status.message && (
        <div className="text-muted-foreground text-xs mt-1">
          {status.message}
        </div>
      )}
    </motion.div>
  );
};

export default JobStatusBar;
