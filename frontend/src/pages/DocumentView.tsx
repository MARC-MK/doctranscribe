import * as React from "react";
import { useState, useEffect, useRef, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getDocument,
  getDocumentStatus,
  processDocument,
  getJobResults,
  generateXLSX,
  getXLSXDownloadURL,
  getJobStatus,
  getPdfUrl,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  FileIcon,
  ClockIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  FileTextIcon,
  DownloadIcon,
  RefreshCwIcon,
  XIcon,
  ChevronDownIcon,
  ZoomInIcon,
  ZoomOutIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  SearchIcon,
  Minimize2Icon,
  Edit2Icon,
  ClipboardIcon,
  Table,
  BarChart,
  FileSpreadsheet,
  Copy,
  AlertTriangle,
  FileXIcon,
  InfoIcon,
} from "lucide-react";
import XLSXPreview from "@/components/XLSXPreview";

// Import the UI table components
import {
  Table as UITable,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
  name?: string;
  filename?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  uploaded_at?: string;
  total_pages?: number;
  latest_job?: {
    id: string;
    status: string;
    pages_processed?: number;
    total_pages?: number;
    started_at?: string;
    completed_at?: string;
    model_name?: string;
  };
}

interface JobStatus {
  id: string;
  status: string;
  pages_processed?: number;
  total_pages?: number;
  started_at?: string;
  completed_at?: string;
  model_name?: string;
}

interface ExtractedField {
  label: string;
  value: string;
  field_type: string;
  confidence: number;
  is_handwritten: boolean;
}

interface DocumentSection {
  title: string;
  fields: ExtractedField[];
}

interface QuestionAnswer {
  question: string;
  answer: string;
  page: number;
  confidence: number;
  is_handwritten: boolean;
  notes?: string;
}

interface CheckboxField {
  label: string;
  options: string[];
  selected: string;
  confidence: number;
  is_handwritten: boolean;
}

interface SignatureField {
  label: string;
  is_signed: boolean;
  date?: string;
  confidence: number;
  position?: string;
}

interface ExtractedContent {
  form_title?: string;
  document_type?: string;
  explanation_text?: string;
  header?: { text: string; position: string };
  overall_confidence?: number;
  metadata?: Record<string, string>;
  sections?: DocumentSection[];
  questions?: QuestionAnswer[];
  form_elements?: {
    checkboxes?: CheckboxField[];
    signatures?: SignatureField[];
  };
  notes?: string;
  footer?: { text: string; position: string };
}

interface ExtractionResult {
  id: string;
  page_number: number;
  content: ExtractedContent;
  processing_time: number;
  confidence_score: number;
}

