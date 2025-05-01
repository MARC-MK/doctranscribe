import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

async function fetchResults() {
  const { data } = await api.get("/results");
  return data;
}

export default function ResultsPage() {
  const { data, isLoading, error } = useQuery({ queryKey: ["results"], queryFn: fetchResults });

  if (isLoading) return <p>Loading…</p>;
  if (error) return <p className="text-red-500">Error loading results</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Recent Jobs</h2>
      <table className="w-full text-sm text-left">
        <thead className="text-gray-400 border-b border-background-light">
          <tr>
            <th className="py-2">Sheet Name</th>
            <th>Anomaly Count</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((row: any, idx: number) => (
            <tr key={idx} className="border-b border-background-light hover:bg-background-light/30">
              <td className="py-2">{row.sheet_name}</td>
              <td>{row.anomalies}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
} 