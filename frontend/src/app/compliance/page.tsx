"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Scan,
  Download,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { API_URL } from "@/lib/utils";

interface Framework {
  name: string;
  display_name: string;
  description: string;
  total_checks: number;
  passing_checks: number;
  coverage_pct: number;
}

interface Check {
  id: string;
  check_name: string;
  category: string;
  status: string;
  frameworks: string[];
  details: Record<string, string>;
  last_scanned: string;
}

interface Status {
  overall_score: number;
  total_checks: number;
  passing: number;
  failing: number;
  warnings: number;
  frameworks: Framework[];
  last_scan: string | null;
}

const statusIcon = (s: string) => {
  switch (s) {
    case "pass": return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    case "fail": return <XCircle className="h-4 w-4 text-red-500" />;
    case "warning": return <AlertTriangle className="h-4 w-4 text-amber-500" />;
    default: return <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />;
  }
};

const statusBadge = (s: string) => {
  switch (s) {
    case "pass": return "success" as const;
    case "fail": return "destructive" as const;
    case "warning": return "warning" as const;
    default: return "secondary" as const;
  }
};

function ScoreRing({ score, size = 160 }: { score: number; size?: number }) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? "text-emerald-500" : score >= 60 ? "text-amber-500" : "text-red-500";
  const strokeColor = score >= 80 ? "#10b981" : score >= 60 ? "#f59e0b" : "#ef4444";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="currentColor" strokeWidth={strokeWidth} className="text-secondary" />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className={`text-4xl font-bold ${color}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {score}
        </motion.span>
        <span className="text-xs text-muted-foreground">/ 100</span>
      </div>
    </div>
  );
}

export default function CompliancePage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [checks, setChecks] = useState<Check[]>([]);
  const [scanning, setScanning] = useState(false);
  const [expandedCheck, setExpandedCheck] = useState<string | null>(null);

  const loadData = () => {
    fetch(`${API_URL}/api/compliance/status`).then(r => r.json()).then(setStatus).catch(() => {});
    fetch(`${API_URL}/api/compliance/checks`).then(r => r.json()).then(setChecks).catch(() => {});
  };

  useEffect(() => { loadData(); }, []);

  const runScan = async () => {
    setScanning(true);
    try {
      await fetch(`${API_URL}/api/compliance/scan`, { method: "POST" });
      await new Promise(r => setTimeout(r, 2000));
      loadData();
    } finally {
      setScanning(false);
    }
  };

  const exportReport = async () => {
    const res = await fetch(`${API_URL}/api/compliance/report`);
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "compliance-report.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const frameworkColors: Record<string, string> = {
    SOC2: "violet",
    HIPAA: "blue",
    GDPR: "emerald",
    ISO27001: "amber",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Compliance</h1>
          <p className="text-muted-foreground mt-1">Policy engine & compliance automation</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={exportReport}
            className="inline-flex items-center gap-2 rounded-md border border-border px-4 py-2.5 text-sm font-medium hover:bg-accent transition-colors"
          >
            <Download className="h-4 w-4" />
            Export Report
          </button>
          <button
            onClick={runScan}
            disabled={scanning}
            className="relative inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors disabled:opacity-80"
          >
            {scanning && (
              <motion.div
                className="absolute inset-0 rounded-md bg-violet-500"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
            )}
            <span className="relative flex items-center gap-2">
              {scanning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Scan className="h-4 w-4" />}
              {scanning ? "Scanning..." : "Run Scan"}
            </span>
          </button>
        </div>
      </div>

      {/* Score Ring */}
      {status && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-center"
        >
          <Card className="w-full max-w-sm">
            <CardContent className="flex flex-col items-center py-8">
              <ScoreRing score={status.overall_score} />
              <p className="text-sm font-medium mt-4">Compliance Score</p>
              <div className="flex gap-4 mt-3 text-sm">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  {status.passing} passing
                </span>
                <span className="flex items-center gap-1.5">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                  {status.warnings} warnings
                </span>
                <span className="flex items-center gap-1.5">
                  <XCircle className="h-3.5 w-3.5 text-red-500" />
                  {status.failing} failing
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Framework Cards */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {status.frameworks.map((fw, i) => {
            const c = frameworkColors[fw.name] || "violet";
            return (
              <motion.div
                key={fw.name}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
              >
                <Card className={`bg-${c}-500/5 border-${c}-500/20`}>
                  <CardContent className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <p className="font-semibold">{fw.display_name}</p>
                      <span className={`text-sm font-bold text-${c}-400`}>{fw.coverage_pct}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${fw.coverage_pct}%` }}
                        transition={{ duration: 1, delay: 0.3 + i * 0.1 }}
                        className={`h-full rounded-full ${
                          fw.coverage_pct >= 80 ? "bg-emerald-500" : fw.coverage_pct >= 60 ? "bg-amber-500" : "bg-red-500"
                        }`}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-2">
                      {fw.passing_checks}/{fw.total_checks} checks passing
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Checks List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-violet-500" />
            Compliance Checks
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {checks.map((check, i) => (
              <motion.div
                key={check.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <button
                  onClick={() => setExpandedCheck(expandedCheck === check.id ? null : check.id)}
                  className="w-full text-left rounded-lg border border-border p-4 hover:border-violet-500/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.2 + i * 0.03, type: "spring" }}
                    >
                      {statusIcon(check.status)}
                    </motion.div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">{check.check_name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant={statusBadge(check.status)} className="text-xs capitalize">
                          {check.status}
                        </Badge>
                        {check.frameworks.map(fw => (
                          <span key={fw} className="text-xs text-muted-foreground">{fw}</span>
                        ))}
                      </div>
                    </div>
                    <motion.div
                      animate={{ rotate: expandedCheck === check.id ? 180 : 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    </motion.div>
                  </div>
                </button>

                <AnimatePresence>
                  {expandedCheck === check.id && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-4 pt-2 ml-7 space-y-2">
                        {Object.entries(check.details).map(([key, value]) => (
                          <div key={key}>
                            <span className="text-xs font-medium text-muted-foreground capitalize">{key}: </span>
                            <span className="text-sm">{value}</span>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
