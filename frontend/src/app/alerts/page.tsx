"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  Bell,
  Plus,
  Trash2,
  DollarSign,
  Shield,
  AlertTriangle,
  Mail,
  Globe,
  Smartphone,
  X,
} from "lucide-react";
import { API_URL } from "@/lib/utils";

const TYPE_OPTIONS = [
  { value: "budget_threshold", label: "Budget Threshold", icon: DollarSign, description: "Alert when spending exceeds a percentage of budget" },
  { value: "compliance_violation", label: "Compliance Violation", icon: Shield, description: "Alert on policy violations" },
  { value: "model_deprecation", label: "Model Deprecation", icon: AlertTriangle, description: "Alert when a model is being deprecated" },
];

const CHANNEL_OPTIONS = [
  { value: "in_app", label: "In-App", icon: Smartphone },
  { value: "email", label: "Email", icon: Mail },
  { value: "webhook", label: "Webhook", icon: Globe },
];

export default function AlertsPage() {
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newRule, setNewRule] = useState({ type: "budget_threshold", threshold: 80, channel: "in_app", enabled: true });

  async function loadRules() {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/alert-rules/`);
      setRules(await res.json());
    } catch (e) {
      console.error("Failed to load alert rules", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRules(); }, []);

  async function createRule() {
    try {
      const res = await fetch(`${API_URL}/api/alert-rules/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newRule),
      });
      if (res.ok) {
        setShowCreate(false);
        setNewRule({ type: "budget_threshold", threshold: 80, channel: "in_app", enabled: true });
        loadRules();
      }
    } catch (e) {
      console.error("Failed to create rule", e);
    }
  }

  async function toggleRule(id: string, enabled: boolean) {
    try {
      await fetch(`${API_URL}/api/alert-rules/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !enabled }),
      });
      setRules((prev) => prev.map((r) => (r.id === id ? { ...r, enabled: !enabled } : r)));
    } catch (e) {
      console.error("Failed to toggle rule", e);
    }
  }

  async function deleteRule(id: string) {
    try {
      await fetch(`${API_URL}/api/alert-rules/${id}`, { method: "DELETE" });
      setRules((prev) => prev.filter((r) => r.id !== id));
    } catch (e) {
      console.error("Failed to delete rule", e);
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Alert Rules"
        description="Configure automated alerts for cost, compliance, and model changes"
        actions={
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Rule
          </motion.button>
        }
      />

      {/* Create modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={() => setShowCreate(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-lg border border-border bg-card p-6 shadow-xl"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold">Create Alert Rule</h2>
                <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-2 block">Alert Type</label>
                  <div className="space-y-2">
                    {TYPE_OPTIONS.map((t) => (
                      <button
                        key={t.value}
                        onClick={() => setNewRule({ ...newRule, type: t.value })}
                        className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-colors text-left ${
                          newRule.type === t.value
                            ? "border-violet-500 bg-violet-500/10"
                            : "border-border hover:border-violet-500/30"
                        }`}
                      >
                        <t.icon className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">{t.label}</p>
                          <p className="text-xs text-muted-foreground">{t.description}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {newRule.type === "budget_threshold" && (
                  <div>
                    <label className="text-sm font-medium text-muted-foreground mb-2 block">
                      Threshold (% of budget)
                    </label>
                    <input
                      type="number"
                      value={newRule.threshold}
                      onChange={(e) => setNewRule({ ...newRule, threshold: Number(e.target.value) })}
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                      min={1}
                      max={100}
                    />
                  </div>
                )}

                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-2 block">Channel</label>
                  <div className="flex gap-2">
                    {CHANNEL_OPTIONS.map((c) => (
                      <button
                        key={c.value}
                        onClick={() => setNewRule({ ...newRule, channel: c.value })}
                        className={`flex items-center gap-2 px-3 py-2 rounded-md border text-sm transition-colors ${
                          newRule.channel === c.value
                            ? "border-violet-500 bg-violet-500/10"
                            : "border-border hover:border-violet-500/30"
                        }`}
                      >
                        <c.icon className="h-4 w-4" />
                        {c.label}
                      </button>
                    ))}
                  </div>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={createRule}
                  className="w-full rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors mt-4"
                >
                  Create Rule
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Rules list */}
      <div className="space-y-3">
        {rules.map((rule, i) => {
          const typeConfig = TYPE_OPTIONS.find((t) => t.value === rule.type) || TYPE_OPTIONS[0];
          const channelConfig = CHANNEL_OPTIONS.find((c) => c.value === rule.channel) || CHANNEL_OPTIONS[0];
          const Icon = typeConfig.icon;
          const ChannelIcon = channelConfig.icon;

          return (
            <motion.div
              key={rule.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className={`transition-colors ${!rule.enabled ? "opacity-60" : ""}`}>
                <CardContent className="flex items-center gap-4 py-4">
                  <div className="p-2 rounded-lg bg-accent/50">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-medium">{typeConfig.label}</h3>
                      {rule.threshold && (
                        <Badge variant="secondary" className="text-[10px]">
                          {rule.threshold}%
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <ChannelIcon className="h-3 w-3 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground">{channelConfig.label}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleRule(rule.id, rule.enabled)}
                      className={`relative w-10 h-5 rounded-full transition-colors ${
                        rule.enabled ? "bg-violet-600" : "bg-accent"
                      }`}
                    >
                      <motion.div
                        className="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow"
                        animate={{ left: rule.enabled ? 22 : 2 }}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      />
                    </button>
                    <motion.button
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => deleteRule(rule.id)}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </motion.button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}

        {rules.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Bell className="h-8 w-8 mx-auto mb-3 opacity-50" />
            <p>No alert rules configured</p>
            <p className="text-sm mt-1">Create a rule to get started</p>
          </div>
        )}
      </div>
    </div>
  );
}
