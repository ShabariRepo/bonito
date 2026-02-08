import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Box, Sparkles, MessageSquare, Image, Code } from "lucide-react";

const models = [
  {
    name: "GPT-4 Turbo",
    provider: "Azure OpenAI",
    id: "gpt-4-turbo-preview",
    capabilities: ["chat", "code", "reasoning"],
    pricing: "$10 / 1M input tokens",
    status: "available",
  },
  {
    name: "Claude 3 Opus",
    provider: "AWS Bedrock",
    id: "anthropic.claude-3-opus",
    capabilities: ["chat", "code", "reasoning", "vision"],
    pricing: "$15 / 1M input tokens",
    status: "available",
  },
  {
    name: "Gemini Pro",
    provider: "GCP Vertex AI",
    id: "gemini-pro",
    capabilities: ["chat", "code", "vision"],
    pricing: "$7 / 1M input tokens",
    status: "available",
  },
  {
    name: "Mistral Large",
    provider: "AWS Bedrock",
    id: "mistral.mistral-large",
    capabilities: ["chat", "code"],
    pricing: "$8 / 1M input tokens",
    status: "available",
  },
  {
    name: "Llama 3 70B",
    provider: "AWS Bedrock",
    id: "meta.llama3-70b",
    capabilities: ["chat", "code"],
    pricing: "$2.75 / 1M input tokens",
    status: "available",
  },
  {
    name: "DALL·E 3",
    provider: "Azure OpenAI",
    id: "dall-e-3",
    capabilities: ["image-generation"],
    pricing: "$0.04 / image",
    status: "available",
  },
];

const capabilityIcon = (cap: string) => {
  switch (cap) {
    case "chat": return <MessageSquare className="h-3 w-3" />;
    case "code": return <Code className="h-3 w-3" />;
    case "vision": return <Image className="h-3 w-3" />;
    default: return <Sparkles className="h-3 w-3" />;
  }
};

export default function ModelsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Model Catalog</h1>
        <p className="text-muted-foreground mt-1">Browse and manage available AI models</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {models.map((model) => (
          <Card key={model.id} className="hover:border-violet-500/50 transition-colors cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                    <Box className="h-5 w-5 text-violet-400" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{model.name}</h3>
                    <p className="text-sm text-muted-foreground">{model.provider}</p>
                  </div>
                </div>
                <Badge variant="success">{model.status}</Badge>
              </div>

              <div className="mt-4 flex flex-wrap gap-1.5">
                {model.capabilities.map((cap) => (
                  <Badge key={cap} variant="secondary" className="gap-1">
                    {capabilityIcon(cap)}
                    {cap}
                  </Badge>
                ))}
              </div>

              <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
                <code className="text-xs text-muted-foreground">{model.id}</code>
                <span className="text-xs text-muted-foreground">{model.pricing}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
