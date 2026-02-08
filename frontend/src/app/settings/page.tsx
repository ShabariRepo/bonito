"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings,
  Shield,
  Bell,
  Key,
  Users,
  Upload,
  Trash2,
  AlertTriangle,
  Database,
  Plus,
  Eye,
  EyeOff,
  Copy,
  Check,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function SettingsPage() {
  const [orgName, setOrgName] = useState("Bonito Enterprise");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteInput, setDeleteInput] = useState("");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [notifications, setNotifications] = useState({
    deployments: true,
    costAlerts: true,
    modelUpdates: false,
    weeklyReports: true,
    slackWebhook: "",
    email: "team@bonito.ai",
  });
  const [security, setSecurity] = useState({
    twoFactor: true,
    sso: false,
    ipAllowlist: false,
  });
  const [retention, setRetention] = useState("90");

  const apiKeys = [
    { name: "Production Key", prefix: "bnt_prod_****a8f2", created: "2026-01-15", lastUsed: "2 hours ago", id: "1" },
    { name: "Development Key", prefix: "bnt_dev_****c4e1", created: "2026-01-20", lastUsed: "5 min ago", id: "2" },
    { name: "CI/CD Pipeline", prefix: "bnt_ci_****9b3d", created: "2026-02-01", lastUsed: "12 min ago", id: "3" },
  ];

  const copyKey = (id: string) => {
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const Toggle = ({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) => (
    <button
      onClick={onToggle}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        enabled ? "bg-violet-600" : "bg-secondary"
      }`}
    >
      <motion.span
        className="inline-block h-4 w-4 rounded-full bg-white"
        animate={{ x: enabled ? 24 : 4 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      />
    </button>
  );

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your platform configuration</p>
      </div>

      {/* Organization */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-violet-500" />
              Organization
            </CardTitle>
            <CardDescription>Manage your organization settings and branding</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0">
                <div className="h-20 w-20 rounded-xl bg-violet-600/10 border-2 border-dashed border-violet-500/30 flex flex-col items-center justify-center cursor-pointer hover:border-violet-500/50 transition-colors">
                  <Upload className="h-5 w-5 text-violet-500 mb-1" />
                  <span className="text-[10px] text-muted-foreground">Logo</span>
                </div>
              </div>
              <div className="flex-1 space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Organization Name</label>
                  <input
                    type="text"
                    value={orgName}
                    onChange={e => setOrgName(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Organization ID</label>
                  <input
                    type="text"
                    value="org_bnt_a1b2c3d4"
                    readOnly
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm opacity-50 cursor-not-allowed"
                  />
                </div>
              </div>
            </div>
            <button className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
              Save Changes
            </button>
          </CardContent>
        </Card>
      </motion.div>

      {/* API Keys */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-violet-500" />
              API Keys
            </CardTitle>
            <CardDescription>Manage API keys for programmatic access</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {apiKeys.map((k, i) => (
                <motion.div
                  key={k.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center justify-between rounded-lg border border-border p-4 hover:border-violet-500/20 transition-colors group"
                >
                  <div>
                    <p className="font-medium text-sm">{k.name}</p>
                    <p className="text-sm text-muted-foreground mt-0.5">
                      <code className="bg-secondary px-1.5 py-0.5 rounded text-xs">{k.prefix}</code>
                      <span className="ml-2">Created {k.created}</span>
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground">Last used {k.lastUsed}</span>
                    <button
                      onClick={() => copyKey(k.id)}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {copiedKey === k.id ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                    </button>
                    <button className="text-muted-foreground hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
            <button className="mt-4 inline-flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors">
              <Plus className="h-4 w-4" />
              Generate New Key
            </button>
          </CardContent>
        </Card>
      </motion.div>

      {/* Notifications */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5 text-violet-500" />
              Notifications
            </CardTitle>
            <CardDescription>Configure alert and notification preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-4">
              {[
                { label: "Deployment status changes", key: "deployments" as const },
                { label: "Cost threshold alerts", key: "costAlerts" as const },
                { label: "Model availability updates", key: "modelUpdates" as const },
                { label: "Weekly usage reports", key: "weeklyReports" as const },
              ].map(item => (
                <div key={item.key} className="flex items-center justify-between">
                  <span className="text-sm">{item.label}</span>
                  <Toggle
                    enabled={notifications[item.key]}
                    onToggle={() => setNotifications(n => ({ ...n, [item.key]: !n[item.key] }))}
                  />
                </div>
              ))}
            </div>
            <div className="border-t border-border pt-4 space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Email notifications</label>
                <input
                  type="email"
                  value={notifications.email}
                  onChange={e => setNotifications(n => ({ ...n, email: e.target.value }))}
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Slack webhook URL</label>
                <input
                  type="url"
                  value={notifications.slackWebhook}
                  onChange={e => setNotifications(n => ({ ...n, slackWebhook: e.target.value }))}
                  placeholder="https://hooks.slack.com/services/..."
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Security */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-violet-500" />
              Security
            </CardTitle>
            <CardDescription>Configure authentication and access controls</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { label: "Two-factor authentication", key: "twoFactor" as const },
                { label: "SSO / SAML integration", key: "sso" as const },
                { label: "IP allowlist", key: "ipAllowlist" as const },
              ].map(item => (
                <div key={item.key} className="flex items-center justify-between">
                  <span className="text-sm">{item.label}</span>
                  <Toggle
                    enabled={security[item.key]}
                    onToggle={() => setSecurity(s => ({ ...s, [item.key]: !s[item.key] }))}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Data Retention */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-violet-500" />
              Data Retention
            </CardTitle>
            <CardDescription>Configure how long data is stored</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Log retention period</label>
              <div className="flex gap-2 flex-wrap">
                {["30", "60", "90", "180", "365"].map(d => (
                  <button
                    key={d}
                    onClick={() => setRetention(d)}
                    className={`rounded-full px-3 py-1.5 text-sm font-medium border transition-all ${
                      retention === d
                        ? "border-violet-500/50 bg-violet-500/10 text-foreground"
                        : "border-border text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {d} days
                  </button>
                ))}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Logs older than {retention} days will be automatically archived and deleted.
            </p>
          </CardContent>
        </Card>
      </motion.div>

      {/* Danger Zone */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Card className="border-red-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-500">
              <AlertTriangle className="h-5 w-5" />
              Danger Zone
            </CardTitle>
            <CardDescription>Irreversible actions — proceed with caution</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between rounded-lg border border-red-500/20 bg-red-500/5 p-4">
              <div>
                <p className="font-medium text-sm">Delete Organization</p>
                <p className="text-xs text-muted-foreground mt-0.5">Permanently delete this organization and all its data</p>
              </div>
              <button
                onClick={() => setShowDeleteConfirm(!showDeleteConfirm)}
                className="rounded-md border border-red-500/50 px-4 py-2 text-sm font-medium text-red-500 hover:bg-red-500/10 transition-colors"
              >
                Delete Organization
              </button>
            </div>

            <AnimatePresence>
              {showDeleteConfirm && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/5 p-4 space-y-3">
                    <p className="text-sm text-red-400">
                      Type <strong>delete my organization</strong> to confirm:
                    </p>
                    <input
                      type="text"
                      value={deleteInput}
                      onChange={e => setDeleteInput(e.target.value)}
                      placeholder="delete my organization"
                      className="w-full rounded-md border border-red-500/30 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500/50"
                    />
                    <div className="flex gap-2">
                      <button
                        disabled={deleteInput !== "delete my organization"}
                        className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        Permanently Delete
                      </button>
                      <button
                        onClick={() => { setShowDeleteConfirm(false); setDeleteInput(""); }}
                        className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
