import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import * as XLSX from "xlsx";
import { api } from "@/lib/api";
import { Download, FileSpreadsheet, X } from "lucide-react";

interface XLSXPreviewProps {
  jobId: string;
  onClose?: () => void;
}

interface XLSXRow {
  [key: string]: string | number | null;
}

export const XLSXPreview: React.FC<XLSXPreviewProps> = ({ jobId, onClose }) => {
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [rows, setRows] = useState<XLSXRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUrlAndPreview = async () => {
      setLoading(true);
      setError(null);
      try {
        // Get the XLSX data through the API client instead of fetch
        const response = await api.get(`/results/${jobId}/xlsx`, { responseType: 'arraybuffer' });
        
        // Set download URL to be our proxied endpoint
        setDownloadUrl(`/api/results/${jobId}/xlsx?download=true`);
        
        // Process the XLSX data
        const ab = response.data;
        const workbook = XLSX.read(ab, { type: "array" });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json<XLSXRow>(sheet, { header: 1 });
        
        if (json.length > 0) {
          setColumns(json[0] as string[]);
          setRows(
            json.slice(1, 11).map((row) => {
              const obj: XLSXRow = {};
              (json[0] as string[]).forEach((col, i) => {
                obj[col] = row[i] ?? null;
              });
              return obj;
            })
          );
        }
      } catch (e: any) {
        console.error("XLSX preview error:", e);
        setError(e.message || "Could not fetch XLSX file");
      } finally {
        setLoading(false);
      }
    };
    fetchUrlAndPreview();
  }, [jobId]);

  // Determine if a cell value is an anomaly (for highlighting)
  const isAnomaly = (colName: string, value: string | number | null): boolean => {
    return colName === "Anomaly" && value === "Yes";
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
        className="relative bg-white text-gray-800 border border-gray-200 rounded-lg w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
          <h2 className="text-xl font-semibold flex items-center gap-2 text-gray-700">
            <FileSpreadsheet className="text-blue-600" size={22} />
            XLSX Preview
          </h2>
          <div className="flex items-center gap-3">
            {downloadUrl && (
              <Button 
                asChild 
                variant="outline" 
                className="flex items-center gap-2 text-sm hover:bg-blue-50 text-blue-600 border-blue-200"
              >
                <a href={downloadUrl} download target="_blank" rel="noopener noreferrer">
                  <Download size={16} /> Download XLSX
                </a>
              </Button>
            )}
            {onClose && (
              <button 
                onClick={onClose}
                className="text-gray-500 hover:text-gray-700 p-1 rounded"
                title="Close preview"
              >
                <X size={20} />
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-5 bg-white">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <div className="animate-pulse flex flex-col items-center">
                <FileSpreadsheet className="text-blue-500 mb-3" size={40} />
                <p className="text-gray-500">Loading XLSX data...</p>
              </div>
            </div>
          )}
          
          {error && (
            <div className="text-center p-8 bg-red-50 rounded-lg border border-red-200">
              <p className="text-red-600 mb-2 font-medium">Error loading XLSX file</p>
              <p className="text-sm text-gray-600">{error}</p>
            </div>
          )}
          
          {!loading && !error && rows.length > 0 && (
            <div className="rounded-lg shadow-md border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-gray-700">
                  <thead>
                    <tr className="bg-gray-100 border-b border-gray-200">
                      {columns.map((col) => (
                        <th 
                          key={col} 
                          className="px-6 py-3 text-left font-semibold text-gray-700 border-r border-gray-200 last:border-r-0"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr 
                        key={i} 
                        className={`${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition-colors duration-150`}
                      >
                        {columns.map((col) => {
                          const cellValue = row[col] ?? "";
                          const isAnomalyCell = isAnomaly(col, cellValue);
                          
                          return (
                            <td 
                              key={col} 
                              className={`px-6 py-3 border-b border-gray-200 border-r border-gray-200 last:border-r-0 ${
                                col === 'Value' ? 'font-mono' : ''
                              }`}
                            >
                              {isAnomalyCell ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                                  {cellValue}
                                </span>
                              ) : cellValue}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          
          {!loading && !error && rows.length === 0 && (
            <div className="text-center p-8 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-gray-500">No data found in XLSX file.</p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default XLSXPreview; 