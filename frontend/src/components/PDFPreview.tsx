import React, { useState, useEffect } from "react";
import { X, FileWarning, RefreshCw } from "lucide-react";

interface PDFPreviewProps {
  file: File | null;
  onClose: () => void;
}

const PDFPreview: React.FC<PDFPreviewProps> = ({ file, onClose }) => {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  // Create object URL for the file when it changes
  useEffect(() => {
    if (file) {
      try {
        setIsLoading(true);
        setErrorMessage(null);
        const url = URL.createObjectURL(file);
        setObjectUrl(url);

        // Simulate a delay to show loading state
        const timer = setTimeout(() => {
          setIsLoading(false);
        }, 1000);

        return () => {
          URL.revokeObjectURL(url);
          clearTimeout(timer);
        };
      } catch (error) {
        console.error("Error creating object URL:", error);
        setErrorMessage("Could not prepare the PDF for viewing.");
        setIsLoading(false);
      }
    }
  }, [file]);

  const retryLoading = () => {
    setIsRetrying(true);
    setErrorMessage(null);

    if (file) {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        setObjectUrl(null);
      }

      setTimeout(() => {
        try {
          const newUrl = URL.createObjectURL(file);
          setObjectUrl(newUrl);
          setIsRetrying(false);
          setIsLoading(false);
        } catch (error) {
          console.error("Error retrying:", error);
          setErrorMessage(
            "Failed to reload the PDF. It may be corrupted or password-protected.",
          );
          setIsRetrying(false);
          setIsLoading(false);
        }
      }, 800);
    } else {
      setIsRetrying(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="relative bg-white text-gray-800 border border-gray-200 rounded-lg w-[95vw] h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-3 border-b border-gray-200 bg-gray-50">
          <h3 className="font-medium flex items-center gap-2 text-gray-700">
            <span>PDF Preview:</span>
            <span className="text-gray-500 text-sm font-normal truncate max-w-md">
              {file?.name}
            </span>
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 p-1 rounded"
            title="Close preview"
          >
            <X size={20} />
          </button>
        </div>

        {/* PDF Content */}
        <div className="flex-1 flex bg-gray-100 w-full h-full">
          {isLoading ? (
            <div className="flex items-center justify-center w-full h-full">
              <div className="inline-block p-8 bg-white rounded-lg shadow-lg">
                <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4 mx-auto"></div>
                <div className="text-gray-600">Loading PDF...</div>
              </div>
            </div>
          ) : errorMessage ? (
            <div className="flex items-center justify-center w-full h-full">
              <div className="text-center p-10 max-w-md bg-white rounded-lg border border-red-200 shadow-lg">
                <FileWarning size={48} className="mx-auto text-red-500 mb-4" />
                <h3 className="text-xl font-semibold text-gray-800 mb-3">
                  PDF Error
                </h3>
                <p className="text-gray-600 mb-5">{errorMessage}</p>
                <div className="flex flex-col sm:flex-row justify-center gap-3">
                  <button
                    onClick={retryLoading}
                    disabled={isRetrying}
                    className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-50 hover:bg-blue-100 rounded-md transition-colors text-blue-600 border border-blue-200"
                  >
                    {isRetrying ? (
                      <>
                        <RefreshCw size={16} className="animate-spin" />
                        Retrying...
                      </>
                    ) : (
                      <>
                        <RefreshCw size={16} />
                        Retry
                      </>
                    )}
                  </button>
                  <button
                    onClick={onClose}
                    className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-gray-700"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          ) : objectUrl ? (
            <iframe
              src={objectUrl}
              title="PDF Preview"
              className="w-full h-full border-0"
              onError={() =>
                setErrorMessage(
                  "This PDF could not be loaded. It may be corrupted or password-protected.",
                )
              }
              style={{ minHeight: "100%", minWidth: "100%" }}
            />
          ) : (
            <div className="flex items-center justify-center w-full h-full text-gray-600">
              No PDF file selected
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PDFPreview;