// PDF Viewer Component that uses a direct URL to load PDFs
function PDFViewer({
  currentPage,
  totalPages,
  onPageChange,
  documentId,
}: PDFViewerProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pdfUrlRef = useRef<string | null>(null);

  // Use memo to prevent unnecessary calculations
  const pdfUrl = useMemo(() => {
    if (!documentId) return null;
    return getPdfUrl(documentId);
  }, [documentId]);

  useEffect(() => {
    // Store in ref to avoid re-fetching when component re-renders
    if (pdfUrl) {
      pdfUrlRef.current = pdfUrl;
    }

    // Clear previous blob URL to prevent memory leaks
    if (blobUrl) {
      URL.revokeObjectURL(blobUrl);
      setBlobUrl(null);
    }

    if (!pdfUrl) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    // Fetch with AbortController for cleanup
    const controller = new AbortController();

    fetch(pdfUrl, {
      signal: controller.signal,
      headers: {
        "Cache-Control": "max-age=3600",
        Pragma: "cache",
      },
      cache: "force-cache",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `Error fetching PDF: ${response.status} ${response.statusText}`,
          );
        }
        return response.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        setBlobUrl(url);
        // Don't try to cache PDFs in sessionStorage - they're too large
        // and cause QuotaExceededError
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Error loading PDF:", err);
          setError(`Failed to load PDF: ${err.message}`);
        }
      })
      .finally(() => {
        setIsLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [pdfUrl, documentId]);

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (blobUrl) {
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, []);

  return (
    <div className="flex-1 flex flex-col h-full relative">
      <div className="flex-1 bg-gray-950/30 flex items-center justify-center h-[calc(100%-42px)] max-h-full overflow-hidden">
        {isLoading ? (
          <div className="text-center">
            <div className="h-8 w-8 border-4 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-3"></div>
            <p className="text-gray-400">Loading PDF...</p>
          </div>
        ) : error ? (
          <div className="text-center text-gray-400 max-w-md p-4">
            <AlertCircleIcon className="h-16 w-16 mx-auto text-red-500 mb-3" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">
              Error Loading PDF
            </h3>
            <p className="text-sm text-gray-400 mb-4">{error}</p>
            <p className="text-xs text-gray-500">
              Try refreshing or check the server logs for more information.
            </p>
          </div>
        ) : blobUrl ? (
          <iframe
            src={blobUrl}
            className="w-full h-full border-0 max-h-full"
            title="PDF Document Viewer"
            loading="lazy"
            style={{ maxHeight: "100%", maxWidth: "100%", overflow: "auto" }}
          />
        ) : (
          <div className="text-center text-gray-400 max-w-md p-4">
            <FileIcon className="h-16 w-16 mx-auto text-gray-600 mb-3" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">
              Generating PDF Preview
            </h3>
            <p className="text-sm mb-1">
              Page {currentPage} of {totalPages}
            </p>
          </div>
        )}
      </div>

      <div className="p-2 border-t border-gray-700 bg-gray-800 flex justify-between mt-auto">
        <Button
          variant="ghost"
          size="sm"
          className="text-gray-300 hover:text-white hover:bg-gray-700 h-8 px-2"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" /> Prev
        </Button>
        <div className="flex items-center gap-1 text-sm text-gray-400">
          <span>
            {currentPage} / {totalPages}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-gray-300 hover:text-white hover:bg-gray-700 h-8 px-2"
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
function StatusCard({
  status,
  activeJob,
  progress,
  isProcessing,
  isCompleted,
  isFailed,
  isPending,
}: StatusCardProps) {
  return (
    <Card className="bg-gray-900 border-gray-800 shadow-xl">
      <div className="p-6">
        <h2 className="text-lg font-semibold mb-4">Status</h2>
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            {isProcessing && (
              <ClockIcon className="h-5 w-5 text-amber-500 animate-pulse" />
            )}
            {isCompleted && (
              <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
            )}
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
                    Processing page {activeJob.pages_processed} of{" "}
                    {activeJob.total_pages}
                  </div>
                )}
              </div>

              <div className="space-y-2 text-sm pt-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Pages Processed:</span>
                  <span>
                    {activeJob.pages_processed} / {activeJob.total_pages}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Model:</span>
                  <span>{activeJob.model_name}</span>
                </div>
                {activeJob.started_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Started:</span>
                    <span>
                      {new Date(activeJob.started_at).toLocaleString()}
                    </span>
                  </div>
                )}
                {activeJob.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Completed:</span>
                    <span>
                      {new Date(activeJob.completed_at).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </>
          )}

          {isProcessing && (
            <div className="pt-2 text-sm border-t border-gray-800 mt-2">
              <p className="text-gray-400 mt-2">
                Please wait while we process your document. This may take 25-30
                seconds per page.
              </p>
            </div>
          )}

          {isCompleted && (
            <div className="pt-2 text-sm border-t border-gray-800 mt-2">
              <p className="text-emerald-500 font-medium mt-2">
                Processing complete! You can now view results and export to
                Excel.
              </p>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

// Document Information Card Component
function DocumentInfoCard({
  document,
  totalPages,
  isCompleted,
  isProcessing,
  isPending,
  isFailed,
  processMutation,
  setCurrentTab,
}: DocumentInfoCardProps) {
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
                {document?.filename} • PDF with {totalPages}{" "}
                {totalPages === 1 ? "page" : "pages"}
              </p>
            </div>
          </div>

          {/* Conditional content based on status */}
          {isCompleted && (
            <div className="pt-2">
              <p className="text-sm">
                Processing completed successfully. You can now view the
                extracted text in the Results tab or generate an Excel file.
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
                Currently processing your document using advanced OCR
                technology. This may take several minutes depending on the
                document size.
              </p>
              <div className="flex items-center gap-2 mt-4 text-sm text-amber-500">
                <div className="h-3 w-3 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                <span>
                  Processing page {document?.latest_job?.pages_processed || 0}{" "}
                  of {document?.latest_job?.total_pages || totalPages}
                </span>
              </div>
            </div>
          )}

          {isPending && (
            <div className="pt-2">
              <p className="text-sm">
                Ready to process. Click the "Start Processing" button to begin
                extracting handwritten text.
              </p>
              <div className="mt-4">
                <Button
                  variant="default"
                  onClick={() => processMutation.mutate()}
                  disabled={processMutation.isPending || isProcessing}
                >
                  {processMutation.isPending || isProcessing ? (
                    <>
                      Starting <RefreshCwIcon className="ml-2 h-4 w-4 animate-spin" />
                    </>
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
                Processing failed. Please try again or contact support if the
                issue persists.
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

// MemoizedResultCard Component
const MemoizedResultCard = React.memo(function ResultCard({
  question,
  answer,
  confidence,
}: {
  question: string;
  answer: string;
  confidence: number;
}) {
  const isLowConfidence = confidence < 0.95;

  return (
    <div className="bg-gray-800/70 border border-gray-700 rounded-lg p-4 hover:bg-gray-800/90 transition-colors">
      <div className="flex justify-between items-start">
        <h3 className="font-medium text-gray-300 mb-2">{question}</h3>
        <span
          className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${
            isLowConfidence
              ? "bg-amber-400/10 text-amber-400"
              : "bg-emerald-400/10 text-emerald-400"
          }`}
        >
          {isLowConfidence && <AlertTriangle className="h-3 w-3" />}
          Confidence: {Math.round(confidence * 100)}%
          {isLowConfidence && " (below target)"}
        </span>
      </div>
      <p className="text-gray-400 whitespace-pre-line">{answer}</p>
    </div>
  );
});

// Memoized Questionnaire Component to prevent unnecessary re-renders
const MemoizedQuestionnaire = React.memo(function Questionnaire({
  extractedResults,
  overallConfidence,
}: {
  extractedResults: ExtractionResult[] | null;
  overallConfidence: number;
}) {
  console.log("Questionnaire rendering with:", extractedResults);
  // Find the combined result (page 0)
  const combinedResult = useMemo(() => {
    return extractedResults?.find((result) => result.page_number === 0);
  }, [extractedResults]);

  console.log("Combined result:", combinedResult);

  // Get questions from the combined result
  const questions = useMemo(() => {
    return combinedResult?.content?.questions || [];
  }, [combinedResult]);

  console.log("Questions:", questions);

  // If no questions found, show message
  if (!questions || questions.length === 0) {
    return (
      <div className="text-center py-10">
        <FileXIcon className="h-10 w-10 mx-auto text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-400 mb-2">
          No Data Found
        </h3>
        <p className="text-gray-500">
          No extracted questions found in this document.
        </p>
        <p className="text-gray-500 mt-2">
          Document may need to be reprocessed.
        </p>
        {combinedResult && (
          <pre className="text-left text-xs text-gray-400 mt-4 p-4 bg-gray-800 rounded-md overflow-auto">
            {JSON.stringify(combinedResult.content, null, 2)}
          </pre>
        )}
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Questionnaire</h2>
        <div className="bg-amber-100/10 text-amber-400 px-3 py-1 rounded-full text-sm flex gap-1 items-center">
          <InfoIcon className="h-4 w-4" />
          Confidence: {Math.round(overallConfidence * 100)}%
        </div>
      </div>

      <div className="relative rounded-lg border border-gray-800 overflow-hidden">
        <UITable>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>Question</TableHead>
              <TableHead>Answer</TableHead>
              <TableHead className="w-32 text-right">Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {questions.map((question, idx) => {
              return (
                <TableRow key={idx}>
                  <TableCell className="font-medium text-blue-400">
                    {idx + 1}
                  </TableCell>
                  <TableCell className="font-medium">
                    {question.question}
                  </TableCell>
                  <TableCell>{question.answer}</TableCell>
                  <TableCell className="text-right">
                    <div
                      className={`px-2 py-1 rounded-full inline-flex items-center gap-1 text-xs ml-auto ${
                        (question.confidence || 0) < 0.8 
                          ? "bg-red-100 text-red-800" 
                          : (question.confidence || 0) < 0.95 
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-green-100 text-green-800"
                      }`}
                    >
                      {(question.confidence || 0) < 0.8 && (
                        <AlertTriangle className="h-3 w-3 mr-1" />
                      )}
                      {Math.round((question.confidence || 0) * 100)}%
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </UITable>
      </div>
    </div>
  );
});

// Add a function to extract the overall confidence score from results
function getOverallConfidence(results: any[] | null): number {
  if (!results || results.length === 0) return 0;

  const combinedResult = results.find((r) => r.page_number === 0);
  if (combinedResult) {
    if (combinedResult.content?.overall_confidence !== undefined) {
      return combinedResult.content.overall_confidence;
    }
    if (combinedResult.confidence_score !== undefined) {
      return combinedResult.confidence_score;
    }
  }
  return (
    results[0]?.content?.overall_confidence || results[0]?.confidence_score || 0
  );
}

// Fix for the table highlighting in the questionnaire with blue backgrounds
// Add a style tag to the component to handle this special case
const CustomStyles = () => (
  <style>{`
    .hover\\:bg-blue-50\\/20:hover {
      color: #1f2937 !important;
    }
    
    /* Colored backgrounds with text */
    .bg-blue-100, .bg-blue-200, .bg-blue-300 {
      color: #1e40af !important; /* dark blue text */
    }
    
    /* Ensure all colored cells have proper text contrast */
    .px-4.py-3 {
      color: #1f2937; /* text-gray-800 equivalent */
    }

    /* Fix specifically for the blue background question cells */
    [class*="bg-blue-"] {
      color: #1e3a8a !important;
    }
    
    /* These are the specific classes from the screenshot */
    .bg-slate-100 div {
      color: #1f2937;
    }
    
    /* Specific fix for the blue cells in the questionnaire */
    td div[style*="background-color: rgb(219, 234, 254)"] {
      color: #1e3a8a !important;
    }
    
    /* Color adjustment for the table cells with specific background colors */
    div[style*="background-color:"] {
      color: #1e3a8a !important;
    }
    
    /* Fix for the colored question-answer cells in the results tab */
    .questionnaire-for-survey {
      color: #000000 !important;
      font-weight: 600;
    }
    
    /* Direct override for all light blue cells from the screenshot */
    [class^="bg-blue-"] {
      color: #000000 !important;
    }
    
    /* Force black text in all question/answer cells */
    table td, table th {
      color: #000000 !important;
    }
    
    /* Target specific light blue highlighted cells from the screenshot */
    div[style*="background:"] {
      color: #000000 !important;
    }
    
    /* Fix for blue cells with white text in the results view */
    div[style*="background-color: rgb(219, 234, 254)"],
    div[style*="background-color: rgb(191, 219, 254)"],
    div[style*="background-color: rgb(147, 197, 253)"] {
      color: #000 !important;
      text-shadow: 0 0 1px rgba(0,0,0,0.2);
    }
    
    /* Remove the :has() selector as it's not supported in all browsers */
    /* Instead, just target all cells in the result view */
    .overflow-y-auto .px-4.py-3 {
      color: #000000 !important;
    }
    
    /* Ensure all cells in the data table have dark text */
    div.mb-6 div {
      color: #000000 !important;
    }
    
    /* Add !important to all text colors in the table */
    .text-gray-900 {
      color: #000000 !important;
    }
    
    /* Additional fix for the form title box with light background */
    div.mt-6 div.bg-white p-4 div,
    div.col-span-1 div.bg-white p-4 div,
    div.col-span-2 div.bg-white p-4 div {
      color: #000000 !important;
    }
    
    /* Fix for the blue background in the form title box */
    [style*="background-color: rgb(219, 234, 254)"],
    [style*="background-color: rgb(191, 219, 254)"] {
      color: #1e3a8a !important;
      text-shadow: 0 0 1px rgba(0,0,0,0.1);
      font-weight: 500;
    }
    
    /* Explicitly target the metadata boxes at the bottom */
    .mt-6 div.grid .bg-white p-4 div,
    .mt-6 .col-span-1 div,
    .mt-6 .col-span-2 div {
      color: #000000 !important;
    }
    
    /* Target the light blue form title specifically */
    div[style*="background-color:"] {
      color: #000000 !important;
      font-weight: 500;
    }
    
    /* Target the specific metadata boxes at the bottom */
    div:has(> div.text-sm.text-gray-500) div:not(.text-sm) {
      color: #000000 !important;
    }
  `}</style>
);

// Add a specialized component for the form title that handles blue backgrounds
const FormTitleDisplay = ({ title }: { title: string | React.ReactNode }) => {
  // If the title is a string, we can check if it's styled with blue background
  if (typeof title === 'string') {
    return (
      <div className="font-medium" style={{ fontSize: '14px', color: '#000000' }}>
        {title}
      </div>
    );
  }
  
  // Otherwise return as is but with dark color styling
  return (
    <div className="font-medium text-black" style={{ color: '#000000' }}>
      {title}
    </div>
  );
};

export default function DocumentView() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [currentTab, setCurrentTab] = useState("overview");
  const [xlsxUrl, setXlsxUrl] = useState<string | null>(null);
  const [showXlsxPreview, setShowXlsxPreview] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoadingResults, setIsLoadingResults] = useState(false);
  const [hasAttemptedFetch, setHasAttemptedFetch] = useState(false);
  const [stableResultsData, setStableResultsData] = useState<ExtractionResult[] | null>(null);
  
  // New state variables for UI stability
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [lastStableStatus, setLastStableStatus] = useState<string | null>(null);
  const debounceTimerRef = useRef<number | null>(null);
  const stableJobIdRef = useRef<string | null>(null);
  
  // Add error boundary state to prevent crashes
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Error boundary effect
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      console.error('Error caught by error handler:', event.error);
      setHasError(true);
      setErrorMessage(event.error?.message || 'An unknown error occurred');
      // Prevent the error from crashing the app
      event.preventDefault();
    };

    window.addEventListener('error', handleError);
    
    return () => {
      window.removeEventListener('error', handleError);
    };
  }, []);
  
  // React hook to clean up timers on unmount - this must be before any conditional logic
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);
  
  // Show error fallback if we encounter an error
  if (hasError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] p-8 bg-red-50 border border-red-200 rounded-lg">
        <AlertCircleIcon className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-xl font-bold text-red-800 mb-2">Something went wrong</h2>
        <p className="text-red-600 mb-4 text-center max-w-md">{errorMessage || 'There was an error loading this document'}</p>
        <div className="flex gap-4">
          <Button variant="outline" onClick={() => navigate('/')}>
            Go back to documents
          </Button>
          <Button onClick={() => { setHasError(false); window.location.reload(); }}>
            Try again
          </Button>
        </div>
      </div>
    );
  }

  // Add debounce function for state transitions
  const debounceStatusChange = (newStatus: string, callback: () => void, delay = 300) => {
    // Clear any existing timer
    if (debounceTimerRef.current) {
      window.clearTimeout(debounceTimerRef.current);
    }
    
    // Set transitioning state to prevent UI flashes
    setIsTransitioning(true);
    
    // Set a new timer
    debounceTimerRef.current = window.setTimeout(() => {
      setLastStableStatus(newStatus);
      setIsTransitioning(false);
      callback();
    }, delay);
  };

  // --- DEFINE ALL useQuery/useMutation HOOKS FIRST ---
  const documentQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId ?? ""),
    enabled: !!documentId,
    staleTime: 60000,
  });

  const statusQuery = useQuery({
    queryKey: ["document-status", documentId],
    queryFn: () => getDocumentStatus(documentId ?? ""),
    enabled: !!documentId,
    refetchInterval: (query) => {
      const data = query.state.data as any;
      if (!data) return 3000;
      if (
        data.status === "processing" ||
        data.latest_job?.status === "processing"
      )
        return 3000;
      if (
        data.status === "completed" ||
        data.latest_job?.status === "completed"
      )
        return false;
      if (data.status === "failed" || data.latest_job?.status === "failed")
        return false;
      return false;
    },
    staleTime: 5000,
  });

  const resultsQuery = useQuery<ExtractionResult[] | null>({
    queryKey: ["results", statusQuery.data?.latest_job?.id || documentQuery.data?.latest_job?.id],
    queryFn: async () => {
      const jobId = statusQuery.data?.latest_job?.id || documentQuery.data?.latest_job?.id;
      console.log("Fetching results for job:", jobId);
      
      // Set loading state at the beginning of the fetch
      setIsLoadingResults(true);
      setHasAttemptedFetch(true);
      
      if (
        !jobId ||
        jobId.startsWith("temp-") ||
        jobId.startsWith("virtual-")
      ) {
        console.log("Skipping results fetch: No real job ID yet.");
        setIsLoadingResults(false);
        return Promise.resolve(null);
      }
      
      // Store stable job ID reference to prevent unnecessary refetches
      if (jobId !== stableJobIdRef.current) {
        stableJobIdRef.current = jobId;
      }
      
      try {
        console.log("Making fetch request to job results endpoint");
        const results = await getJobResults(jobId);
        console.log("Raw API Results:", JSON.stringify(results).substring(0, 500) + "...");
        
        if (Array.isArray(results) && results.length > 0) {
          // Check if results contain an error response
          const hasErrorResult = results.some(r => 
            r.id?.toString().startsWith('error-') || 
            (r.content && typeof r.content === 'object' && 'error' in r.content)
          );
          
          if (hasErrorResult) {
            console.warn("Backend returned error response:", results[0]);
            
            // Instead of failing, create a synthetic result with the error details
            const errorResults = [{
              id: "synthetic-error-result",
              page_number: 0,
              content: {
                form_title: "Processing Error",
                document_type: "error",
                explanation_text: "An error occurred while processing this document.",
                questions: [
                  {
                    question: "Error Details",
                    answer: results[0]?.content?.error || "Unknown error occurred",
                    page: 0,
                    confidence: 0.0,
                    is_handwritten: false
                  },
                  {
                    question: "Recommendation",
                    answer: "Please try processing the document again or check your OpenAI API key.",
                    page: 0,
                    confidence: 0.0,
                    is_handwritten: false
                  }
                ],
                overall_confidence: 0.0
              },
              processing_time: 0,
              confidence_score: 0
            }];
            
            // Use debouncing to prevent rapid state changes
            debounceStatusChange("error", () => {
              setIsLoadingResults(false);
              setStableResultsData(errorResults);
            });
            return errorResults;
          }
          
          // It's a valid result set - use debouncing for smooth transition
          console.log(`Got ${results.length} results for job ${jobId}`);
          debounceStatusChange("completed", () => {
            setIsLoadingResults(false);
            setStableResultsData(results);
          });
          return results;
        } else {
          console.warn("API returned empty or non-array results:", results);
          // Return a helpful structured empty result instead of null
          const emptyResults = [{
            id: "empty-result",
            page_number: 0,
            content: {
              form_title: "No Results Available",
              document_type: "error",
              explanation_text: "The document was processed but no extraction results were found.",
              questions: [
                {
                  question: "Status",
                  answer: "The document status is completed, but no extraction results were generated.",
                  page: 0,
                  confidence: 0.0,
                  is_handwritten: false
                },
                {
                  question: "Recommendation",
                  answer: "Please try processing the document again.",
                  page: 0,
                  confidence: 0.0,
                  is_handwritten: false
                }
              ],
              overall_confidence: 0.0
            },
            processing_time: 0,
            confidence_score: 0
          }];
          
          // Use debouncing for smooth transition
          debounceStatusChange("empty", () => {
            setIsLoadingResults(false);
            setStableResultsData(emptyResults);
          });
          return emptyResults;
        }
      } catch (error) {
        console.error("Error fetching results:", error);
        setIsLoadingResults(false);
        throw error;
      }
    },
    enabled: !!(
      (statusQuery.data?.latest_job?.id || documentQuery.data?.latest_job?.id) &&
      !(statusQuery.data?.latest_job?.id || documentQuery.data?.latest_job?.id)?.startsWith("temp-") &&
      !(statusQuery.data?.latest_job?.id || documentQuery.data?.latest_job?.id)?.startsWith("virtual-") &&
      // Only try to fetch results if the document/job is completed
      (statusQuery.data?.latest_job?.status === "completed" || 
       statusQuery.data?.status === "completed" ||
       documentQuery.data?.latest_job?.status === "completed" ||
       documentQuery.data?.status === "completed")
    ),
    staleTime: 15000, // 15 seconds
    retry: 3,
    retryDelay: 1000,
    refetchOnWindowFocus: false, // Prevent refetching when window gains focus
  });

  const processMutation = useMutation({
    mutationFn: () => processDocument(documentId ?? ""),
    onMutate: async () => {
      // Optimistically update statusQuery cache
      queryClient.setQueryData(["document-status", documentId], (old: any) => ({
        ...(old || {}),
        status: "processing",
        latest_job: {
          ...(old?.latest_job || {}),
          id: old?.latest_job?.id || `temp-${Date.now()}`,
          status: "processing",
          pages_processed: 0,
          total_pages: old?.latest_job?.total_pages || documentQuery.data?.total_pages || 1,
        },
      }));
      toast.info("Processing started...");
    },
    onSuccess: (data) => {
      toast.success("Processing started");
      queryClient.invalidateQueries({ queryKey: ["document-status", documentId] });
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
    },
    onError: (error) => {
      toast.error(
        `Error processing document: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
      queryClient.invalidateQueries({ queryKey: ["document-status", documentId] });
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
    },
  });

  const xlsxMutation = useMutation({
    mutationFn: () => {
      try {
        // Get the job ID from all possible sources
        const jobId = statusQuery.data?.latest_job?.id || 
                     documentQuery.data?.latest_job?.id || 
                     (resultsQuery.data && resultsQuery.data.length > 0 ? 
                      resultsQuery.data[0].id.split('-')[0] : null);
        
        console.log("Exporting Excel, using job ID:", jobId);
        console.log("Current API base URL:", import.meta.env.VITE_API_URL || "Not set in env");
        
        if (!jobId) {
          console.error("No job ID available for Excel export");
          return Promise.reject(new Error("No job ID available"));
        }
        
        // Use direct axios call to debug the network request more clearly
        const baseUrl = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8080`;
        console.log(`Making Excel export request to: ${baseUrl}/handwriting/jobs/${jobId}/export`);
        
        return generateXLSX(jobId);
      } catch (error) {
        console.error("Error in Excel export mutation:", error);
        return Promise.reject(error);
      }
    },
    onSuccess: (data) => {
      if (!data) {
        toast.error("Failed to generate XLSX - no data returned");
        return;
      }
      
      console.log("XLSX export success:", data);
      toast.success("XLSX file generated");
      
      // Handle different response formats
      const exportId = data.id;
      setXlsxUrl(getXLSXDownloadURL(exportId));
      
      // Try multiple URL formats to improve reliability
      let downloadUrl = null;
      
      // Try the download_url from the response first if available
      if (data.download_url) {
        downloadUrl = getResourceUrl(data.download_url);
        console.log("Using download_url from response:", downloadUrl);
      } 
      // Otherwise use the export ID to construct the URL
      else {
        downloadUrl = getXLSXDownloadURL(exportId);
        console.log("Using constructed download URL:", downloadUrl);
      }
      
      // Attempt to open the download URL
      try {
        console.log("Opening download URL:", downloadUrl);
        window.open(downloadUrl, "_blank");
      } catch (error) {
        console.error("Error opening download URL:", error);
        
        // Try alternative direct download as fallback
        try {
          const fallbackUrl = getResourceUrl(`/handwriting/jobs/${jobId}/export/download`);
          console.log("Trying fallback direct download URL:", fallbackUrl);
          window.open(fallbackUrl, "_blank");
        } catch (fallbackError) {
          console.error("Error with fallback download:", fallbackError);
          toast.error("XLSX file generated but couldn't open download automatically");
        }
      }
    },
    onError: (error) => {
      console.error("XLSX generation error:", error);
      // Show more detailed error message
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'object' && error !== null) {
        // For axios errors
        const axiosError = error as any;
        if (axiosError.response) {
          errorMessage = `Server responded with status ${axiosError.response.status}: ${
            axiosError.response.data?.detail || axiosError.response.statusText || 'Unknown error'
          }`;
        } else if (axiosError.request) {
          errorMessage = "No response received from server. Backend may be down or unreachable.";
        } else {
          errorMessage = axiosError.message || "Unknown error";
        }
      }
      
      toast.error(`Error generating XLSX: ${errorMessage}`);
    },
  });

  // --- Define useMemo AFTER hooks ---
  // Use statusQuery for all status/progress logic
  const activeJob = useMemo(() => {
    // For debugging:
    console.log("StatusQuery data:", JSON.stringify(statusQuery.data));
    
    if (statusQuery.data?.latest_job) {
      console.log("Found latest job in statusQuery:", statusQuery.data.latest_job.id);
      return statusQuery.data.latest_job;
    }
    return null;
  }, [statusQuery.data]);

  const isProcessing = useMemo(() => {
    return (
      statusQuery.data?.status === "processing" ||
      activeJob?.status === "processing"
    );
  }, [statusQuery.data, activeJob]);

  const isCompleted = useMemo(() => {
    return (
      statusQuery.data?.status === "completed" ||
      activeJob?.status === "completed"
    );
  }, [statusQuery.data, activeJob]);

  const isFailed = useMemo(() => {
    return (
      statusQuery.data?.status === "failed" ||
      activeJob?.status === "failed"
    );
  }, [statusQuery.data, activeJob]);

  const isPending = useMemo(() => {
    return (
      !isProcessing && !isCompleted && !isFailed
    );
  }, [isProcessing, isCompleted, isFailed]);

  const progress = useMemo(() => {
    if (activeJob && activeJob.total_pages) {
      return Math.round(
        ((activeJob.pages_processed || 0) / activeJob.total_pages) * 100
      );
    }
    return 0;
  }, [activeJob]);

  // Calculate confidenceValue AFTER useMemo
  const overallConfidenceValue = getOverallConfidence(resultsQuery.data);

  // --- Define useEffect hooks AFTER useMemo ---
  useEffect(() => {
    if (isCompleted && currentTab === "overview") {
      const timer = setTimeout(() => setCurrentTab("results"), 1000);
      return () => clearTimeout(timer);
    }
  }, [isCompleted, currentTab]);

  // --- Robust polling and status logic ---
  // If the job ID is temporary or missing, keep polling and show status
  const isTempJob = !activeJob || (activeJob?.id && activeJob.id.startsWith("temp-"));

  // Always show the status/progress card unless the document/job is truly completed or failed
  const shouldShowStatus = !isCompleted || isProcessing || isTempJob;

  // --- Auto-switch to results tab as soon as results are available ---
  useEffect(() => {
    if (resultsQuery.data && resultsQuery.data.length > 0 && currentTab !== "results" && !isTransitioning) {
      console.log("Results available, switching to results tab");
      // Delay tab switching slightly to prevent UI jitter
      setTimeout(() => {
        setCurrentTab("results");
      }, 100);
    }
  }, [resultsQuery.data, currentTab, isTransitioning]);

  // --- Force status refresh when completed ---
  // Force requery if we detect completion
  useEffect(() => {
    const docStatusCompleted = statusQuery.data?.status === "completed";
    const jobStatusCompleted = activeJob?.status === "completed";
    
    // Only proceed if we're transitioning to completed state
    if ((docStatusCompleted || jobStatusCompleted) && lastStableStatus !== "completed") {
      console.log("Document or Job status shows completed - preparing to fetch results");
      console.log("Document status:", statusQuery.data?.status);
      console.log("Job status:", activeJob?.status);
      console.log("Job ID:", activeJob?.id);
      
      // Update last stable status
      setLastStableStatus("completed");
      
      // Make sure we have the latest job ID - if not, force refresh document data
      if (!activeJob?.id || activeJob.id.startsWith("temp-") || activeJob.id.startsWith("virtual-")) {
        console.log("Missing real job ID, refreshing document data first");
        documentQuery.refetch();
      } else if (!isLoadingResults && !resultsQuery.isLoading) {
        console.log("Have real job ID, fetching results:", activeJob.id);
        // Only refetch if we're not already loading results
        // Explicitly update the results query key to match the job ID
        stableJobIdRef.current = activeJob.id;
        
        // Wait a moment before triggering the fetch to allow state to settle
        setTimeout(() => {
          if (!isLoadingResults) {
            resultsQuery.refetch();
          }
        }, 500);
      }
    }
  }, [statusQuery.data?.status, activeJob?.status, activeJob?.id, documentQuery, resultsQuery, lastStableStatus, isLoadingResults]);

  // --- Results refetch on completion - consolidated for better control ---
  useEffect(() => {
    if (isCompleted && !isLoadingResults && !resultsQuery.isLoading && !stableResultsData) {
      // Only attempt to fetch results if we don't already have them and aren't already fetching
      console.log("Job completed but no results yet, forcing fetch");
      
      // First make sure document data is fresh
      documentQuery.refetch().then(() => {
        statusQuery.refetch().then(() => {
          // Now we should have the latest job ID
          const jobId = statusQuery.data?.latest_job?.id || documentQuery.data?.latest_job?.id;
          
          if (jobId && !jobId.startsWith("temp-") && !jobId.startsWith("virtual-")) {
            // Update our stable reference
            stableJobIdRef.current = jobId;
            
            // Set a small delay to ensure state is settled
            setTimeout(() => {
              if (!isLoadingResults) {
                console.log("Fetching results for job:", jobId);
                resultsQuery.refetch();
              }
            }, 300);
          }
        });
      });
    }
  }, [isCompleted, documentQuery, statusQuery, resultsQuery, isLoadingResults, stableResultsData]);

  // --- Add handleRefresh function with debounce ---
  const handleRefresh = React.useCallback(() => {
    console.log("Performing complete refresh of document and results data");
    
    // Prevent multiple rapid refreshes
    if (isLoadingResults || isTransitioning) {
      console.log("Already loading or transitioning, skipping refresh");
      return;
    }
    
    // Set transition state to prevent UI flashing
    setIsTransitioning(true);
    
    // Invalidate all document and job queries
    queryClient.invalidateQueries({ queryKey: ["document", documentId] });
    queryClient.invalidateQueries({ queryKey: ["document-status", documentId] });
    
    // Refresh document data first
    documentQuery.refetch().then(response => {
      console.log("Document refetch complete:", response.data?.status);
      
      // Get the latest job ID from the refreshed document
      const latestJobId = response.data?.latest_job?.id;
      if (latestJobId) {
        console.log(`Invalidating and refetching results for job: ${latestJobId}`);
        // Update our stable reference
        stableJobIdRef.current = latestJobId;
        
        queryClient.invalidateQueries({ 
          queryKey: ["results", latestJobId] 
        });
        
        // Brief delay to allow state to settle
        setTimeout(() => {
          // End transition state
          setIsTransitioning(false);
          // Explicitly refetch results
          resultsQuery.refetch();
        }, 300);
      } else {
        console.warn("No job ID found after document refresh");
        setIsTransitioning(false);
      }
    }).catch(() => {
      // Make sure we always end transition state
      setIsTransitioning(false);
    });
  }, [queryClient, documentId, documentQuery, resultsQuery, isLoadingResults, isTransitioning]);

  // --- Add an effect to handle initial load of a completed document ---
  useEffect(() => {
    // Check if document is already completed on initial load and results aren't loaded yet
    const docStatus = documentQuery.data?.status;
    const jobStatus = documentQuery.data?.latest_job?.status;
    const resultsEnabled = !!(
      documentQuery.data?.latest_job?.id && 
      !documentQuery.data.latest_job.id.startsWith("temp-") && 
      !documentQuery.data.latest_job.id.startsWith("virtual-") &&
      (jobStatus === "completed" || docStatus === "completed")
    );
    
    if ((docStatus === "completed" || jobStatus === "completed") && 
        !resultsQuery.data && 
        !resultsQuery.isLoading && 
        !resultsQuery.isError && 
        resultsEnabled) {
      console.log("Document already completed on load, fetching results");
      resultsQuery.refetch();
    }
  }, [documentQuery.data, resultsQuery]);
  
  // --- StatusCard state logic ---
  // Determine the current status and message for the StatusCard
  let statusType = "pending";
  let statusTitle = "Pending";
  let statusMessage = "Waiting to start processing";
  let showProgress = false;
  let progressValue = 0;
  let extraInfo = null;
  let indeterminate = false;

  if (isProcessing && activeJob?.id?.startsWith("temp-")) {
    statusType = "starting";
    statusTitle = "Starting";
    statusMessage = "Starting processing…";
  } else if (isProcessing) {
    statusType = "processing";
    statusTitle = "Processing";
    statusMessage = "Extracting handwritten text…";
    showProgress = true;
    progressValue = progress;
    indeterminate = isProcessing && progress === 0;
    extraInfo = (
      <div className="text-xs text-gray-400 mt-1 text-center">
        Processing page {activeJob?.pages_processed || 0} of {activeJob?.total_pages || totalPages}
      </div>
    );
  } else if (isCompleted) {
    statusType = "completed";
    statusTitle = "Completed";
    statusMessage = "Text extraction complete.";
  } else if (isFailed) {
    statusType = "failed";
    statusTitle = "Failed";
    statusMessage = "Error during processing.";
  }

  // --- Conditional rendering for loading/error states ---
  if (documentQuery.isLoading) {
    return <div className="p-10 text-center">Loading document details...</div>;
  }
  if (documentQuery.isError) {
    return (
      <div className="p-10 text-center text-red-500">
        Error loading document details.
      </div>
    );
  }

  // --- Final variable assignments before return ---
  const document = documentQuery.data;
  const totalPages = document?.total_pages || 1;

  // Excel export function defined before any return statements but after all hooks
  const handleExcelExport = () => {
    // Log relevant data to help debug
    console.log("Document data:", documentQuery.data);
    console.log("Status data:", statusQuery.data);
    console.log("Results data:", resultsQuery.data);
    
    // Check if we have a job ID before attempting export
    const jobId = statusQuery.data?.latest_job?.id || 
                documentQuery.data?.latest_job?.id ||
                (resultsQuery.data && resultsQuery.data.length > 0 ? 
                resultsQuery.data[0].id.split('-')[0] : null);
    
    if (!jobId) {
      toast.error("Cannot export - no job ID available. Try refreshing the page.");
      return;
    }
    
    // Display a toast notification to indicate the export process has started
    toast.loading(`Exporting to Excel, job ID: ${jobId}`, {
      id: "excel-export",
      duration: 3000,
    });
    
    console.log("Exporting to Excel, job ID:", jobId);
    console.log("API URL environment:", import.meta.env.VITE_API_URL);
    console.log("Hostname:", window.location.hostname);
    
    // Trigger the Excel export
    xlsxMutation.mutate();
  };

  // --- Results tab rendering ---
  // Compute all needed variables at the top level
  const jobId = statusQuery.data?.latest_job?.id || documentQuery.data?.latest_job?.id;
  const jobStatus = statusQuery.data?.latest_job?.status || documentQuery.data?.latest_job?.status;
  const docStatus = statusQuery.data?.status || documentQuery.data?.status;
  const resultsEnabled = !!(
    jobId && 
    !jobId.startsWith("temp-") && 
    !jobId.startsWith("virtual-") &&
    (jobStatus === "completed" || docStatus === "completed")
  );
  
  // Use stableResultsData if available to prevent UI flashing
  const resultsLoading = (isLoadingResults || (resultsQuery.isLoading && !stableResultsData)) && !isTransitioning;
  const resultsError = resultsQuery.isError && !stableResultsData;
  
  // Always use stableResultsData if it exists, even during loading
  const resultsData = stableResultsData || resultsQuery.data;
  const showSpinner = resultsLoading && !resultsData;

  let resultsContent: JSX.Element;
  
  // If we already have stable results, show them even during transitions
  if (resultsData && resultsData.length > 0 && !isTransitioning) {
    // Render results in a table: one row per page
    console.log("Rendering stable results. Data length:", resultsData.length);
    const pageResults = resultsData.filter(r => r.page_number > 0);
    const combinedResult = resultsData.find(r => r.page_number === 0);
    
    // Get all questions from the combined result
    const questions = combinedResult?.content?.questions || [];
    console.log("Found questions:", questions.length);
    
    // If no questions found, show the raw data
    if (questions.length === 0 && combinedResult) {
      console.log("No questions found in results, showing raw data");
    }

    resultsContent = (
      <div className="p-4">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-semibold questionnaire-for-survey">
            {combinedResult?.content?.form_title || "Extracted Results"}
          </h3>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              className="flex items-center gap-1 text-blue-600 border-blue-200 hover:bg-blue-50"
            >
              <RefreshCwIcon className="h-4 w-4" /> Refresh
            </Button>
            
            {/* Excel export button in results UI header */}
            <Button
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
              onClick={handleExcelExport}
              disabled={xlsxMutation.isPending}
            >
              <FileSpreadsheet className="h-4 w-4" />
              {xlsxMutation.isPending ? "Generating..." : "Export to Excel"}
            </Button>
          </div>
        </div>
        
        {/* Excel-like table view for questions and answers */}
        {questions.length > 0 ? (
          <div className="mb-6 overflow-hidden rounded-lg border border-gray-300 shadow-sm">
            {/* Column headers with Excel-like style */}
            <div className="bg-slate-100 border-b border-slate-300 flex">
              <div className="px-4 py-2 w-12 font-medium text-gray-700 border-r border-slate-300 flex items-center">#</div>
              <div className="px-4 py-2 w-1/3 font-medium text-gray-700 border-r border-slate-300 flex items-center">Question</div>
              <div className="px-4 py-2 flex-1 font-medium text-gray-700 border-r border-slate-300 flex items-center">Answer</div>
              <div className="px-4 py-2 w-20 font-medium text-gray-700 border-r border-slate-300 flex items-center justify-center">Page</div>
              <div className="px-4 py-2 w-32 font-medium text-gray-700 flex items-center justify-center">Confidence</div>
            </div>
            
            <div className="overflow-y-auto max-h-[400px] text-black">
              {questions.map((question, idx) => {
                return (
                  <div 
                    key={idx} 
                    className={`flex border-b border-slate-200 ${idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'} hover:bg-blue-50/20 transition-colors`}
                  >
                    <div className="px-4 py-3 w-12 text-gray-700 font-medium border-r border-slate-200 flex items-center">{idx + 1}</div>
                    <div className="px-4 py-3 w-1/3 text-black font-medium border-r border-slate-200 flex items-center bg-white" style={{ color: "#000000" }}>
                      {/* Render the question as plain text - don't use HTML parsing which causes issues */}
                      {question.question}
                    </div>
                    <div className="px-4 py-3 flex-1 text-black border-r border-slate-200 flex items-center bg-white" style={{ color: "#000000" }}>
                      {/* Render the answer as plain text */}
                      {question.answer}
                    </div>
                    <div className="px-4 py-3 w-20 text-center text-gray-600 border-r border-slate-200 flex items-center justify-center">{question.page || 1}</div>
                    <div className="px-4 py-3 w-32 flex items-center justify-center">
                      <div 
                        className={`w-16 h-6 rounded-md relative overflow-hidden flex items-center justify-center font-medium text-xs ${
                          (question.confidence || 0) < 0.8 
                            ? 'bg-red-100 text-red-800' 
                            : (question.confidence || 0) < 0.95 
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-green-100 text-green-800'
                        }`}
                      >
                        <div 
                          className={`absolute left-0 top-0 bottom-0 opacity-40 ${
                            (question.confidence || 0) < 0.8 
                              ? 'bg-red-300' 
                              : (question.confidence || 0) < 0.95 
                                ? 'bg-yellow-300'
                                : 'bg-green-300'
                          }`}
                          style={{ width: `${Math.round((question.confidence || 0) * 100)}%` }}
                        />
                        <span className="z-10">{Math.round((question.confidence || 0) * 100)}%</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="bg-white p-10 text-center text-gray-500 border border-gray-200 rounded-lg">
            <FileXIcon className="h-10 w-10 mx-auto mb-3 text-gray-400" />
            <p className="text-lg font-medium mb-1">No questions found</p>
            <p className="text-sm">No structured question data was found in the extracted results.</p>
          </div>
        )}
        
        {/* Export options */}
        <div className="mt-6 flex gap-3">
          <Button
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
            onClick={handleExcelExport}
            disabled={xlsxMutation.isPending}
          >
            <FileSpreadsheet className="h-4 w-4" />
            {xlsxMutation.isPending ? "Generating..." : "Export to Excel"}
          </Button>
          
          {/* Direct download button for emergency use */}
          <Button
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
            onClick={() => {
              const jobId = statusQuery.data?.latest_job?.id || 
                          documentQuery.data?.latest_job?.id ||
                          (resultsQuery.data && resultsQuery.data.length > 0 ? 
                           resultsQuery.data[0].id.split('-')[0] : null);
              
              if (!jobId) {
                toast.error("No job ID available");
                return;
              }
              
              // Direct debug endpoint for reliable downloads
              const baseUrl = import.meta.env.VITE_API_URL || 
                          `http://${window.location.hostname}:8080`;
              const url = `${baseUrl}/handwriting/debug/xlsx/${jobId}`;
              
              console.log("Opening direct debug download URL:", url);
              window.open(url, "_blank");
              toast.success("Download started via alternative method");
            }}
          >
            <DownloadIcon className="h-4 w-4" />
            Direct Download
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
            onClick={() => {
              // Create a blob with the JSON data and download it
              const blob = new Blob(
                [JSON.stringify(combinedResult?.content || {}, null, 2)], 
                { type: "application/json" }
              );
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${document?.filename || "document"}_results.json`;
              document.body.appendChild(a);
              a.click();
              document.body.removeChild(a);
              URL.revokeObjectURL(url);
            }}
          >
            <FileTextIcon className="h-4 w-4" />
            Export JSON
          </Button>
          
          {xlsxUrl && (
            <Button
              variant="outline" 
              size="sm"
              className="flex items-center gap-2"
              onClick={() => window.open(xlsxUrl, "_blank")}
            >
              <DownloadIcon className="h-4 w-4" />
              Download XLSX
            </Button>
          )}
        </div>
        
        {/* Additional metadata boxes with proper text contrast */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Form Title box */}
          <div className="col-span-full md:col-span-1">
            <div className="text-gray-700 font-medium mb-2">Form Title</div>
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
              {combinedResult?.content?.form_title ? (
                <div 
                  className="text-black font-medium" 
                  style={{ 
                    color: '#000000', 
                    fontWeight: 500,
                    padding: '8px',
                    borderRadius: '4px'
                  }}
                >
                  {/* Handle blue background case by forcing black text */}
                  <span
                    dangerouslySetInnerHTML={{
                      __html: typeof combinedResult.content.form_title === 'string'
                        ? combinedResult.content.form_title
                            .replace(/style="background-color:[^"]*"/g, 'style="background-color:#e1effe; color:#000000; font-weight:600;"')
                        : String(combinedResult.content.form_title)
                    }}
                    style={{
                      color: '#000000',
                      fontSize: '14px',
                      lineHeight: '1.5'
                    }}
                  />
                </div>
              ) : (
                <div className="text-gray-500">No title available</div>
              )}
            </div>
          </div>
          
          {/* Overall Confidence box */}
          <div className="col-span-full md:col-span-1">
            <div className="text-gray-700 font-medium mb-2">Overall Confidence</div>
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
              <div className="flex flex-col">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-gray-700 font-medium" style={{ color: '#000000' }}>
                    {Math.round(overallConfidenceValue * 100)}%
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    overallConfidenceValue < 0.8 
                      ? 'bg-red-100 text-red-800' 
                      : overallConfidenceValue < 0.95 
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-green-100 text-green-800'
                  }`}>
                    {overallConfidenceValue < 0.8 
                      ? 'Low' 
                      : overallConfidenceValue < 0.95 
                        ? 'Medium'
                        : 'High'
                    }
                  </span>
                </div>
                <div className="h-3 w-full bg-gray-100 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${
                      overallConfidenceValue < 0.8 
                        ? 'bg-red-500' 
                        : overallConfidenceValue < 0.95 
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                    }`}
                    style={{ width: `${Math.round(overallConfidenceValue * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>
          
          {/* Processing Time */}
          {combinedResult?.processing_time && (
            <div className="col-span-full">
              <div className="text-gray-700 font-medium mb-2">Processing Time</div>
              <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm">
                <div className="text-black font-medium" style={{ color: '#000000' }}>
                  {(combinedResult.processing_time).toFixed(2)} seconds
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  } else if (!resultsEnabled) {
    resultsContent = (
      <div className="py-10 text-center text-gray-500">
        <div className="h-8 w-8 border-4 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-3"></div>
        <div className="text-lg font-medium mb-3">Waiting for results…</div>
        <div className="mt-2 text-xs text-gray-400 mb-4">
          Job ID: {jobId || 'N/A'} | Job Status: {jobStatus || 'N/A'} | Doc Status: {docStatus || 'N/A'}
        </div>
        
        {/* Additional info for debugging */}
        <div className="mt-2 p-3 bg-gray-800 rounded-md text-xs text-left mx-auto max-w-md">
          <div className="text-gray-400 mb-2 text-center">Debug Information</div>
          <div className="mb-1"><span className="text-blue-400 mr-2">Document Query Status:</span> {documentQuery.status}</div>
          <div className="mb-1"><span className="text-blue-400 mr-2">Status Query Status:</span> {statusQuery.status}</div>
          <div className="mb-1"><span className="text-blue-400 mr-2">Results Query Status:</span> {resultsQuery.status}</div>
          <div className="mb-1"><span className="text-blue-400 mr-2">isCompleted:</span> {isCompleted ? "true" : "false"}</div>
          <div className="mb-1"><span className="text-blue-400 mr-2">isProcessing:</span> {isProcessing ? "true" : "false"}</div>
        </div>
        
        {(isCompleted || docStatus === "completed" || jobStatus === "completed") && (
          <div className="mt-4">
            <Button variant="secondary" size="sm" onClick={handleRefresh}>
              <RefreshCwIcon className="h-4 w-4 mr-1" /> Force Refresh
            </Button>
          </div>
        )}
      </div>
    );
  } else if (showSpinner) {
    // Only show loading spinner if we don't have any data to display
    resultsContent = (
      <div className="py-10 text-center text-gray-500">
        <div className="h-8 w-8 border-4 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-3"></div>
        <div className="text-lg font-medium mb-2">Loading extraction results…</div>
        <div className="mt-2 text-xs text-gray-400 mb-4">
          Job ID: {jobId || 'N/A'} | Job Status: {jobStatus || 'N/A'} | Doc Status: {docStatus || 'N/A'}
        </div>
      </div>
    );
  } else if (resultsError && !stableResultsData) {
    resultsContent = (
      <div className="text-center py-10">
        <AlertCircleIcon className="h-10 w-10 mx-auto mb-3 text-red-500" />
        <div className="text-lg font-medium mb-2 text-red-500">Error Loading Results</div>
        <div className="mt-2 text-xs text-gray-400 mb-4">
          Job ID: {jobId || 'N/A'} | Job Status: {jobStatus || 'N/A'} | Doc Status: {docStatus || 'N/A'}
        </div>
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={handleRefresh}>
            <RefreshCwIcon className="h-4 w-4 mr-1" /> Force Refresh
          </Button>
        </div>
      </div>
    );
  } else {
    // Generic empty state when we have no data and no specific state to show
    resultsContent = (
      <div className="text-center py-10 text-gray-400">
        <FileXIcon className="h-10 w-10 mx-auto mb-4" />
        <p className="font-medium mb-2">No extraction results available yet</p>
        <p className="text-sm text-gray-500 mb-4">The document has been processed, but no extraction results were found.</p>
        <div className="mt-2 text-xs text-gray-400 mb-4">
          Job ID: {jobId || 'N/A'} | Job Status: {jobStatus || 'N/A'} | Doc Status: {docStatus || 'N/A'}
        </div>
        <Button variant="secondary" size="sm" onClick={handleRefresh}>
          <RefreshCwIcon className="h-4 w-4 mr-1" /> Force Refresh
        </Button>
      </div>
    );
  }

  // --- Return JSX ---
  return (
    <div className="flex flex-col">
      <CustomStyles />
      {/* Always-visible status and document info cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="lg:col-span-2">
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
        <div className="lg:col-span-1">
          {(shouldShowStatus || isTempJob || isCompleted || isFailed) && (
            <Card className="bg-gray-900 border-gray-800 shadow-xl">
              <div className="p-6">
                <h2 className="text-lg font-semibold mb-4">Status</h2>
                <div className="space-y-4">
                  {(() => {
                    try {
                      /* Status icons and info section */
                      return (
                        <>
                          <div className="flex items-center gap-3">
                            {statusType === "processing" && (
                              <ClockIcon className="h-5 w-5 text-amber-500 animate-pulse" />
                            )}
                            {statusType === "starting" && (
                              <ClockIcon className="h-5 w-5 text-blue-400 animate-spin" />
                            )}
                            {statusType === "completed" && (
                              <CheckCircleIcon className="h-5 w-5 text-emerald-500" />
                            )}
                            {statusType === "failed" && (
                              <AlertCircleIcon className="h-5 w-5 text-red-500" />
                            )}
                            {statusType === "pending" && (
                              <ClockIcon className="h-5 w-5 text-gray-400" />
                            )}
                            <div>
                              <div className="font-medium">{statusTitle}</div>
                              <div className="text-sm text-gray-400">{statusMessage}</div>
                            </div>
                          </div>
                          {showProgress && (
                            <>
                              <div className="pt-2">
                                <div className="flex justify-between text-sm mb-1">
                                  <span>Processing Progress</span>
                                  <span>{indeterminate ? <span className="animate-pulse text-amber-500">…</span> : `${progressValue}%`}</span>
                                </div>
                                {indeterminate ? (
                                  <div className="h-2 bg-gradient-to-r from-amber-400 via-amber-200 to-amber-400 animate-pulse rounded-full w-full" />
                                ) : (
                                  <Progress value={progressValue} className="h-2 bg-gray-800" />
                                )}
                                {extraInfo}
                              </div>
                            </>
                          )}
                          {statusType === "processing" && (
                            <div className="pt-2 text-sm border-t border-gray-800 mt-2">
                              <p className="text-gray-400 mt-2">
                                Please wait while we process your document. This may take 25-30 seconds per page.
                              </p>
                            </div>
                          )}
                          {statusType === "completed" && (
                            <div className="pt-2 text-sm border-t border-gray-800 mt-2">
                              <p className="text-emerald-500 font-medium mt-2">
                                Processing complete! You can now view results and export to Excel.
                              </p>
                            </div>
                          )}
                          {statusType === "failed" && (
                            <div className="pt-2 text-sm border-t border-gray-800 mt-2">
                              <p className="text-red-500 font-medium mt-2">
                                Processing failed. Please try again or contact support if the issue persists.
                              </p>
                            </div>
                          )}
                        </>
                      );
                    } catch (err) {
                      console.error("Error rendering status card:", err);
                      return (
                        <div className="py-3 px-2 bg-red-100 border border-red-300 rounded-md text-red-700">
                          <p className="font-medium">Error displaying status</p>
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="mt-2" 
                            onClick={() => window.location.reload()}
                          >
                            Reload page
                          </Button>
                        </div>
                      );
                    }
                  })()}
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Main tabs */}
      <Tabs value={currentTab} onValueChange={setCurrentTab} className="w-full">
        {/* TabsList */}
        <div className="flex justify-between items-center mb-4">
          {/* ... TabsList content ... */}
        </div>

        <TabsContent value="overview">
          {/* Removed 'Overview coming soon…' for a cleaner UI */}
        </TabsContent>

        <TabsContent value="results" className="mt-0">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            {/* Left panel: PDF Viewer */}
            <div className="lg:col-span-1 h-[600px]">
              <PDFViewer
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                documentId={documentId}
              />
            </div>
            {/* Right panel: Extraction Results */}
            <div className="lg:col-span-4">
              <div className="bg-white rounded-lg border border-gray-200 shadow-lg overflow-hidden">
                {/* Header with Confidence */}
                <div className="flex items-center justify-between px-4 py-3 bg-gray-100 border-b border-gray-200">
                  {/* ... Title ... */}
                  <div className="flex gap-2">
                    {isCompleted && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                        className="text-blue-600 border-blue-200 hover:bg-blue-50"
                      >
                        <RefreshCwIcon className="h-4 w-4 mr-1" /> Refresh
                      </Button>
                    )}
                    <div
                      className={`px-3 py-1 rounded-full text-sm flex items-center gap-1 border ${
                        overallConfidenceValue >= 0.95
                          ? "bg-blue-100 text-blue-700 border-blue-200"
                          : "bg-amber-100 text-amber-700 border-amber-200"
                      }`}
                    >
                      {overallConfidenceValue < 0.95 ? (
                        <AlertTriangle className="h-4 w-4 mr-1" />
                      ) : (
                        <InfoIcon className="h-4 w-4 mr-1" />
                      )}
                      Confidence: {Math.round(overallConfidenceValue * 100)}%
                    </div>
                  </div>
                </div>
                {/* Results Content Area */}
                <div className="bg-white">
                  {resultsContent}
                </div>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
