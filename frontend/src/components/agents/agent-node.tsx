import { memo } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { Bot, DollarSign, Activity, BookOpen, Wrench } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface AgentNodeData {
  id: string;
  name: string;
  description?: string;
  status: string;
  model_id: string;
  knowledge_base_count: number;
  total_runs: number;
  total_cost: number;
  last_active_at?: string;
}

export const AgentNode = memo(({ data, selected }: { data: AgentNodeData; selected?: boolean }) => {
  const getStatusIndicator = (status: string) => {
    switch (status) {
      case "active":
        return <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />;
      case "paused":
        return <div className="w-2 h-2 rounded-full bg-yellow-500" />;
      case "disabled":
        return <div className="w-2 h-2 rounded-full bg-red-500" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-gray-500" />;
    }
  };

  const formatCurrency = (amount: number) => {
    if (amount < 0.01) return "$0.00";
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatTimeAgo = (dateString?: string) => {
    if (!dateString) return "Never";
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    
    if (diffMinutes < 1) return "Now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}h ago`;
    return `${Math.floor(diffMinutes / 1440)}d ago`;
  };

  const getModelBadge = (modelId: string) => {
    const modelColors: Record<string, string> = {
      "auto": "bg-blue-500/10 text-blue-400 border-blue-500/30",
      "gpt-4o": "bg-purple-500/10 text-purple-400 border-purple-500/30",
      "gpt-4": "bg-purple-500/10 text-purple-400 border-purple-500/30",
      "claude-3-sonnet": "bg-orange-500/10 text-orange-400 border-orange-500/30",
      "claude-3-haiku": "bg-orange-500/10 text-orange-400 border-orange-500/30",
    };
    
    return (
      <Badge 
        variant="outline" 
        className={`text-xs ${modelColors[modelId] || "bg-gray-500/10 text-gray-400 border-gray-500/30"}`}
      >
        <Bot className="w-3 h-3 mr-1" />
        {modelId}
      </Badge>
    );
  };

  return (
    <div className="group">
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 !bg-cyan-500 !border-2 !border-cyan-400"
      />
      
      <Card 
        className={`
          w-80 bg-[#1a1a2e] border-2 transition-all duration-200 hover:shadow-lg hover:shadow-cyan-500/20
          ${selected 
            ? "border-cyan-500 shadow-lg shadow-cyan-500/30" 
            : "border-gray-700 hover:border-cyan-500/50"
          }
        `}
      >
        <CardContent className="p-4">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center space-x-2 flex-1">
              {getStatusIndicator(data.status)}
              <h3 className="font-semibold text-white text-sm truncate">
                {data.name}
              </h3>
            </div>
            <Bot className="w-4 h-4 text-cyan-500 flex-shrink-0" />
          </div>

          {/* Description */}
          {data.description && (
            <p className="text-xs text-gray-400 mb-3 line-clamp-2">
              {data.description}
            </p>
          )}

          {/* Model Badge */}
          <div className="mb-3">
            {getModelBadge(data.model_id)}
          </div>

          {/* Stats */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center text-gray-400">
                <BookOpen className="w-3 h-3 mr-1" />
                {data.knowledge_base_count} KBs
              </div>
              <div className="flex items-center text-gray-400">
                <Wrench className="w-3 h-3 mr-1" />
                4 Tools
              </div>
            </div>
            
            <div className="border-t border-gray-700 pt-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center text-green-400">
                  <DollarSign className="w-3 h-3 mr-1" />
                  {formatCurrency(data.total_cost)} spent
                </div>
                <div className="flex items-center text-gray-400">
                  <Activity className="w-3 h-3 mr-1" />
                  {data.total_runs} runs
                </div>
              </div>
              
              <div className="mt-1 text-xs text-gray-500 text-center">
                {formatTimeAgo(data.last_active_at)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-cyan-500 !border-2 !border-cyan-400"
      />
    </div>
  );
});