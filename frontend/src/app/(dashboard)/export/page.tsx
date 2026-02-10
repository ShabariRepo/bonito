"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Download,
  Copy,
  Check,
  FileCode2,
  Settings2,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiRequest } from "@/lib/auth";

const formats = [
  {
    id: "terraform",
    name: "Terraform",
    ext: ".tf",
    logo: "HCL",
    color: "violet",
    description: "HashiCorp Configuration Language",
  },
  {
    id: "pulumi",
    name: "Pulumi",
    ext: ".ts",
    logo: "TS",
    color: "blue",
    description: "TypeScript infrastructure code",
  },
];

const providers = [
  { id: "aws", name: "AWS Bedrock", color: "bg-amber-500" },
  { id: "azure", name: "Azure AI", color: "bg-blue-500" },
  { id: "gcp", name: "GCP Vertex", color: "bg-emerald-500" },
];

export default function ExportPage() {
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [selectedProviders, setSelectedProviders] = useState<string[]>(["aws", "azure", "gcp"]);
  const [namingPrefix, setNamingPrefix] = useState("bonito");
  const [code, setCode] = useState("");
  const [filename, setFilename] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const toggleProvider = (id: string) => {
    setSelectedProviders(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const generate = async (format: string) => {
    setSelectedFormat(format);
    setLoading(true);
    setCode("");
    try {
      const res = await apiRequest(`/api/export/${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ providers: selectedProviders, naming_prefix: namingPrefix }),
      });
      if (res.ok) {
        const data = await res.json();
        setCode(data.code);
        setFilename(data.filename);
      }
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadFile = () => {
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Simple syntax coloring via spans
  const highlightCode = (text: string) => {
    if (!text) return null;
    return text.split("\n").map((line, i) => {
      let html = line
        .replace(/^(#|\/\/)(.*)$/gm, '<span class="text-muted-foreground">$&</span>')
        .replace(/"([^"]*)"/g, '<span class="text-emerald-400">"$1"</span>')
        .replace(/\b(resource|variable|provider|output|terraform|import|const|new|export)\b/g, '<span class="text-violet-400">$1</span>')
        .replace(/\b(true|false|null)\b/g, '<span class="text-amber-400">$1</span>');
      return (
        <div key={i} className="table-row">
          <span className="table-cell pr-4 text-muted-foreground/40 select-none text-right w-8">{i + 1}</span>
          <span className="table-cell" dangerouslySetInnerHTML={{ __html: html }} />
        </div>
      );
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Export</h1>
        <p className="text-muted-foreground mt-1">Generate Infrastructure as Code for your AI platform</p>
      </div>

      {/* Config */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-violet-500" />
            Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">Providers to include</label>
            <div className="flex gap-2 flex-wrap">
              {providers.map(p => (
                <button
                  key={p.id}
                  onClick={() => toggleProvider(p.id)}
                  className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium border transition-all ${
                    selectedProviders.includes(p.id)
                      ? "border-violet-500/50 bg-violet-500/10 text-foreground"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <div className={`h-2 w-2 rounded-full ${p.color}`} />
                  {p.name}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">Naming prefix</label>
            <input
              type="text"
              value={namingPrefix}
              onChange={e => setNamingPrefix(e.target.value)}
              className="w-full max-w-xs rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            />
          </div>
        </CardContent>
      </Card>

      {/* Format Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {formats.map((f, i) => (
          <motion.div
            key={f.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
          >
            <Card
              className={`cursor-pointer hover:scale-[1.02] transition-all ${
                selectedFormat === f.id ? "border-violet-500/50 bg-violet-500/5" : "hover:border-violet-500/20"
              }`}
              onClick={() => generate(f.id)}
            >
              <CardContent className="p-6 flex items-center gap-4">
                <div className={`h-12 w-12 rounded-lg bg-${f.color}-500/10 border border-${f.color}-500/20 flex items-center justify-center font-mono font-bold text-${f.color}-400`}>
                  {f.logo}
                </div>
                <div className="flex-1">
                  <p className="font-semibold">{f.name}</p>
                  <p className="text-sm text-muted-foreground">{f.description}</p>
                </div>
                <FileCode2 className="h-5 w-5 text-muted-foreground" />
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Code Preview */}
      <AnimatePresence>
        {(loading || code) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileCode2 className="h-4 w-4 text-violet-500" />
                  {filename || "Generated Code"}
                </CardTitle>
                {code && (
                  <div className="flex gap-2">
                    <button
                      onClick={copyToClipboard}
                      className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent transition-colors"
                    >
                      <AnimatePresence mode="wait">
                        {copied ? (
                          <motion.div key="check" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                            <Check className="h-3.5 w-3.5 text-emerald-500" />
                          </motion.div>
                        ) : (
                          <motion.div key="copy" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
                            <Copy className="h-3.5 w-3.5" />
                          </motion.div>
                        )}
                      </AnimatePresence>
                      {copied ? "Copied!" : "Copy"}
                    </button>
                    <button
                      onClick={downloadFile}
                      className="inline-flex items-center gap-1.5 rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
                    >
                      <Download className="h-3.5 w-3.5" />
                      Download
                    </button>
                  </div>
                )}
              </CardHeader>
              <CardContent>
                {loading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
                    <span className="ml-2 text-sm text-muted-foreground">Generating...</span>
                  </div>
                ) : (
                  <div className="rounded-lg bg-[#0d1117] border border-border p-4 overflow-x-auto max-h-[500px] overflow-y-auto">
                    <pre className="text-sm font-mono leading-relaxed table w-full">
                      {highlightCode(code)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Empty state */}
      {!code && !loading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <FileCode2 className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
          <p className="text-lg font-medium text-muted-foreground">Select a format to generate your IaC</p>
          <p className="text-sm text-muted-foreground/70 mt-1">Choose Terraform or Pulumi above to get started</p>
        </motion.div>
      )}
    </div>
  );
}
