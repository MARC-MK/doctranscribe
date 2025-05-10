import React, { useState, useEffect, useRef } from "react";
import { X, Send, Brain, Loader2, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";

interface AssistantDrawerProps {
  jobId: string;
  onClose: () => void;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Anomaly {
  row_id: string;
  algorithm: string;
  score: number;
  dismissed: boolean;
}

interface JobContext {
  json_file_id: string;
  anomalies: Anomaly[];
  xlsx_url: string;
}

const AssistantDrawer: React.FC<AssistantDrawerProps> = ({
  jobId,
  onClose,
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [jobContext, setJobContext] = useState<JobContext | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleClose = () => {
    setIsOpen(false);
    // Give time for animation to complete
    setTimeout(onClose, 200);
  };

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Load job context
  useEffect(() => {
    const fetchJobContext = async () => {
      setIsLoading(true);
      try {
        const response = await api.get(`/jobs/${jobId}/context`);
        setJobContext(response.data);
      } catch (error) {
        console.error("Error fetching job context:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobContext();
  }, [jobId]);

  // Create a detailed initial greeting when job context is loaded
  useEffect(() => {
    if (jobContext && jobContext.anomalies.length > 0) {
      // Sort anomalies by score (descending) to prioritize most important ones
      const sortedAnomalies = [...jobContext.anomalies].sort(
        (a, b) => b.score - a.score,
      );
      const highestPriorityAnomaly = sortedAnomalies[0];

      // Extract meaningful data for initial greeting
      const anomalyCount = sortedAnomalies.length;
      const highestScore = Math.round(highestPriorityAnomaly.score * 100);
      const urgentRowId = highestPriorityAnomaly.row_id;

      // Determine recommended first action based on context
      let recommendedAction = "";
      if (anomalyCount > 3) {
        recommendedAction =
          "I recommend starting with a summary view since there are multiple anomalies.";
      } else if (highestScore > 90) {
        recommendedAction = `I recommend reviewing ${urgentRowId} first since it has high confidence (${highestScore}%).`;
      } else {
        recommendedAction =
          "I recommend a row-by-row review to examine each anomaly in detail.";
      }

      // Create detailed greeting
      const initialMessage = {
        role: "assistant" as const,
        content: `I found ${anomalyCount} anomalies in this job. The most significant is in ${urgentRowId} (${highestScore}% confidence).\n\n${recommendedAction}\n\nHow would you like to proceed?`,
      };
      setMessages([initialMessage]);
    } else if (jobContext && jobContext.anomalies.length === 0) {
      // No anomalies case
      const initialMessage = {
        role: "assistant" as const,
        content: `I didn't find any anomalies in this job. The data appears to be within expected ranges. You can still view the data or ask me questions about it.`,
      };
      setMessages([initialMessage]);
    }
  }, [jobContext]);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleQuickAction = async (action: string) => {
    // Add user message
    const userMessage = {
      role: "user" as const,
      content: action,
    };
    setMessages((prev) => [...prev, userMessage]);

    // Now send to API
    await sendMessage(action);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    // Add user message to chat
    const userMessage = {
      role: "user" as const,
      content: inputValue,
    };
    setMessages((prev) => [...prev, userMessage]);

    // Clear input
    setInputValue("");

    // Send message to API
    await sendMessage(inputValue);
  };

  const sendMessage = async (message: string) => {
    setIsLoading(true);
    try {
      const response = await api.post("/assistant/chat", {
        job_id: jobId,
        user_message: message,
      });

      // Add assistant response
      if (response.data?.assistant_messages) {
        const newMessages = response.data.assistant_messages.map(
          (msg: unknown) => ({
            role: msg as string,
            content: msg as string,
          }),
        );

        setMessages((prev) => [...prev, ...newMessages]);
      }

      // Check if this was a dismiss request and it was confirmed
      if (
        message.toLowerCase().includes("yes") &&
        message.toLowerCase().includes("dismiss") &&
        jobContext
      ) {
        // TODO: Call dismiss API
        console.log("Would dismiss anomaly here");
      }
    } catch (error) {
      console.error("Error sending message:", error);
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I encountered an error processing your request. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Generate quick action buttons based on anomaly context
  const getQuickActionButtons = () => {
    if (!jobContext || jobContext.anomalies.length === 0) return null;

    return (
      <div className="flex flex-wrap gap-2 mt-4">
        <button
          onClick={() => handleQuickAction("Show me a summary")}
          className="px-3 py-1.5 bg-white border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50"
        >
          Summary
        </button>
        <button
          onClick={() => handleQuickAction("Review row by row")}
          className="px-3 py-1.5 bg-white border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50"
        >
          Row-by-row
        </button>
        {jobContext.anomalies.length > 0 && (
          <button
            onClick={() =>
              handleQuickAction(
                `Tell me about ${jobContext.anomalies[0].row_id}`,
              )
            }
            className="px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-full text-sm text-blue-700 hover:bg-blue-100"
          >
            <span className="flex items-center">
              <AlertTriangle size={12} className="mr-1" />
              Check highest priority
            </span>
          </button>
        )}
        <button
          onClick={() => handleQuickAction("Dismiss all anomalies")}
          className="px-3 py-1.5 bg-white border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50"
        >
          Dismiss all
        </button>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" aria-modal="true">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/30 backdrop-blur-sm transition-opacity"
        onClick={handleClose}
      />

      {/* Drawer */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="fixed inset-y-0 right-0 flex max-w-full"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            <div className="w-screen max-w-md">
              <div className="flex h-full flex-col bg-white shadow-xl">
                {/* Header */}
                <div className="border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Brain className="text-blue-600" size={20} />
                    <h2 className="text-lg font-semibold text-gray-800">
                      Anomaly Assistant
                    </h2>
                  </div>
                  <button
                    onClick={handleClose}
                    className="text-gray-400 hover:text-gray-500 focus:outline-none"
                  >
                    <X size={20} />
                  </button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
                  {isLoading && messages.length === 0 ? (
                    <div className="flex items-center justify-center h-32">
                      <div className="flex flex-col items-center">
                        <Loader2
                          className="animate-spin text-blue-600 mb-2"
                          size={24}
                        />
                        <p className="text-gray-500 text-sm">
                          Analyzing anomalies...
                        </p>
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* Messages */}
                      <div className="space-y-4">
                        {messages.map((message, index) => (
                          <div
                            key={index}
                            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                          >
                            <div
                              className={`rounded-lg px-4 py-2 max-w-[80%] ${
                                message.role === "user"
                                  ? "bg-blue-600 text-white"
                                  : "bg-white border border-gray-200 text-gray-800"
                              }`}
                            >
                              {message.content.split("\n").map((line, i) => (
                                <React.Fragment key={i}>
                                  {line}
                                  {i <
                                    message.content.split("\n").length - 1 && (
                                    <br />
                                  )}
                                </React.Fragment>
                              ))}
                            </div>
                          </div>
                        ))}
                        {/* Loading indicator for responses */}
                        {isLoading && messages.length > 0 && (
                          <div className="flex justify-start">
                            <div className="rounded-lg px-4 py-2 bg-white border border-gray-200">
                              <Loader2
                                className="animate-spin text-blue-600"
                                size={20}
                              />
                            </div>
                          </div>
                        )}
                        <div ref={messagesEndRef} />
                      </div>

                      {/* Quick Action chips - only show after initial greeting */}
                      {messages.length === 1 &&
                        !isLoading &&
                        getQuickActionButtons()}
                    </>
                  )}
                </div>

                {/* Input form */}
                <div className="border-t border-gray-200 p-4 bg-white">
                  <form onSubmit={handleSendMessage} className="flex">
                    <input
                      type="text"
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder="Type your message..."
                      className="flex-1 rounded-l-md border-0 px-3.5 py-2 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:text-sm"
                      disabled={isLoading}
                    />
                    <button
                      type="submit"
                      className={`rounded-r-md p-2 bg-blue-600 text-white ${
                        isLoading || !inputValue.trim()
                          ? "opacity-50 cursor-not-allowed"
                          : "hover:bg-blue-700"
                      }`}
                      disabled={isLoading || !inputValue.trim()}
                    >
                      <Send size={18} />
                    </button>
                  </form>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default AssistantDrawer;
