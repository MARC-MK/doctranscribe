import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { api } from "@/lib/api";
import { UploadCloud, Loader2, FileText, X, AlertCircle, Eye } from "lucide-react";
import PDFPreview from "./PDFPreview";

interface Props {
  onSuccess: (data: any) => void;
}

export default function DropZone({ onSuccess }: Props) {
  const [isUploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<File | null>(null);

  const removeFile = (fileToRemove: File) => {
    setSelectedFiles(selectedFiles.filter(file => file !== fileToRemove));
  };

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return;
    
    // Add files to the queue
    setSelectedFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const startUpload = async () => {
    if (!selectedFiles.length) return;
    
    setError(null);
    setUploading(true);
    setUploadProgress(0);
    
    try {
      // First check if backend is reachable
      try {
        const testResponse = await api.get("/extract/test");
        console.log("Test endpoint response:", testResponse.data);
      } catch (testErr) {
        console.error("Backend test failed:", testErr);
        throw new Error(`Backend connectivity test failed: ${testErr instanceof Error ? testErr.message : 'Unknown error'}`);
      }
      
      // For demonstration, we'll simulate a batch upload with progress
      const totalFiles = selectedFiles.length;
      
      // This would be a real batch upload in production
      // const form = new FormData();
      // selectedFiles.forEach((file, index) => {
      //   form.append(`files[${index}]`, file);
      // });
      
      // Simulate file processing with progress
      for (let i = 0; i < totalFiles; i++) {
        // In a real app, you'd upload all files at once, not one by one
        const progressPercent = Math.round(((i + 1) / totalFiles) * 100);
        setUploadProgress(progressPercent);
        
        // Simulate processing delay for demo
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      // For now, just use the temporary endpoint and simulate success
      const response = await api.get("/temp-upload");
      console.log("Upload simulation response:", response.data);
      
      // Create a fake batch result with the uploaded file count
      const resultData = {
        sheet_name: "Survey Batch " + new Date().toLocaleDateString(),
        anomalies: Math.floor(Math.random() * 5), // Random number of anomalies for demo
        job_id: "batch-" + Date.now(),
        documents: selectedFiles.length
      };
      
      // Clear the file list on success
      setSelectedFiles([]);
      
      // Call the success handler
      onSuccess(resultData);
    } catch (err) {
      console.error("Upload error:", err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop, 
    accept: { "application/pdf": [] },
    disabled: isUploading
  });

  const openPreview = (file: File) => {
    setPreviewFile(file);
  };

  const closePreview = () => {
    setPreviewFile(null);
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 
          ${isDragActive ? 'border-primary bg-primary/5' : 'border-gray-600'} 
          ${isUploading ? 'bg-gray-900/50 cursor-not-allowed' : 'bg-gray-900/20 cursor-pointer'}`}
      >
        <input {...getInputProps()} disabled={isUploading} />
        <UploadCloud size={48} className="mx-auto text-primary mb-4" />
        <h3 className="text-xl font-semibold mb-2">Batch Survey Upload</h3>
        <p className="text-gray-400 mb-4">
          {isDragActive ? 
            "Drop the survey PDFs here..." : 
            "Drag and drop survey PDFs here, or click to select files"
          }
        </p>
        <p className="text-sm text-gray-500">
          Upload up to 100 survey PDFs at once. Each file should be less than 10MB.
        </p>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-900/20 border border-red-900 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-medium text-red-400 mb-1">Upload Failed</h4>
            <p className="text-sm text-gray-300">{error}</p>
          </div>
        </div>
      )}

      {/* Selected files list */}
      {selectedFiles.length > 0 && (
        <div className="bg-background border border-background-light rounded-lg overflow-hidden">
          <div className="p-4 border-b border-background-light flex justify-between items-center">
            <h3 className="font-medium">
              {selectedFiles.length} {selectedFiles.length === 1 ? 'File' : 'Files'} Selected
            </h3>
            <button
              onClick={startUpload}
              disabled={isUploading}
              className={`px-4 py-1.5 rounded-md flex items-center gap-1 ${
                isUploading 
                  ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-primary text-white hover:bg-primary/90'
              }`}
            >
              {isUploading ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Processing...
                </>
              ) : (
                <>
                  <UploadCloud size={16} /> Process Batch
                </>
              )}
            </button>
          </div>

          {/* Progress bar during upload */}
          {isUploading && (
            <div className="w-full bg-background-light h-2">
              <div 
                className="bg-primary h-2 transition-all duration-300 ease-out"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          )}

          <div className="max-h-64 overflow-y-auto p-2">
            {selectedFiles.map((file, index) => (
              <div 
                key={file.name + index}
                className="flex items-center justify-between p-2 hover:bg-background-light/50 rounded"
              >
                <div className="flex items-center gap-3">
                  <FileText className="text-primary" />
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-xs text-gray-400">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <div className="flex items-center">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openPreview(file);
                    }}
                    className="text-gray-400 hover:text-primary p-1 mr-1"
                    title="Preview PDF"
                  >
                    <Eye size={16} />
                  </button>
                  {!isUploading && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(file);
                      }}
                      className="text-gray-400 hover:text-white p-1"
                      title="Remove file"
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Help text */}
      <div className="text-center text-gray-400 text-sm">
        <p>
          Supported format: PDF only. Maximum 100 files per batch, 10MB per file.
        </p>
      </div>

      {/* PDF Preview Modal */}
      {previewFile && (
        <PDFPreview file={previewFile} onClose={closePreview} />
      )}
    </div>
  );
} 