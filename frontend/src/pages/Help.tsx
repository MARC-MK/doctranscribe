import React from "react";
import { FileText, HelpCircle, MessageSquare, Upload, FileSpreadsheet, AlertTriangle } from "lucide-react";

const HelpPage = () => {
  return (
    <div className="max-w-4xl mx-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold mb-3 flex items-center gap-2">
          <HelpCircle className="text-primary" /> Help & Documentation
        </h1>
        <p className="text-gray-400">
          Learn how to use DocTranscribe to convert your handwritten surveys into digital data
        </p>
      </header>

      {/* FAQ accordion */}
      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Frequently Asked Questions</h2>
        
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <details 
              key={index} 
              className="bg-background border border-background-light rounded-lg overflow-hidden group"
            >
              <summary className="cursor-pointer p-4 font-medium flex items-center justify-between">
                {faq.question}
                <span className="text-primary transition-transform duration-200 group-open:rotate-180">
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </span>
              </summary>
              <div className="p-4 pt-0 text-gray-300">
                {faq.answer}
              </div>
            </details>
          ))}
        </div>
      </section>

      {/* Quick start guide */}
      <section className="mb-10">
        <h2 className="text-2xl font-semibold mb-4">Quick Start Guide</h2>
        
        <div className="bg-background border border-background-light rounded-lg p-6">
          <ol className="space-y-6">
            <li className="flex gap-4">
              <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold">
                1
              </div>
              <div>
                <h3 className="font-medium text-lg mb-2 flex items-center gap-2">
                  <Upload size={18} /> Upload Your Survey PDFs
                </h3>
                <p className="text-gray-300 mb-2">
                  Go to the Upload page and drag & drop your survey PDFs. You can upload up to 100 files at once.
                </p>
                <div className="bg-background-light p-3 rounded text-sm">
                  <strong>Tip:</strong> Make sure your PDFs are clear and scanners are set to at least 300 DPI for best results.
                </div>
              </div>
            </li>
            
            <li className="flex gap-4">
              <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold">
                2
              </div>
              <div>
                <h3 className="font-medium text-lg mb-2 flex items-center gap-2">
                  <FileText size={18} /> Wait for Processing
                </h3>
                <p className="text-gray-300 mb-2">
                  Our AI will analyze the handwritten surveys and extract all the information. Processing time depends on the number of surveys and complexity.
                </p>
                <div className="bg-background-light p-3 rounded text-sm">
                  <strong>Note:</strong> You can leave the page and come back later - we'll send you a notification when processing is complete.
                </div>
              </div>
            </li>
            
            <li className="flex gap-4">
              <div className="flex-shrink-0 h-8 w-8 rounded-full bg-primary/20 text-primary flex items-center justify-center font-bold">
                3
              </div>
              <div>
                <h3 className="font-medium text-lg mb-2 flex items-center gap-2">
                  <FileSpreadsheet size={18} /> Download & Review Results
                </h3>
                <p className="text-gray-300 mb-2">
                  Once processing is complete, you can view and download your survey data in Excel format. Each survey field is organized into columns for easy analysis.
                </p>
                <div className="bg-background-light p-3 rounded text-sm">
                  <strong>Tip:</strong> Check the "Confidence" column to identify any responses the AI was unsure about.
                </div>
              </div>
            </li>
          </ol>
        </div>
      </section>

      {/* Support section */}
      <section className="bg-primary/10 border border-primary/20 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-3 flex items-center gap-2">
          <MessageSquare className="text-primary" /> Need Additional Help?
        </h2>
        <p className="mb-4">
          If you have questions not covered in our documentation, our support team is ready to assist you.
        </p>
        <a 
          href="mailto:support@doctranscribe.com" 
          className="inline-block px-4 py-2 bg-primary text-white rounded hover:bg-primary/90 transition"
        >
          Contact Support
        </a>
      </section>
    </div>
  );
};

// Sample FAQ data
const faqs = [
  {
    question: "What types of handwriting can DocTranscribe recognize?",
    answer: "Our AI can recognize both print and cursive handwriting with varying degrees of clarity. For best results, ensure that the handwriting is reasonably legible and the scan quality is good (300 DPI or higher)."
  },
  {
    question: "How many survey pages can I upload at once?",
    answer: "You can upload up to 100 PDF files in a single batch. Each PDF can contain multiple pages of survey responses."
  },
  {
    question: "What happens if the AI can't read part of the handwriting?",
    answer: "When our AI is uncertain about particular text, it will mark those entries with a lower confidence score in the output. This allows you to quickly identify and manually review uncertain entries."
  },
  {
    question: "How long does processing take?",
    answer: "Processing time varies based on the number of surveys and complexity of the handwriting. Generally, a batch of 50 survey pages takes about 5-10 minutes to process completely."
  },
  {
    question: "Can I export the data in formats other than Excel?",
    answer: "Currently, we support Excel (XLSX) as the primary export format. We plan to add support for CSV, JSON, and direct database integration in future updates."
  },
  {
    question: "Is my survey data secure?",
    answer: "Yes, we take data security seriously. All uploads are encrypted in transit and at rest. Your files are processed in isolated environments and automatically deleted after 30 days (or sooner if you choose to delete them manually)."
  }
];

export default HelpPage; 