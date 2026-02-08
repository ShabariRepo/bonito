import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Rocket, MoreVertical, Globe, Cpu, Clock } from "lucide-react";

const deployments = [
  {
    name: "GPT-4 Turbo — Production",
    model: "gpt-4-turbo-preview",
    provider: "Azure OpenAI",
    region: "East US",
    status: "active",
    replicas: 3,
    uptime: "99.97%",
    created: "2026-01-15",
  },
  {
    name: "Claude 3 — Chatbot",
    model: "anthropic.claude-3-opus",
    provider: "AWS Bedrock",
    region: "us-east-1",
    status: "active",
    replicas: 2,
    uptime: "99.99%",
    created: "2026-01-20",
  },
  {
    name: "Gemini Pro — Staging",
    model: "gemini-pro",
    provider: "GCP Vertex AI",
    region: "us-central1",
    status: "deploying",
    replicas: 1,
    uptime: "—",
    created: "2026-02-07",
  },
  {
    name: "Mistral — Internal Tools",
    model: "mistral.mistral-large",
    provider: "AWS Bedrock",
    region: "eu-west-1",
    status: "active",
    replicas: 1,
    uptime: "99.95%",
    created: "2026-01-28",
  },
  {
    name: "Llama 3 — Dev/Test",
    model: "meta.llama3-70b",
    provider: "AWS Bedrock",
    region: "us-west-2",
    status: "stopped",
    replicas: 0,
    uptime: "—",
    created: "2026-02-01",
  },
];

const statusVariant = (s: string) => {
  switch (s) {
    case "active": return "success" as const;
    case "deploying": return "warning" as const;
    case "stopped": return "destructive" as const;
    default: return "secondary" as const;
  }
};

export default function DeploymentsPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Deployments</h1>
          <p className="text-muted-foreground mt-1">Manage your model deployments</p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
          <Rocket className="h-4 w-4" />
          New Deployment
        </button>
      </div>

      <div className="space-y-3">
        {deployments.map((d, i) => (
          <Card key={i} className="hover:border-violet-500/30 transition-colors">
            <CardContent className="flex items-center justify-between py-5">
              <div className="flex items-center gap-4">
                <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-accent">
                  <Rocket className="h-5 w-5 text-violet-400" />
                </div>
                <div>
                  <p className="font-medium">{d.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {d.model} · {d.provider}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-6">
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Globe className="h-3.5 w-3.5" />
                  {d.region}
                </div>
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Cpu className="h-3.5 w-3.5" />
                  {d.replicas} replica{d.replicas !== 1 ? "s" : ""}
                </div>
                <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  {d.uptime}
                </div>
                <Badge variant={statusVariant(d.status)}>{d.status}</Badge>
                <button className="text-muted-foreground hover:text-foreground">
                  <MoreVertical className="h-4 w-4" />
                </button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
