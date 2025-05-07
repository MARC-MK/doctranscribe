import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDocument, processDocument, getJobResults, generateXLSX, getXLSXDownloadURL, getJobStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { toast } from "sonner";
import { 
  FileIcon, ClockIcon, CheckCircleIcon, AlertCircleIcon, FileTextIcon, 
  DownloadIcon, RefreshCwIcon, XIcon, ChevronDownIcon, 
  ZoomInIcon, ZoomOutIcon, ArrowLeftIcon, ArrowRightIcon,
  SearchIcon, Minimize2Icon, Edit2Icon, ClipboardIcon, 
  Table, BarChart, FileSpreadsheet, Copy, AlertTriangle
} from "lucide-react";
import XLSXPreview from "@/components/XLSXPreview";

// Types definitions
interface PDFViewerProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  documentId?: string;
}

interface StatusCardProps {
  status?: string;
  activeJob?: any;
  progress: number;
  isProcessing: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  isPending: boolean;
}

interface DocumentInfoCardProps {
  document: any;
  totalPages: number;
  isCompleted: boolean;
  isProcessing: boolean;
  isPending: boolean;
  isFailed: boolean;
  processMutation: any;
  setCurrentTab: (tab: string) => void;
}

// Types for our document data
interface Document {
  id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
  latest_job?: {
    id: string;
    status: string;
  };
}

interface JobStatus {
  id: string;
  status: string;
}

