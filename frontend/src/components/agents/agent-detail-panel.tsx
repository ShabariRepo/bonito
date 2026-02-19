"use client";

import { useState, useEffect } from "react";
import { X, Settings, MessageSquare, Clock, BarChart3, Send } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useToast } from "@/components/ui/use-toast";
import { apiRequest } from "@/lib/auth";

interface AgentDetailPanelProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: string | null;
  onAgentUpdate?: () => void;
}

interface Agent {
  id: string;
  name: string;
  description?: string;
  status: string;
  system_prompt: string;
  model_id: string;
  model_config: any;
  knowledge_base_ids: string[];
  total_runs: number;
  total_tokens: number;
  total_cost: number;
  last_active_at?: string;
  created_at: string;
}

interface Session {
  id: string;
  title?: string;
  message_count: number;
  total_tokens: number;
  total_cost: number;
  last_message_at?: string;
  created_at: string;
}

interface Message {
  id: string;
  role: string;
  content?: string;
  tool_calls?: any;
  model_used?: string;
  cost?: number;
  created_at: string;
}

export function AgentDetailPanel({ isOpen, onClose, agentId, onAgentUpdate }: AgentDetailPanelProps) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatMessage, setChatMessage] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (isOpen && agentId) {
      fetchAgentDetails();
      fetchSessions();
    }
  }, [isOpen, agentId]);

  useEffect(() => {
    if (selectedSession) {
      fetchSessionMessages(selectedSession.id);
    }
  }, [selectedSession]);

  const fetchAgentDetails = async () => {
    if (!agentId) return;
    
    setLoading(true);
    try {
      const data = await apiRequest(`/api/agents/${agentId}?include_sessions=true`);
      setAgent(data);
    } catch (error) {
      console.error("Failed to fetch agent:", error);
      toast({
        title: "Error",
        description: "Failed to load agent details",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const fetchSessions = async () => {
    if (!agentId) return;
    
    try {
      const data = await apiRequest(`/api/agents/${agentId}/sessions?limit=10`);
      setSessions(data);
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
    }
  };

  const fetchSessionMessages = async (sessionId: string) => {
    if (!agentId) return;
    
    try {
      const data = await apiRequest(`/api/agents/${agentId}/sessions/${sessionId}/messages`);
      setMessages(data);
    } catch (error) {
      console.error("Failed to fetch messages:", error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentId || !chatMessage.trim()) return;

    setChatLoading(true);
    try {
      const response = await apiRequest(`/api/agents/${agentId}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: chatMessage,
          session_id: selectedSession?.id,
        }),
      });

      setChatMessage("");
      
      // Refresh sessions and messages
      await fetchSessions();
      if (selectedSession) {
        await fetchSessionMessages(selectedSession.id);
      } else {
        // If no session was selected, select the new one
        const newSessions = await apiRequest(`/api/agents/${agentId}/sessions?limit=1`);
        if (newSessions.length > 0) {
          setSelectedSession(newSessions[0]);
        }
      }

      toast({
        title: "Message Sent",
        description: "Agent response received",
      });
    } catch (error) {
      console.error("Failed to send message:", error);
      toast({
        title: "Error",
        description: "Failed to send message",
        variant: "destructive",
      });
    } finally {
      setChatLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 4,
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-US").format(num);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case "user":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "assistant":
        return "bg-green-500/10 text-green-400 border-green-500/30";
      case "system":
        return "bg-gray-500/10 text-gray-400 border-gray-500/30";
      case "tool":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      default:
        return "bg-gray-500/10 text-gray-400 border-gray-500/30";
    }
  };

  if (!agent && !loading) return null;

  return (
    <Sheet open={isOpen} onOpenChange={onClose}>
      <SheetContent side="right" className="w-[800px] sm:max-w-[800px] bg-[#1a1a2e] border-l border-gray-800 text-white">
        <SheetHeader className="border-b border-gray-800 pb-4">
          <div className="flex items-center justify-between">
            <div>
              <SheetTitle className="text-white flex items-center space-x-2">
                <span>{agent?.name || "Loading..."}</span>
                {agent?.status && (
                  <Badge variant="outline" className={
                    agent.status === "active" 
                      ? "bg-green-500/10 text-green-400 border-green-500/30"
                      : "bg-gray-500/10 text-gray-400 border-gray-500/30"
                  }>
                    {agent.status}
                  </Badge>
                )}
              </SheetTitle>
              {agent?.description && (
                <p className="text-sm text-gray-400 mt-1">{agent.description}</p>
              )}
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </SheetHeader>

        {loading ? (
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <Tabs defaultValue="chat" className="h-full">
            <TabsList className="grid w-full grid-cols-4 bg-[#2a2a4e]">
              <TabsTrigger value="chat" className="data-[state=active]:bg-[#3a3a6e]">
                <MessageSquare className="w-4 h-4 mr-2" />
                Chat
              </TabsTrigger>
              <TabsTrigger value="configure" className="data-[state=active]:bg-[#3a3a6e]">
                <Settings className="w-4 h-4 mr-2" />
                Configure
              </TabsTrigger>
              <TabsTrigger value="sessions" className="data-[state=active]:bg-[#3a3a6e]">
                <Clock className="w-4 h-4 mr-2" />
                Sessions
              </TabsTrigger>
              <TabsTrigger value="metrics" className="data-[state=active]:bg-[#3a3a6e]">
                <BarChart3 className="w-4 h-4 mr-2" />
                Metrics
              </TabsTrigger>
            </TabsList>

            <TabsContent value="chat" className="space-y-4 h-full">
              <div className="flex space-x-4 h-full">
                {/* Sessions List */}
                <Card className="w-80 bg-[#2a2a4e] border-gray-700">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm text-white">Sessions</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <ScrollArea className="h-96">
                      {sessions.map((session) => (
                        <div
                          key={session.id}
                          className={`p-3 cursor-pointer hover:bg-[#3a3a6e] border-b border-gray-700 ${
                            selectedSession?.id === session.id ? "bg-[#3a3a6e]" : ""
                          }`}
                          onClick={() => setSelectedSession(session)}
                        >
                          <p className="text-sm text-white font-medium truncate">
                            {session.title || `Session ${session.id.slice(0, 8)}`}
                          </p>
                          <div className="flex justify-between items-center mt-1">
                            <span className="text-xs text-gray-400">
                              {session.message_count} messages
                            </span>
                            <span className="text-xs text-gray-400">
                              {formatCurrency(session.total_cost)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </ScrollArea>
                  </CardContent>
                </Card>

                {/* Chat Area */}
                <Card className="flex-1 bg-[#2a2a4e] border-gray-700 flex flex-col">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm text-white">
                      {selectedSession?.title || "Select a session or start a new conversation"}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    {/* Messages */}
                    <ScrollArea className="flex-1 mb-4">
                      {messages.map((message) => (
                        <div key={message.id} className="mb-4">
                          <div className="flex items-center space-x-2 mb-1">
                            <Badge variant="outline" className={getRoleColor(message.role)}>
                              {message.role}
                            </Badge>
                            {message.model_used && (
                              <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">
                                {message.model_used}
                              </Badge>
                            )}
                            <span className="text-xs text-gray-500">
                              {formatDate(message.created_at)}
                            </span>
                          </div>
                          <div className="bg-[#1a1a2e] rounded-lg p-3 text-sm">
                            {message.content ? (
                              <p className="whitespace-pre-wrap">{message.content}</p>
                            ) : message.tool_calls ? (
                              <pre className="text-xs text-gray-400">
                                {JSON.stringify(message.tool_calls, null, 2)}
                              </pre>
                            ) : (
                              <p className="text-gray-500 italic">No content</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </ScrollArea>

                    {/* Chat Input */}
                    <form onSubmit={handleSendMessage} className="flex space-x-2">
                      <Input
                        placeholder="Send a message to the agent..."
                        value={chatMessage}
                        onChange={(e) => setChatMessage(e.target.value)}
                        className="flex-1 bg-[#1a1a2e] border-gray-600 text-white"
                        disabled={chatLoading}
                      />
                      <Button type="submit" disabled={chatLoading || !chatMessage.trim()}>
                        <Send className="w-4 h-4" />
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            <TabsContent value="configure" className="space-y-4">
              <Card className="bg-[#2a2a4e] border-gray-700">
                <CardHeader>
                  <CardTitle className="text-white">Agent Configuration</CardTitle>
                  <CardDescription className="text-gray-400">
                    Configure the agent's behavior and settings
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-white">System Prompt</label>
                    <Textarea
                      value={agent?.system_prompt || ""}
                      readOnly
                      className="mt-1 bg-[#1a1a2e] border-gray-600 text-white min-h-[200px]"
                      placeholder="Agent system prompt..."
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-white">Model</label>
                      <Input
                        value={agent?.model_id || ""}
                        readOnly
                        className="mt-1 bg-[#1a1a2e] border-gray-600 text-white"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium text-white">Knowledge Bases</label>
                      <Input
                        value={`${agent?.knowledge_base_ids?.length || 0} assigned`}
                        readOnly
                        className="mt-1 bg-[#1a1a2e] border-gray-600 text-white"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="sessions" className="space-y-4">
              <Card className="bg-[#2a2a4e] border-gray-700">
                <CardHeader>
                  <CardTitle className="text-white">Recent Sessions</CardTitle>
                  <CardDescription className="text-gray-400">
                    View conversation history and session details
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-96">
                    {sessions.map((session) => (
                      <Card key={session.id} className="mb-4 bg-[#1a1a2e] border-gray-700">
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start">
                            <div>
                              <h4 className="text-white font-medium">
                                {session.title || `Session ${session.id.slice(0, 8)}`}
                              </h4>
                              <p className="text-sm text-gray-400">
                                {session.message_count} messages • {formatNumber(session.total_tokens)} tokens
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm text-green-400">{formatCurrency(session.total_cost)}</p>
                              <p className="text-xs text-gray-500">
                                {session.last_message_at 
                                  ? formatDate(session.last_message_at)
                                  : formatDate(session.created_at)
                                }
                              </p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="metrics" className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="bg-[#2a2a4e] border-gray-700">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-white">Total Runs</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold text-blue-400">{formatNumber(agent?.total_runs || 0)}</p>
                  </CardContent>
                </Card>
                
                <Card className="bg-[#2a2a4e] border-gray-700">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-white">Total Tokens</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold text-purple-400">{formatNumber(agent?.total_tokens || 0)}</p>
                  </CardContent>
                </Card>
                
                <Card className="bg-[#2a2a4e] border-gray-700">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-white">Total Cost</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold text-green-400">{formatCurrency(agent?.total_cost || 0)}</p>
                  </CardContent>
                </Card>
              </div>

              <Card className="bg-[#2a2a4e] border-gray-700">
                <CardHeader>
                  <CardTitle className="text-white">Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Created:</span>
                      <span className="text-white">{agent?.created_at ? formatDate(agent.created_at) : "N/A"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Last Active:</span>
                      <span className="text-white">
                        {agent?.last_active_at ? formatDate(agent.last_active_at) : "Never"}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}
      </SheetContent>
    </Sheet>
  );
}