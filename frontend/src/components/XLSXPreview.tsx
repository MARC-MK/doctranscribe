import React, { useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import * as XLSX from "xlsx";
import { api } from "@/lib/api";
import {
  Download,
  FileSpreadsheet,
  X,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";

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
  const [retryCount, setRetryCount] = useState(0);

  // Helper function to classify columns for styling
  const getColumnType = useCallback(
    (colName: string): "metadata" | "handwritten" | "normal" => {
      // These columns are likely metadata - adjust based on your data model
      const metadataColumns = ["Sample", "Units", "Reference Range"];
      const handwrittenColumns = ["Value", "Measurement"];

      if (metadataColumns.includes(colName)) return "metadata";
      if (handwrittenColumns.includes(colName)) return "handwritten";
      return "normal";
    },
    [],
  );

  // Helper function to determine if a cell value is an anomaly
  const isAnomaly = useCallback(
    (colName: string, value: string | number | null): boolean => {
      // Consider a value anomalous if:
      // 1. It's explicitly marked as an anomaly
      // 2. It's a Value column and out of reference range if we can determine that

      // Direct anomaly marking
      if (colName === "Anomaly" && value === "Yes") {
        return true;
      }

      return false;
    },
    [],
  );

  const handleRetry = () => {
    setRetryCount((prev) => prev + 1);
  };

  useEffect(() => {
    const fetchUrlAndPreview = async () => {
      if (!jobId) return;

      setLoading(true);
      setError(null);
      try {
        console.log(`Fetching XLSX for job ${jobId}`);
        // Get the XLSX data through the API client instead of fetch
        const response = await api.get(`/results/${jobId}/xlsx`, {
          responseType: "arraybuffer",
          // Increase timeout for large files
          timeout: 30000,
        });

        // Set download URL to be our proxied endpoint
        setDownloadUrl(`/api/results/${jobId}/xlsx?download=true`);

        // Process the XLSX data
        const ab = response.data;
        const workbook = XLSX.read(ab, { type: "array" });

        if (!workbook.SheetNames || workbook.SheetNames.length === 0) {
          throw new Error("No sheets found in XLSX file");
        }

        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json<XLSXRow>(sheet, { header: 1 });

        if (json.length === 0) {
          throw new Error("No data found in the XLSX file");
        }

        if (json.length > 0) {
          setColumns(json[0] as string[]);

          // Get all rows, not just the first 10
          const dataRows = json.slice(1).map((row) => {
            const obj: XLSXRow = {};
            (json[0] as string[]).forEach((col, i) => {
              obj[col] = row[i] ?? null;
            });
            return obj;
          });

          setRows(dataRows);
          console.log(`Loaded ${dataRows.length} rows from XLSX`);
        }
      } catch (e: unknown) {
        console.error("XLSX preview error:", e);
        setError(e instanceof Error ? e.message : "Could not fetch XLSX file");
      } finally {
        setLoading(false);
      }
    };

    fetchUrlAndPreview();
  }, [jobId, retryCount]);

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2 }}
        className="relative bg-white text-gray-800 border border-gray-200 rounded-lg w-full max-w-[95vw] max-h-[90vh] flex flex-col overflow-hidden shadow-2xl"
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
                <a
                  href={downloadUrl}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Download size={16} /> Download XLSX
                </a>
              </Button>
            )}
            {error && (
              <Button
                variant="outline"
                className="flex items-center gap-2 text-sm hover:bg-yellow-50 text-yellow-600 border-yellow-200"
                onClick={handleRetry}
              >
                <RefreshCw size={16} />
                Retry
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
        <div className="flex-1 overflow-auto p-5 bg-gray-50">
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
              <AlertTriangle className="text-red-500 mx-auto mb-3" size={32} />
              <p className="text-red-600 mb-2 font-medium">
                Error loading XLSX file
              </p>
              <p className="text-sm text-gray-600 mb-4">{error}</p>
              <Button
                variant="outline"
                className="text-red-600 border-red-200 hover:bg-red-100"
                onClick={handleRetry}
              >
                <RefreshCw size={16} className="mr-2" /> Try Again
              </Button>
            </div>
          )}

          {!loading && !error && rows.length > 0 && (
            <div className="overflow-hidden shadow-md rounded-lg bg-white border border-gray-300">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-gray-700 border-collapse">
                  <thead>
                    <tr className="bg-blue-50 border-b border-gray-300">
                      {columns.map((col) => {
                        const colType = getColumnType(col);
                        return (
                          <th
                            key={col}
                            className={`
                              px-4 py-2 text-left font-semibold text-blue-800 border border-gray-300
                              ${colType === "metadata" ? "bg-gray-100" : ""}
                              ${colType === "handwritten" ? "bg-blue-50" : ""}
                            `}
                          >
                            {col}
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, i) => (
                      <tr
                        key={i}
                        className={`${i % 2 === 0 ? "bg-white" : "bg-gray-50"} hover:bg-blue-50 transition-colors duration-150`}
                      >
                        {columns.map((col) => {
                          const cellValue = row[col] ?? "";
                          const isAnomalyCell = isAnomaly(col, cellValue);
                          const colType = getColumnType(col);

                          return (
                            <td
                              key={col}
                              className={`
                                px-4 py-2 border border-gray-300
                                ${isAnomalyCell ? "bg-red-50" : ""}
                                ${colType === "handwritten" ? "font-mono text-blue-700 font-medium" : ""}
                                ${colType === "metadata" ? "text-gray-600" : ""}
                              `}
                            >
                              {isAnomalyCell ? (
                                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                                  {cellValue}
                                </span>
                              ) : (
                                <span>{cellValue}</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Footer with summary */}
              <div className="bg-gray-50 border-t border-gray-300 px-4 py-2 text-xs text-gray-500">
                Showing {rows.length} rows
              </div>
            </div>
          )}

          {!loading && !error && rows.length === 0 && (
            <div className="text-center p-8 bg-gray-50 rounded-lg border border-gray-200">
              <FileSpreadsheet
                className="text-gray-400 mx-auto mb-3"
                size={32}
              />
              <p className="text-gray-500">No data found in XLSX file.</p>
              <p className="text-sm text-gray-400 mt-2">
                The file might be empty or in an unexpected format.
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default XLSXPreview;
