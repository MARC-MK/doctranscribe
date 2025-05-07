import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { UploadIcon, FileIcon, XIcon, CheckIcon, AlertCircleIcon } from "lucide-react";
import { toast } from "sonner";
import { uploadDocument } from "@/lib/api";

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [apiKey, setApiKey] = useState("");
  const navigate = useNavigate();

  const uploadMutation = useMutation({
    mutationFn: async ({ file, apiKey }: { file: File; apiKey?: string }) => {
      return uploadDocument(file, apiKey);
    },
    onSuccess: (data) => {
      toast.success("File uploaded successfully!");
      // Navigate to processing page with document ID
      navigate(`/document/${data.id}`);
    },
    onError: (error) => {
      toast.error(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    },
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf") {
        setFile(droppedFile);
      } else {
        toast.error("Please upload a PDF file");
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === "application/pdf") {
        setFile(selectedFile);
      } else {
        toast.error("Please upload a PDF file");
      }
    }
  };

  const handleSubmit = () => {
    if (!file) {
      toast.error("Please select a file to upload");
      return;
    }
    
    uploadMutation.mutate({
      file,
      apiKey: apiKey.trim() || undefined
    });
  };

  const clearFile = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Upload Document</h1>
        <Button 
          variant="default" 
          onClick={handleSubmit} 
          disabled={!file || uploadMutation.isPending}
        >
          {uploadMutation.isPending ? "Uploading..." : "Process Document"}
        </Button>
      </div>

      <Card className="p-6">
        <div 
          className={`
            border-2 border-dashed rounded-lg p-8 text-center 
            ${dragActive ? "border-primary bg-primary/10" : "border-gray-700"}
            ${!file ? "hover:border-primary hover:bg-primary/5 cursor-pointer transition-all" : ""}
          `}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => !file && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept="application/pdf"
            onChange={handleChange}
          />

          {!file ? (
            <>
              <UploadIcon className="mx-auto h-12 w-12 text-gray-500 mb-4" />
              <h3 className="text-xl font-medium">Drag & drop your file here</h3>
              <p className="text-gray-500 mt-2">or click to browse your files</p>
              <p className="text-xs text-gray-400 mt-4">Supported file: PDF</p>
            </>
          ) : (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileIcon className="h-8 w-8 text-primary" />
                <div className="text-left">
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB • PDF</p>
                </div>
              </div>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={(e) => {
                  e.stopPropagation();
                  clearFile();
                }}
              >
                <XIcon className="h-5 w-5" />
              </Button>
            </div>
          )}
        </div>

        {file && (
          <div className="mt-4">
            <h4 className="text-sm font-medium mb-2">OpenAI API Key (Optional)</h4>
            <div className="flex gap-2">
              <input
                type="password"
                placeholder="sk-..."
                className="flex-1 rounded-md border border-gray-700 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <Button 
                variant="secondary" 
                className="text-xs"
                onClick={() => setApiKey("")}
              >
                Clear
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              If not provided, the server will use its configured API key.
            </p>
          </div>
        )}

        {uploadMutation.isPending && (
          <div className="mt-6">
            <div className="flex justify-between text-sm mb-1">
              <span>Uploading file...</span>
              <span>Please wait</span>
            </div>
            <Progress value={50} className="h-2" />
          </div>
        )}
      </Card>

      <Card className="p-6">
        <h3 className="text-xl font-semibold mb-4">How it works</h3>
        <ol className="space-y-4">
          <li className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-primary font-bold">1</span>
            </div>
            <div>
              <h4 className="font-medium">Upload your document</h4>
              <p className="text-gray-500 text-sm">PDF files containing handwritten survey forms</p>
            </div>
          </li>
          <li className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-primary font-bold">2</span>
            </div>
            <div>
              <h4 className="font-medium">AI Processing</h4>
              <p className="text-gray-500 text-sm">Our GPT-4.1 powered system extracts handwritten text</p>
            </div>
          </li>
          <li className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-primary font-bold">3</span>
            </div>
            <div>
              <h4 className="font-medium">Review and Download</h4>
              <p className="text-gray-500 text-sm">Download your extracted data as a structured Excel file</p>
            </div>
          </li>
        </ol>
      </Card>
    </div>
  );
} 