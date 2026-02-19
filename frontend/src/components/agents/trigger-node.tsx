import { memo } from "react";
import { Handle, Position, NodeProps } from "@xyflow/react";
import { Webhook, Calendar, Zap, Play, Settings } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface TriggerNodeData {
  id: string;
  trigger_type: string;
  config: any;
  enabled: boolean;
  agent_name: string;
  last_fired_at?: string;
}

export const TriggerNode = memo(({ data, selected }: NodeProps<TriggerNodeData>) => {
  const getTriggerIcon = (type: string) => {
    switch (type) {
      case "webhook":
        return <Webhook className="w-4 h-4" />;
      case "schedule":
        return <Calendar className="w-4 h-4" />;
      case "event":
        return <Zap className="w-4 h-4" />;
      case "manual":
        return <Play className="w-4 h-4" />;
      case "api":
        return <Settings className="w-4 h-4" />;
      default:
        return <Zap className="w-4 h-4" />;
    }
  };

  const getTriggerColor = (type: string) => {
    switch (type) {
      case "webhook":
        return "text-blue-400";
      case "schedule":
        return "text-green-400";
      case "event":
        return "text-purple-400";
      case "manual":
        return "text-orange-400";
      case "api":
        return "text-cyan-400";
      default:
        return "text-yellow-400";
    }
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

  const getTriggerDescription = (type: string, config: any) => {
    switch (type) {
      case "webhook":
        return "HTTP webhook trigger";
      case "schedule":
        return config.cron || "Scheduled trigger";
      case "event":
        return "Event-driven trigger";
      case "manual":
        return "Manual execution";
      case "api":
        return "API endpoint trigger";
      default:
        return "Custom trigger";
    }
  };

  return (
    <div className="group">
      <Card 
        className={`
          w-48 bg-[#2a2a4e] border-2 transition-all duration-200 hover:shadow-lg hover:shadow-yellow-500/20
          ${selected 
            ? "border-yellow-500 shadow-lg shadow-yellow-500/30" 
            : "border-gray-600 hover:border-yellow-500/50"
          }
        `}
      >
        <CardContent className="p-3">
          {/* Header */}
          <div className="flex items-center space-x-2 mb-2">
            <div className={`${getTriggerColor(data.trigger_type)}`}>
              {getTriggerIcon(data.trigger_type)}
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <Badge 
                  variant="outline" 
                  className={`text-xs ${
                    data.enabled 
                      ? "bg-green-500/10 text-green-400 border-green-500/30" 
                      : "bg-red-500/10 text-red-400 border-red-500/30"
                  }`}
                >
                  {data.trigger_type}
                </Badge>
                <div className={`w-2 h-2 rounded-full ${
                  data.enabled ? "bg-green-500" : "bg-red-500"
                }`} />
              </div>
            </div>
          </div>

          {/* Description */}
          <p className="text-xs text-gray-300 mb-2">
            {getTriggerDescription(data.trigger_type, data.config)}
          </p>

          {/* Target Agent */}
          <div className="text-xs text-gray-400 mb-2">
            → {data.agent_name}
          </div>

          {/* Last Fired */}
          <div className="text-xs text-gray-500 text-center border-t border-gray-600 pt-2">
            Last fired: {formatTimeAgo(data.last_fired_at)}
          </div>
        </CardContent>
      </Card>

      {/* Output Handle Only */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 !bg-yellow-500 !border-2 !border-yellow-400"
      />
    </div>
  );
});