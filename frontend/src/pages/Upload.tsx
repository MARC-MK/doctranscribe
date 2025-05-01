import { useState } from "react";
import DropZone from "@/components/DropZone";

export default function UploadPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  return (
    <div className="space-y-8">
      <DropZone
        onSuccess={(data) => {
          setJobs((prev) => [data, ...prev]);
        }}
      />

      <h2 className="text-xl font-semibold">Results</h2>
      <table className="w-full text-sm text-left">
        <thead className="text-gray-400 border-b border-background-light">
          <tr>
            <th className="py-2">Sheet Name</th>
            <th>Anomaly Count</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job, idx) => (
            <tr key={idx} className="border-b border-background-light hover:bg-background-light/30">
              <td className="py-2">{job.sheet_name}</td>
              <td>{job.anomalies}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
} 