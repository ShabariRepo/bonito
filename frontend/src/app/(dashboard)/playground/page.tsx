"use client";

import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { PageHeader } from "@/components/ui/page-header";
import { 
  Send, 
  Settings, 
  Trash2, 
  Copy,
  DollarSign,
  Clock,
  Zap,
  Users,
  Bot,
  User,
  RefreshCw
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

interface Model {
  id: string;
  model_id: string;
  display_name: string;
  provider_type: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: number;
}

interface PlaygroundResponse {
  response: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  cost: number;
  latency_ms: number;
  provider: string;
}

interface CompareResult {
  model_id: string;
  display_name: string;
  response: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  cost: number;
  latency_ms: number;
  provider: string;
  error?: string;
}

export default function PlaygroundPage() {
  const searchParams = useSearchParams();
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [compareMode, setCompareMode] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentInput, setCurrentInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1000);
  const [showSettings, setShowSettings] = useState(false);
  const [modelSearch, setModelSearch] = useState("");
  const [providerFilter, setProviderFilter] = useState<string>("all");
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const [lastResponse, setLastResponse] = useState<PlaygroundResponse | null>(null);
  const [compareResults, setCompareResults] = useState<CompareResult[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, compareResults]);

  // Fetch models on load
  useEffect(() => {
    async function fetchModels() {
      try {
        const res = await apiRequest("/api/models/");
        if (res.ok) {
          const data = await res.json();
          setModels(data);
          
          // Set initial model from URL param or first model
          const modelParam = searchParams.get("model");
          if (modelParam) {
            setSelectedModel(modelParam);
          } else if (data.length > 0) {
            setSelectedModel(data[0].id);
          }
        }
      } catch (e) {
        console.error("Failed to fetch models", e);
      }
    }
    fetchModels();
  }, [searchParams]);

  // Close model dropdown on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setModelDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Get unique providers for filter tabs
  const providers = Array.from(new Set(models.map(m => m.provider_type))).sort();

  // Filter models by search + provider
  const filteredModels = models.filter(m => {
    const matchesSearch = !modelSearch || 
      m.display_name.toLowerCase().includes(modelSearch.toLowerCase()) ||
      m.model_id.toLowerCase().includes(modelSearch.toLowerCase());
    const matchesProvider = providerFilter === "all" || m.provider_type === providerFilter;
    return matchesSearch && matchesProvider;
  });

  const handleSendMessage = async () => {
    if (!currentInput.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: currentInput,
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentInput("");
    setIsLoading(true);

    try {
      if (compareMode && selectedModels.length >= 2) {
        // Compare mode
        const response = await apiRequest("/api/models/compare", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model_ids: selectedModels,
            messages: [...messages, userMessage].map(m => ({ role: m.role, content: m.content })),
            temperature,
            max_tokens: maxTokens
          })
        });

        if (response.ok) {
          const data = await response.json();
          setCompareResults(data.results);
        }
      } else {
        // Single model mode
        if (!selectedModel) return;

        const response = await apiRequest(`/api/models/${selectedModel}/playground`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: [...messages, userMessage].map(m => ({ role: m.role, content: m.content })),
            temperature,
            max_tokens: maxTokens
          })
        });

        if (response.ok) {
          const data: PlaygroundResponse = await response.json();
          setLastResponse(data);
          
          const assistantMessage: Message = {
            role: "assistant",
            content: data.response,
            timestamp: Date.now()
          };
          
          setMessages(prev => [...prev, assistantMessage]);
        } else {
          const errData = await response.json().catch(() => ({}));
          const errMsg = errData.detail || `Request failed (${response.status})`;
          setMessages(prev => [...prev, {
            role: "assistant" as const,
            content: `⚠️ Error: ${errMsg}`,
            timestamp: Date.now()
          }]);
        }
      }
    } catch (e) {
      console.error("Failed to send message", e);
      setMessages(prev => [...prev, {
        role: "assistant" as const,
        content: `⚠️ Network error: ${e instanceof Error ? e.message : "Failed to reach server"}`,
        timestamp: Date.now()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const clearMessages = () => {
    setMessages([]);
    setLastResponse(null);
    setCompareResults([]);
  };

  const toggleCompareMode = () => {
    setCompareMode(!compareMode);
    if (!compareMode) {
      // Entering compare mode - select first 2 models
      setSelectedModels(models.slice(0, 2).map(m => m.id));
    } else {
      // Exiting compare mode
      setSelectedModels([]);
      setCompareResults([]);
    }
  };

  const toggleModelSelection = (modelId: string) => {
    if (selectedModels.includes(modelId)) {
      setSelectedModels(prev => prev.filter(id => id !== modelId));
    } else if (selectedModels.length < 4) {
      setSelectedModels(prev => [...prev, modelId]);
    }
  };

  const getModelName = (modelId: string) => {
    const model = models.find(m => m.id === modelId);
    return model?.display_name || model?.model_id || "Unknown Model";
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-12rem)] space-y-6">
      <PageHeader
        title="AI Playground"
        description="Test and compare AI models with interactive chat"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={toggleCompareMode}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                compareMode 
                  ? "bg-violet-600 text-white" 
                  : "bg-accent text-foreground hover:bg-accent/80"
              }`}
            >
              <Users className="h-4 w-4 mr-1.5" />
              Compare Mode
            </button>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                showSettings 
                  ? "bg-accent text-foreground" 
                  : "hover:bg-accent"
              }`}
            >
              <Settings className="h-4 w-4" />
            </button>
            <button
              onClick={clearMessages}
              className="px-3 py-1.5 text-sm font-medium rounded-lg hover:bg-destructive/10 hover:text-destructive transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        }
      />

      <div className="flex flex-col lg:flex-row flex-1 gap-6 min-h-0">
        {/* Main chat area */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Model selection */}
          <Card className="mb-4">
            <CardContent className="py-4">
              {compareMode ? (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-medium">Select Models to Compare (max 4)</h3>
                    <Badge variant="secondary">{selectedModels.length}/4</Badge>
                  </div>
                  <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                    {models.map(model => (
                      <button
                        key={model.id}
                        onClick={() => toggleModelSelection(model.id)}
                        className={`p-3 text-left rounded-lg border transition-colors ${
                          selectedModels.includes(model.id)
                            ? "border-violet-500 bg-violet-50 dark:bg-violet-950"
                            : "border-border hover:border-violet-300"
                        }`}
                      >
                        <div className="font-medium text-sm">{model.display_name}</div>
                        <div className="text-xs text-muted-foreground capitalize">
                          {model.provider_type}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div ref={modelDropdownRef} className="relative">
                  <label className="block text-sm font-medium mb-2">Select Model</label>
                  {/* Selected model display / search input */}
                  <div
                    className="w-full p-2 border rounded-lg bg-background cursor-pointer flex items-center justify-between"
                    onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                  >
                    <span className={selectedModel ? "text-foreground" : "text-muted-foreground"}>
                      {selectedModel ? `${getModelName(selectedModel)} (${models.find(m => m.id === selectedModel)?.provider_type || ""})` : "Select a model..."}
                    </span>
                    <svg className={`h-4 w-4 text-muted-foreground transition-transform ${modelDropdownOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                  </div>

                  {/* Dropdown */}
                  {modelDropdownOpen && (
                    <div className="absolute z-50 mt-1 w-full bg-card border border-border rounded-lg shadow-xl max-h-[60vh] flex flex-col">
                      {/* Search */}
                      <div className="p-2 border-b border-border">
                        <input
                          type="text"
                          placeholder="Search models..."
                          value={modelSearch}
                          onChange={(e) => setModelSearch(e.target.value)}
                          className="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-violet-500"
                          autoFocus
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>
                      {/* Provider filter tabs */}
                      <div className="flex flex-wrap gap-1 p-2 border-b border-border">
                        <button
                          onClick={(e) => { e.stopPropagation(); setProviderFilter("all"); }}
                          className={`px-2 py-1 text-xs font-medium rounded-md whitespace-nowrap transition-colors ${
                            providerFilter === "all" ? "bg-violet-600 text-white" : "bg-accent text-muted-foreground hover:text-foreground"
                          }`}
                        >
                          All ({models.length})
                        </button>
                        {providers.map(p => (
                          <button
                            key={p}
                            onClick={(e) => { e.stopPropagation(); setProviderFilter(p); }}
                            className={`px-2 py-1 text-xs font-medium rounded-md whitespace-nowrap transition-colors uppercase ${
                              providerFilter === p ? "bg-violet-600 text-white" : "bg-accent text-muted-foreground hover:text-foreground"
                            }`}
                          >
                            {p} ({models.filter(m => m.provider_type === p).length})
                          </button>
                        ))}
                      </div>
                      {/* Model list */}
                      <div className="overflow-y-auto flex-1">
                        {filteredModels.length === 0 ? (
                          <div className="p-4 text-sm text-muted-foreground text-center">No models match</div>
                        ) : (
                          filteredModels.map(model => (
                            <button
                              key={model.id}
                              onClick={() => {
                                setSelectedModel(model.id);
                                setModelDropdownOpen(false);
                                setModelSearch("");
                              }}
                              className={`w-full px-3 py-2 text-left hover:bg-accent transition-colors flex items-center justify-between ${
                                selectedModel === model.id ? "bg-violet-500/10 text-violet-400" : ""
                              }`}
                            >
                              <div className="min-w-0">
                                <div className="text-sm font-medium truncate">{model.display_name}</div>
                                <div className="text-xs text-muted-foreground">{model.model_id}</div>
                              </div>
                              <span className="text-xs text-muted-foreground uppercase ml-2 flex-shrink-0">{model.provider_type}</span>
                            </button>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Messages area */}
          <Card className="flex-1 flex flex-col min-h-0">
            <CardHeader className="py-4 border-b">
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-5 w-5" />
                Conversation
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-0">
              <div className="p-4 space-y-4">
                {messages.length === 0 && (
                  <div className="text-center py-12">
                    <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-medium">Start a conversation</h3>
                    <p className="text-muted-foreground">
                      Type a message below to begin testing your AI model
                    </p>
                  </div>
                )}
                
                {messages.map((message, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`max-w-[80%] ${message.role === "user" ? "order-2" : ""}`}>
                      <div className={`p-3 rounded-lg ${
                        message.role === "user" 
                          ? "bg-violet-600 text-white" 
                          : "bg-accent"
                      }`}>
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </div>
                    </div>
                    <div className={`flex-shrink-0 ${message.role === "user" ? "order-1" : ""}`}>
                      <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                        message.role === "user" 
                          ? "bg-violet-100 dark:bg-violet-900" 
                          : "bg-accent"
                      }`}>
                        {message.role === "user" ? 
                          <User className="h-4 w-4" /> : 
                          <Bot className="h-4 w-4" />
                        }
                      </div>
                    </div>
                  </motion.div>
                ))}

                {compareMode && compareResults.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-3"
                  >
                    <h4 className="font-medium text-sm text-muted-foreground">Model Comparison Results</h4>
                    {compareResults.map((result, i) => (
                      <div key={i} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h5 className="font-medium">{result.display_name}</h5>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>${result.cost.toFixed(4)}</span>
                            <span>•</span>
                            <span>{result.latency_ms}ms</span>
                          </div>
                        </div>
                        {result.error ? (
                          <div className="text-destructive text-sm">Error: {result.error}</div>
                        ) : (
                          <div className="text-sm">{result.response}</div>
                        )}
                      </div>
                    ))}
                  </motion.div>
                )}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-accent p-3 rounded-lg">
                      <LoadingDots size="sm" />
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </CardContent>
          </Card>

          {/* Input area */}
          <Card className="mt-4">
            <CardContent className="p-4">
              <div className="flex gap-2">
                <textarea
                  value={currentInput}
                  onChange={(e) => setCurrentInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  className="flex-1 min-h-[60px] max-h-32 p-3 border rounded-lg resize-none bg-background"
                  disabled={isLoading}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!currentInput.trim() || isLoading || (!compareMode && !selectedModel) || (compareMode && selectedModels.length < 2)}
                  className="px-4 py-3 bg-violet-600 text-white rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end min-h-[44px] min-w-[44px] flex items-center justify-center touch-manipulation"
                >
                  {isLoading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Settings sidebar - desktop sidebar, mobile modal */}
        <AnimatePresence>
          {showSettings && (
            <>
              {/* Mobile backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
                onClick={() => setShowSettings(false)}
              />

              {/* Settings panel */}
              <motion.div
                initial={{ 
                  width: 0, 
                  opacity: 0,
                  x: "100%" 
                }}
                animate={{ 
                  width: "auto", 
                  opacity: 1,
                  x: 0 
                }}
                exit={{ 
                  width: 0, 
                  opacity: 0,
                  x: "100%" 
                }}
                transition={{ duration: 0.2 }}
                className="fixed top-0 right-0 z-50 h-full w-80 lg:relative lg:w-80 overflow-hidden"
              >
              <Card className="h-full">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="h-5 w-5" />
                    Settings
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium mb-2">Temperature</label>
                    <input
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={temperature}
                      onChange={(e) => setTemperature(Number(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground mt-1">
                      <span>0 (Focused)</span>
                      <span className="font-medium">{temperature}</span>
                      <span>2 (Creative)</span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Max Tokens</label>
                    <input
                      type="number"
                      min="1"
                      max="4000"
                      value={maxTokens}
                      onChange={(e) => setMaxTokens(Number(e.target.value))}
                      className="w-full p-2 border rounded-lg bg-background"
                    />
                  </div>

                  {lastResponse && !compareMode && (
                    <div className="space-y-3 pt-6 border-t">
                      <h4 className="font-medium">Response Metrics</h4>
                      
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Tokens</span>
                          <span className="font-medium">{lastResponse.usage.total_tokens}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Cost</span>
                          <span className="font-medium">${lastResponse.cost.toFixed(4)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Latency</span>
                          <span className="font-medium">{lastResponse.latency_ms}ms</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-muted-foreground">Provider</span>
                          <span className="font-medium capitalize">{lastResponse.provider}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}