// PDF Viewer Component that uses a direct URL to load PDFs
function PDFViewer({ currentPage, totalPages, onPageChange, documentId }: PDFViewerProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Construct direct URL to the PDF file
  const pdfUrl = documentId 
    ? `/handwriting/documents/${documentId}/pdf${currentPage ? `?page=${currentPage}` : ''}`
    : null;
    
  // Handle errors
  useEffect(() => {
    // Reset loading state when URL changes
    if (pdfUrl) {
      setIsLoading(true);
      setError(null);
      
      // Check if we can access the PDF
      fetch(pdfUrl)
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
          }
          setIsLoading(false);
        })
        .catch(err => {
          console.error('PDF loading error:', err);
          setError(`Failed to load PDF: ${err.message}`);
          setIsLoading(false);
        });
    }
  }, [pdfUrl]);

  // Try a different approach - create a blob URL from the fetch response
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  
  useEffect(() => {
    if (pdfUrl && !error) {
      fetch(pdfUrl)
        .then(response => {
          if (!response.ok) throw new Error(`HTTP error ${response.status}`);
          return response.blob();
        })
        .then(blob => {
          const url = URL.createObjectURL(blob);
          setBlobUrl(url);
        })
        .catch(err => {
          console.error('Error creating blob URL:', err);
        });
    }
    
    return () => {
      // Clean up blob URL when component unmounts
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, [pdfUrl, error]);

  return (
    <div className="border border-gray-700 rounded-md overflow-hidden bg-gray-900 h-full flex flex-col">
      <div className="p-2 bg-gray-800 flex justify-between items-center border-b border-gray-700">
        <div className="flex items-center gap-2">
          <FileIcon className="h-4 w-4 text-blue-400" />
          <span className="text-sm font-medium text-gray-200">PDF Document</span>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 w-8 p-0 text-gray-300 hover:text-white hover:bg-gray-700"
            onClick={() => pdfUrl && window.open(pdfUrl, '_blank')}
            disabled={!pdfUrl}
          >
            <DownloadIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
      
      <div className="flex-1 bg-gray-950/30 flex items-center justify-center">
        {isLoading ? (
          <div className="text-center">
            <div className="h-8 w-8 border-4 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-gray-400">Loading PDF...</p>
          </div>
        ) : error ? (
          <div className="text-center text-gray-400 max-w-md p-4">
            <AlertCircleIcon className="h-16 w-16 mx-auto text-red-500 mb-3" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">Error Loading PDF</h3>
            <p className="text-sm text-gray-400 mb-4">{error}</p>
            <p className="text-xs text-gray-500">
              Try refreshing or check the server logs for more information.
            </p>
          </div>
        ) : blobUrl ? (
          <iframe 
            src={blobUrl} 
            className="w-full h-full border-0"
            title="PDF Document Viewer"
          />
        ) : (
          <div className="text-center text-gray-400 max-w-md p-4">
            <FileIcon className="h-16 w-16 mx-auto text-gray-600 mb-3" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">Generating PDF Preview</h3>
            <p className="text-sm mb-1">Page {currentPage} of {totalPages}</p>
          </div>
        )}
      </div>
      
      <div className="p-2 border-t border-gray-700 bg-gray-800 flex justify-between">
        <Button 
          variant="ghost" 
          size="sm" 
          className="text-gray-300 hover:text-white hover:bg-gray-700"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" /> Previous
        </Button>
        <div className="flex items-center gap-1 text-sm text-gray-400">
          <span>{currentPage} / {totalPages}</span>
        </div>
        <Button 
          variant="ghost" 
          size="sm"
          className="text-gray-300 hover:text-white hover:bg-gray-700"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
        >
          Next <ArrowRightIcon className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  );
}

// Status Card Component
function StatusCard({ status, activeJob, progress, isProcessing, isCompleted, isFailed, isPending }: StatusCardProps) {
  return (
    <Card className="bg-gray-900 border-gray-800 shadow-xl">
      <div className="p-6">
        <h2 className="text-lg font-semibold mb-4">Status</h2>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            {isProcessing && <ClockIcon className="h-5 w-5 text-amber-500 animate-pulse" />}
            {isCompleted && <CheckCircleIcon className="h-5 w-5 text-emerald-500" />}
            {isFailed && <AlertCircleIcon className="h-5 w-5 text-red-500" />}
            {isPending && <ClockIcon className="h-5 w-5 text-gray-400" />}
            <div>
              <div className="font-medium">
                {isProcessing && "Processing"}
                {isCompleted && "Completed"}
                {isFailed && "Failed"}
                {isPending && "Pending"}
              </div>
              <div className="text-sm text-gray-400">
                {isProcessing && "Extracting handwritten text..."}
                {isCompleted && "Text extraction complete"}
                {isFailed && "Error during processing"}
                {isPending && "Waiting to start processing"}
              </div>
            </div>
          </div>

          {activeJob && (
            <>
              <div className="pt-2">
                <div className="flex justify-between text-sm mb-1">
                  <span>Processing Progress</span>
                  <span>{progress}%</span>
                </div>
                <Progress value={progress} className="h-2 bg-gray-800" />
                {isProcessing && (
                  <div className="text-xs text-gray-400 mt-1 text-center">
                    Processing page {activeJob.pages_processed} of {activeJob.total_pages}
                  </div>
                )}
              </div>

              <div className="space-y-2 text-sm pt-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Pages Processed:</span>
                  <span>{activeJob.pages_processed} / {activeJob.total_pages}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Model:</span>
                  <span>{activeJob.model_name}</span>
                </div>
                {activeJob.started_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Started:</span>
                    <span>{new Date(activeJob.started_at).toLocaleString()}</span>
                  </div>
                )}
                {activeJob.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Completed:</span>
                    <span>{new Date(activeJob.completed_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </>
          )}
          
          {isProcessing && (
            <div className="pt-2 text-sm border-t border-gray-800 mt-2">
              <p className="text-gray-400 mt-2">
                Please wait while we process your document. This may take 25-30 seconds per page.
              </p>
            </div>
          )}
          
          {isCompleted && (
            <div className="pt-2 text-sm border-t border-gray-800 mt-2">
              <p className="text-emerald-500 font-medium mt-2">
                Processing complete! You can now view results and export to Excel.
              </p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

// Document Information Card Component
function DocumentInfoCard({ document, totalPages, isCompleted, isProcessing, isPending, isFailed, processMutation, setCurrentTab }: DocumentInfoCardProps) {
  return (
    <Card className="bg-gray-900 border-gray-800 shadow-xl">
      <div className="p-6">
        <h3 className="text-lg font-semibold mb-4">Document Information</h3>
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <FileIcon className="h-5 w-5 text-blue-500 mt-0.5" />
            <div>
              <h4 className="font-medium">File Details</h4>
              <p className="text-sm text-gray-400">
                {document?.filename} • PDF with {totalPages} {totalPages === 1 ? "page" : "pages"}
              </p>
            </div>
          </div>
          
          {/* Conditional content based on status */}
          {isCompleted && (
            <div className="pt-2">
              <p className="text-sm">
                Processing completed successfully. You can now view the extracted text in the Results tab
                or generate an Excel file.
              </p>
              <div className="mt-4">
                <Button 
                  variant="secondary" 
                  size="sm" 
                  onClick={() => setCurrentTab("results")}
                >
                  View Results
                </Button>
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="pt-2">
              <p className="text-sm">
                Currently processing your document using advanced OCR technology.
                This may take several minutes depending on the document size.
              </p>
              <div className="flex items-center gap-2 mt-4 text-sm text-amber-500">
                <div className="h-3 w-3 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                <span>Processing page {document?.latest_job?.pages_processed || 0} of {document?.latest_job?.total_pages || totalPages}</span>
              </div>
            </div>
          )}

          {isPending && (
            <div className="pt-2">
              <p className="text-sm">
                Ready to process. Click the "Start Processing" button to begin extracting handwritten text.
              </p>
              <div className="mt-4">
                <Button 
                  variant="default" 
                  onClick={() => processMutation.mutate()}
                  disabled={processMutation.isPending}
                >
                  {processMutation.isPending ? (
                    <>Starting <RefreshCwIcon className="ml-2 h-4 w-4 animate-spin" /></>
                  ) : (
                    "Start Processing"
                  )}
                </Button>
              </div>
            </div>
          )}

          {isFailed && (
            <div className="pt-2">
              <p className="text-sm text-red-500">
                Processing failed. Please try again or contact support if the issue persists.
              </p>
              <div className="mt-4">
                <Button 
                  variant="secondary" 
                  size="sm" 
                  onClick={() => processMutation.mutate()}
                  disabled={processMutation.isPending}
                >
                  Retry Processing
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

export default function DocumentView() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [currentTab, setCurrentTab] = useState("overview");
  const [xlsxUrl, setXlsxUrl] = useState<string | null>(null);
  const [showXlsxPreview, setShowXlsxPreview] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  // Queries
  const documentQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId ?? ""),
    enabled: !!documentId,
    refetchInterval: (data) => {
      if (!data) return 1000;
      if (data.status === "processing" || data.latest_job?.status === "processing") {
        return 1000;
      }
      return 10000;
    }
  });

  const jobQuery = useQuery({
    queryKey: ["job", documentQuery.data?.latest_job?.id],
    queryFn: () => documentQuery.data?.latest_job?.id ? getJobStatus(documentQuery.data.latest_job.id) : null,
    enabled: !!documentQuery.data?.latest_job?.id,
    refetchInterval: (data) => {
      if (data?.status === "processing") return 1000;
      return false;
    }
  });

  const resultsQuery = useQuery({
    queryKey: ["results", documentQuery.data?.latest_job?.id],
    queryFn: () => documentQuery.data?.latest_job?.id ? getJobResults(documentQuery.data.latest_job.id) : Promise.resolve(null),
    enabled: !!(
      documentQuery.data?.latest_job?.id &&
      (documentQuery.data?.latest_job?.status === "completed" || jobQuery.data?.status === "completed")
    )
  });

  // Process document mutation
  const processMutation = useMutation({
    mutationFn: () => processDocument(documentId ?? ""),
    onSuccess: (data) => {
      toast.success("Processing started");
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
    },
    onError: (error) => {
      toast.error(`Error processing document: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  });

  // Generate XLSX mutation
  const xlsxMutation = useMutation({
    mutationFn: () => documentQuery.data?.latest_job?.id ? generateXLSX(documentQuery.data.latest_job.id) : Promise.resolve(null),
    onSuccess: (data) => {
      if (data) {
        toast.success("XLSX file generated");
        setXlsxUrl(getXLSXDownloadURL(data.id));
      }
    },
    onError: (error) => {
      toast.error(`Error generating XLSX: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  });

  // Calculate progress
  const activeJob = jobQuery.data || documentQuery.data?.latest_job;
  const progress = activeJob ? 
    Math.min(100, Math.round((activeJob.pages_processed / Math.max(1, activeJob.total_pages)) * 100)) : 0;

  // Document status helpers
  const isProcessing = documentQuery.data?.status === "processing" || activeJob?.status === "processing";
  const isCompleted = documentQuery.data?.status === "completed" || activeJob?.status === "completed";
  const isFailed = documentQuery.data?.status === "failed" || activeJob?.status === "failed";
  const isPending = documentQuery.data?.status === "pending" || documentQuery.data?.status === "uploaded";

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };
  
  // Auto-redirect to results tab when processing completes
  useEffect(() => {
    if (isCompleted && currentTab === "overview") {
      const timer = setTimeout(() => {
        setCurrentTab("results");
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, currentTab]);

  // Polling for updates
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        if (documentQuery.data?.latest_job?.id) {
          queryClient.invalidateQueries({ queryKey: ["job", documentQuery.data.latest_job.id] });
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [isProcessing, documentQuery.data?.latest_job?.id, queryClient]);

  if (documentQuery.isLoading) {
    return (
      <div className="flex justify-center items-center py-20">
        <div className="animate-pulse text-center">
          <div className="h-8 w-64 bg-gray-800 rounded-md mb-4 mx-auto"></div>
          <div className="h-4 w-48 bg-gray-800 rounded-md mx-auto"></div>
        </div>
      </div>
    );
  }

  if (documentQuery.isError) {
    return (
      <div className="text-center py-20">
        <AlertCircleIcon className="h-12 w-12 mx-auto text-red-500 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Error Loading Document</h2>
        <p className="text-gray-400 mb-6">We couldn't find the document you're looking for.</p>
        <Button variant="default" onClick={() => navigate("/upload")}>
          Return to Upload
        </Button>
      </div>
    );
  }

  const document = documentQuery.data;
  const totalPages = document?.total_pages || 1;

  return (
    <div className="flex flex-col">
      {/* Header section with document title */}
      <div className="mb-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">
            {document?.filename || "Document"}
          </h1>
          
          {isCompleted && (
            <Button 
              variant="default" 
              onClick={() => xlsxMutation.mutate()}
              disabled={xlsxMutation.isPending}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {xlsxMutation.isPending ? (
                <>Generating <RefreshCwIcon className="ml-2 h-4 w-4 animate-spin" /></>
              ) : (
                <>
                  <FileTextIcon className="mr-2 h-4 w-4" />
                  Export to Excel
                </>
              )}
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1 text-gray-400">
          <FileIcon className="h-4 w-4" />
          <span>
            PDF • {totalPages} {totalPages === 1 ? "page" : "pages"} • 
            Uploaded on {document?.uploaded_at ? new Date(document.uploaded_at).toLocaleDateString() : ""}
          </span>
        </div>
      </div>

      {/* Main tabs */}
      <Tabs value={currentTab} onValueChange={setCurrentTab} className="w-full">
        <div className="flex justify-between items-center mb-4">
          <TabsList className="bg-gray-800/50">
            <TabsTrigger value="overview" className="data-[state=active]:bg-gray-700">Overview</TabsTrigger>
            <TabsTrigger value="results" disabled={!isCompleted} className="data-[state=active]:bg-gray-700">Results</TabsTrigger>
          </TabsList>
          
          {currentTab === "results" && isCompleted && (
            <div className="flex gap-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowXlsxPreview(true)}
                className="text-sm h-8 bg-gray-800 border-gray-700 text-gray-200 hover:bg-gray-700"
              >
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Excel Preview
              </Button>
            </div>
          )}
        </div>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Status Card */}
            <StatusCard 
              status={document?.status}
              activeJob={activeJob}
              progress={progress}
              isProcessing={isProcessing}
              isCompleted={isCompleted}
              isFailed={isFailed}
              isPending={isPending}
            />

            {/* Document Information Card */}
            <DocumentInfoCard 
              document={document}
              totalPages={totalPages}
              isCompleted={isCompleted}
              isProcessing={isProcessing}
              isPending={isPending}
              isFailed={isFailed}
              processMutation={processMutation}
              setCurrentTab={setCurrentTab}
            />
          </div>

          {/* PDF Viewer in Overview */}
          {totalPages > 0 && (
            <div className="mt-4 h-[500px]">
              <PDFViewer 
                currentPage={currentPage} 
                totalPages={totalPages}
                onPageChange={handlePageChange}
                documentId={documentId}
              />
            </div>
          )}
        </TabsContent>

        <TabsContent value="results">
          {resultsQuery.isLoading ? (
            <div className="text-center py-10">
              <div className="h-8 w-8 border-4 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
              <p>Loading extraction results...</p>
            </div>
          ) : resultsQuery.isError ? (
            <Card className="p-6 text-center bg-gray-900 border-gray-800">
              <AlertCircleIcon className="h-8 w-8 text-red-500 mx-auto mb-2" />
              <h3 className="text-lg font-medium mb-1">Error Loading Results</h3>
              <p className="text-sm text-gray-400 mb-4">We encountered an error while retrieving the extraction results.</p>
              <Button 
                variant="secondary" 
                size="sm" 
                onClick={() => resultsQuery.refetch()}
              >
                Try Again
              </Button>
            </Card>
          ) : (
            <div className="grid grid-cols-12 gap-4">
              {/* Left Panel: PDF Preview (3 columns) */}
              <div className="col-span-3 h-[calc(100vh-220px)]">
                <PDFViewer 
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={handlePageChange}
                  documentId={documentId}
                />
              </div>
              
              {/* Right Panel: Excel-like Data (9 columns) */}
              <div className="col-span-9">
                <Card className="bg-white border border-gray-200 h-[calc(100vh-220px)] overflow-auto shadow-lg">
                  {resultsQuery.data?.length > 0 ? (
                    resultsQuery.data.map((result) => (
                      <div key={result.id}>
                        {result.content && typeof result.content === 'object' && (
                          <div>
                            {/* Form Title */}
                            {result.content.form_title && (
                              <div className="sticky top-0 z-10 bg-white border-b border-gray-200 p-3 flex justify-between items-center">
                                <h2 className="text-xl font-semibold text-gray-800">{result.content.form_title}</h2>
                                <div className="flex items-center gap-2">
                                  {result.content.overall_confidence && (
                                    <div className={`px-3 py-1 rounded-full text-sm ${
                                      result.content.overall_confidence >= 0.92 
                                        ? "bg-green-100 text-green-800" 
                                        : result.content.overall_confidence >= 0.75 
                                          ? "bg-amber-100 text-amber-800" 
                                          : "bg-red-100 text-red-800"
                                    }`}>
                                      Confidence: {Math.round(result.content.overall_confidence * 100)}% 
                                      {result.content.overall_confidence < 0.92 && " (fine-tuning)"}
                                    </div>
                                  )}
                                  <Button 
                                    variant="ghost" 
                                    size="sm"
                                    onClick={() => {
                                      navigator.clipboard.writeText(JSON.stringify(result.content, null, 2));
                                      toast.success("JSON copied to clipboard");
                                    }}
                                    className="text-gray-600 hover:text-gray-800 hover:bg-gray-100"
                                  >
                                    <Copy className="h-4 w-4 mr-1" />
                                    Copy JSON
                                  </Button>
                                  <Button 
                                    variant="outline" 
                                    size="sm" 
                                    onClick={() => xlsxMutation.mutate()}
                                    className="border-gray-300 hover:bg-gray-50 text-gray-700"
                                  >
                                    <FileSpreadsheet className="h-4 w-4 mr-1" />
                                    Export
                                  </Button>
                                </div>
                              </div>
                            )}
                            
                            {/* Explanatory Text */}
                            {result.content.explanation_text && (
                              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                                <p className="text-gray-700 whitespace-pre-line">{result.content.explanation_text}</p>
                              </div>
                            )}
                            
                            {/* Questions and Answers in Excel-like format */}
                            {result.content.questions && Array.isArray(result.content.questions) && (
                              <div className="p-0">
                                <table className="w-full border-collapse">
                                  <thead>
                                    <tr>
                                      <th className="w-12 p-3 text-center text-sm font-semibold text-gray-700 bg-gray-100 border border-gray-300">#</th>
                                      <th className="p-3 text-left text-sm font-semibold text-gray-700 bg-gray-100 border border-gray-300">Question</th>
                                      <th className="p-3 text-left text-sm font-semibold text-gray-700 bg-gray-100 border border-gray-300">Answer</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {result.content.questions.map((item, idx) => {
                                      // Extract question number from string if it exists
                                      const questionMatch = item.question?.match(/^(\d+)\.\s/);
                                      const questionNumber = questionMatch ? parseInt(questionMatch[1]) : idx + 1;
                                      
                                      return (
                                        <tr 
                                          key={idx} 
                                          className={`border-b border-gray-300 ${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition-colors duration-150`}
                                        >
                                          <td className="p-3 text-center border-r border-gray-300 text-gray-700">
                                            <div className="flex items-center justify-center">
                                              <div className="w-7 h-7 rounded-full bg-blue-50 flex items-center justify-center text-blue-500 font-medium text-sm">
                                                {questionNumber}
                                              </div>
                                            </div>
                                          </td>
                                          <td className="p-3 text-gray-800 border-r border-gray-300">
                                            <div className="font-medium">
                                              {item.question}
                                            </div>
                                            {item.notes && (
                                              <div className="text-sm text-gray-500 mt-1">{item.notes}</div>
                                            )}
                                          </td>
                                          <td className="p-3 text-gray-700 border-r border-gray-300">
                                            {(item.answer && item.answer !== "No answer provided" && String(item.answer).trim() !== "") ? (
                                              <span className="whitespace-pre-line text-gray-700">{item.answer}</span>
                                            ) : (
                                              <span className="text-gray-400 italic">No answer provided</span>
                                            )}
                                            {item.confidence && (
                                              <div className={`flex items-center gap-1 mt-2 text-xs ${
                                                item.confidence >= 0.92 
                                                  ? "text-green-600" 
                                                  : item.confidence >= 0.75 
                                                    ? "text-amber-600" 
                                                    : "text-red-600"
                                              }`}>
                                                {item.confidence < 0.92 && <AlertTriangle className="h-3 w-3" />}
                                                <span>
                                                  Confidence: {Math.round(item.confidence * 100)}%
                                                  {item.confidence < 0.92 && " (below target)"}
                                                </span>
                                              </div>
                                            )}
                                          </td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                            )}
                            
                            {/* Display other structured data from the content */}
                            {Object.entries(result.content)
                              .filter(([key]) => !['form_title', 'explanation_text', 'questions'].includes(key) && typeof result.content[key] !== 'function')
                              .map(([key, value]) => {
                                if (Array.isArray(value) && value.length > 0) {
                                  return (
                                    <div key={key} className="mt-6 px-4 pb-4">
                                      <h3 className="text-lg font-medium mb-3 text-gray-800 capitalize">{key.replace(/_/g, ' ')}</h3>
                                      <div className="border border-gray-300 rounded-md overflow-hidden">
                                        <div className="overflow-x-auto">
                                          <table className="w-full border-collapse">
                                            <thead>
                                              <tr className="bg-gray-100">
                                                {typeof value[0] === 'object' ? (
                                                  Object.keys(value[0]).map(colKey => (
                                                    <th key={colKey} className="p-3 text-left text-sm font-semibold text-gray-700 border-b border-gray-300">
                                                      {colKey.replace(/_/g, ' ')}
                                                    </th>
                                                  ))
                                                ) : (
                                                  <th className="p-3 text-left text-sm font-semibold text-gray-700 border-b border-gray-300">
                                                    Value
                                                  </th>
                                                )}
                                              </tr>
                                            </thead>
                                            <tbody>
                                              {value.map((item, idx) => (
                                                <tr 
                                                  key={idx} 
                                                  className={`${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50`}
                                                >
                                                  {typeof item === 'object' ? (
                                                    Object.values(item).map((val, valIdx) => (
                                                      <td key={valIdx} className="p-3 text-sm text-gray-700 border-b border-gray-300">
                                                        {val === null ? '-' : String(val)}
                                                      </td>
                                                    ))
                                                  ) : (
                                                    <td className="p-3 text-sm text-gray-700 border-b border-gray-300">
                                                      {item === null ? '-' : String(item)}
                                                    </td>
                                                  )}
                                                </tr>
                                              ))}
                                            </tbody>
                                          </table>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                } else if (typeof value === 'object' && value !== null) {
                                  return (
                                    <div key={key} className="mt-6 px-4 pb-4">
                                      <h3 className="text-lg font-medium mb-3 text-gray-800 capitalize">{key.replace(/_/g, ' ')}</h3>
                                      <div className="bg-white border border-gray-300 rounded-md p-4">
                                        <div className="space-y-2">
                                          {Object.entries(value).map(([subKey, subVal]) => (
                                            <div key={subKey} className="flex justify-between items-center border-b border-gray-200 pb-2">
                                              <div className="text-gray-700 font-medium">{subKey.replace(/_/g, ' ')}</div>
                                              <div className="text-gray-600">{subVal === null ? '-' : String(subVal)}</div>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    </div>
                                  );
                                }
                                return null;
                              })}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full">
                      <FileTextIcon className="h-16 w-16 text-red-500 mb-4" />
                      <h3 className="text-xl font-semibold text-gray-800 mb-2">No Extraction Results</h3>
                      <p className="text-gray-600 max-w-md text-center mb-6">
                        The document hasn't been successfully processed. Please start or restart processing to extract the handwritten text.
                      </p>
                      <Button 
                        onClick={() => processMutation.mutate()}
                        disabled={processMutation.isPending}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        {processMutation.isPending ? (
                          <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCwIcon className="mr-2 h-4 w-4" />
                        )}
                        Process Document
                      </Button>
                    </div>
                  )}
                </Card>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
      
      {/* XLSX Preview Dialog */}
      <Dialog open={showXlsxPreview} onOpenChange={setShowXlsxPreview}>
        <DialogContent className="max-w-6xl p-0 bg-transparent border-none">
          {showXlsxPreview && (
            <XLSXPreview 
              jobId={documentQuery.data?.latest_job?.id} 
              onClose={() => setShowXlsxPreview(false)} 
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
} 