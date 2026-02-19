"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield,
  AlertTriangle,
  Check,
  Copy,
  Loader2,
  ExternalLink,
  Info,
  ChevronDown,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/auth";
import { useAuth } from "@/components/auth/auth-context";
import { API_URL } from "@/lib/utils";

// ---------- Types ----------

interface SSOConfig {
  id: string;
  org_id: string;
  provider_type: string;
  idp_metadata_url: string | null;
  idp_sso_url: string | null;
  idp_entity_id: string | null;
  idp_certificate: string | null;
  sp_entity_id: string | null;
  sp_acs_url: string | null;
  attribute_mapping: Record<string, string> | null;
  role_mapping: Record<string, string> | null;
  enabled: boolean;
  enforced: boolean;
  breakglass_user_id: string | null;
}

interface OrgAdmin {
  id: string;
  email: string;
  name: string;
}

interface TestResult {
  status: string;
  message: string;
  test_login_url?: string;
  sp_metadata_url?: string;
  sp_entity_id?: string;
  sp_acs_url?: string;
}

// ---------- Provider presets ----------

const PROVIDERS = [
  { value: "okta", label: "Okta", description: "Okta Identity Provider" },
  { value: "azure_ad", label: "Azure AD", description: "Microsoft Entra ID (Azure AD)" },
  { value: "google", label: "Google Workspace", description: "Google SAML" },
  { value: "custom", label: "Custom SAML", description: "Any SAML 2.0 Identity Provider" },
];

const PROVIDER_HELP: Record<string, { metadataHint: string; fields: string[] }> = {
  okta: {
    metadataHint: "Find this in your Okta Admin → Applications → Your App → Sign On → Metadata URL",
    fields: ["metadata_url", "sso_url", "entity_id", "certificate"],
  },
  azure_ad: {
    metadataHint: "Azure Portal → Enterprise Applications → Your App → Single sign-on → Federation Metadata URL",
    fields: ["metadata_url", "sso_url", "entity_id", "certificate"],
  },
  google: {
    metadataHint: "Google Admin → Apps → Web and mobile apps → Your App → Download metadata",
    fields: ["sso_url", "entity_id", "certificate"],
  },
  custom: {
    metadataHint: "Enter the IdP metadata URL or configure fields manually",
    fields: ["metadata_url", "sso_url", "entity_id", "certificate"],
  },
};

// ---------- Component ----------

export default function SecuritySettingsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [orgAdmins, setOrgAdmins] = useState<OrgAdmin[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // SSO Config form state
  const [config, setConfig] = useState<SSOConfig | null>(null);
  const [form, setForm] = useState({
    provider_type: "custom",
    idp_metadata_url: "",
    idp_sso_url: "",
    idp_entity_id: "",
    idp_certificate: "",
    attribute_mapping: null as Record<string, string> | null,
    role_mapping: null as Record<string, string> | null,
    breakglass_user_id: "",
  });

  // Load existing config
  const fetchConfig = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiRequest("/api/sso/config");
      if (res.ok) {
        const data: SSOConfig = await res.json();
        setConfig(data);
        setForm({
          provider_type: data.provider_type || "custom",
          idp_metadata_url: data.idp_metadata_url || "",
          idp_sso_url: data.idp_sso_url || "",
          idp_entity_id: data.idp_entity_id || "",
          idp_certificate: data.idp_certificate || "",
          attribute_mapping: data.attribute_mapping,
          role_mapping: data.role_mapping,
          breakglass_user_id: data.breakglass_user_id || "",
        });
      }
    } catch {
      // Config doesn't exist yet — that's fine
    } finally {
      setLoading(false);
    }
  }, []);

  // Load org admins for break-glass selector
  const fetchAdmins = useCallback(async () => {
    try {
      const res = await apiRequest("/api/users");
      if (res.ok) {
        const users = await res.json();
        setOrgAdmins(
          users
            .filter((u: { role: string }) => u.role === "admin")
            .map((u: { id: string; email: string; name: string }) => ({
              id: u.id,
              email: u.email,
              name: u.name,
            }))
        );
      }
    } catch {}
  }, []);

  useEffect(() => {
    fetchConfig();
    fetchAdmins();
  }, [fetchConfig, fetchAdmins]);

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
    setTestResult(null);
  };

  const handleSave = async () => {
    clearMessages();
    setSaving(true);
    try {
      const res = await apiRequest("/api/sso/config", {
        method: "PUT",
        body: JSON.stringify({
          provider_type: form.provider_type,
          idp_metadata_url: form.idp_metadata_url || null,
          idp_sso_url: form.idp_sso_url || null,
          idp_entity_id: form.idp_entity_id || null,
          idp_certificate: form.idp_certificate || null,
          attribute_mapping: form.attribute_mapping,
          role_mapping: form.role_mapping,
          breakglass_user_id: form.breakglass_user_id || null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        setSuccess("SSO configuration saved successfully.");
      } else {
        const err = await res.json().catch(() => ({}));
        setError(err.detail || "Failed to save SSO configuration.");
      }
    } catch {
      setError("Failed to save SSO configuration.");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    clearMessages();
    setTesting(true);
    try {
      const res = await apiRequest("/api/sso/test", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setTestResult(data);
      } else {
        setError(typeof data.detail === "string" ? data.detail : data.detail?.message || "Test failed.");
      }
    } catch {
      setError("Failed to test SSO configuration.");
    } finally {
      setTesting(false);
    }
  };

  const handleToggleSSO = async (enable: boolean) => {
    clearMessages();
    try {
      const res = await apiRequest(`/api/sso/${enable ? "enable" : "disable"}`, { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        setSuccess(data.message);
        fetchConfig();
      } else {
        setError(data.detail || `Failed to ${enable ? "enable" : "disable"} SSO.`);
      }
    } catch {
      setError(`Failed to ${enable ? "enable" : "disable"} SSO.`);
    }
  };

  const handleEnforce = async () => {
    clearMessages();
    if (!form.breakglass_user_id) {
      setError("Please select a break-glass admin before enforcing SSO.");
      return;
    }
    try {
      const res = await apiRequest("/api/sso/enforce", {
        method: "POST",
        body: JSON.stringify({ breakglass_user_id: form.breakglass_user_id }),
      });
      const data = await res.json();
      if (res.ok) {
        setSuccess(data.message);
        fetchConfig();
      } else {
        setError(data.detail || "Failed to enforce SSO.");
      }
    } catch {
      setError("Failed to enforce SSO.");
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const updateForm = (key: string, value: string) => {
    setForm(f => ({ ...f, [key]: value }));
  };

  const providerHelp = PROVIDER_HELP[form.provider_type] || PROVIDER_HELP.custom;

  // ---------- Toggle component ----------
  const Toggle = ({
    enabled,
    onToggle,
    disabled = false,
  }: {
    enabled: boolean;
    onToggle: () => void;
    disabled?: boolean;
  }) => (
    <button
      onClick={onToggle}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Security</h1>
        <p className="text-muted-foreground mt-1">
          Configure SAML Single Sign-On for your organization
        </p>
      </div>

      {/* Status Messages */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg px-4 py-3 flex items-start gap-2"
          >
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}
        {success && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-green-500/10 border border-green-500/20 text-green-400 text-sm rounded-lg px-4 py-3 flex items-start gap-2"
          >
            <Check className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{success}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* SSO Status */}
      {config && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-violet-500" />
                    SSO Status
                  </CardTitle>
                  <CardDescription className="mt-1">
                    Current SAML SSO configuration status
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {config.enforced ? (
                    <Badge className="bg-violet-600/20 text-violet-400 border-violet-600/30">
                      Enforced
                    </Badge>
                  ) : config.enabled ? (
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                      Enabled
                    </Badge>
                  ) : (
                    <Badge variant="secondary">Disabled</Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="text-sm font-medium">SSO Login</p>
                  <p className="text-xs text-muted-foreground">
                    {config.enabled
                      ? "Users can sign in via SSO"
                      : "Enable to allow SSO login"}
                  </p>
                </div>
                <Toggle
                  enabled={config.enabled}
                  onToggle={() => handleToggleSSO(!config.enabled)}
                  disabled={!config.idp_sso_url}
                />
              </div>

              {config.enabled && (
                <div className="flex items-center justify-between py-2 border-t border-border mt-2 pt-4">
                  <div>
                    <p className="text-sm font-medium">Enforce SSO</p>
                    <p className="text-xs text-muted-foreground">
                      {config.enforced
                        ? "Password login disabled (except break-glass admin)"
                        : "When enabled, password login will be disabled for all users"}
                    </p>
                  </div>
                  <Toggle
                    enabled={config.enforced}
                    onToggle={() => {
                      if (config.enforced) {
                        handleToggleSSO(true); // un-enforce by re-enabling without enforcement
                      } else {
                        handleEnforce();
                      }
                    }}
                  />
                </div>
              )}

              {config.enforced && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 mt-3"
                >
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-yellow-500 mt-0.5 shrink-0" />
                    <div className="text-sm">
                      <p className="text-yellow-400 font-medium">SSO is enforced</p>
                      <p className="text-yellow-400/80 text-xs mt-0.5">
                        Only the break-glass admin can use password login. All other users must
                        authenticate through your identity provider.
                      </p>
                    </div>
                  </div>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* SP Info (for IdP setup) */}
      {config && config.sp_entity_id && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Info className="h-4 w-4 text-violet-500" />
                Service Provider Details
              </CardTitle>
              <CardDescription>
                Copy these values into your Identity Provider&apos;s SAML app configuration
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <CopyField
                label="SP Entity ID"
                value={config.sp_entity_id}
                copied={copied}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="ACS URL"
                value={config.sp_acs_url || ""}
                copied={copied}
                onCopy={copyToClipboard}
              />
              <CopyField
                label="SP Metadata URL"
                value={`${API_URL}/api/auth/saml/${config.org_id}/metadata`}
                copied={copied}
                onCopy={copyToClipboard}
              />
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* SSO Configuration Form */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-violet-500" />
              SSO Configuration
            </CardTitle>
            <CardDescription>
              Configure your SAML 2.0 Identity Provider
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Provider Selector */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Identity Provider</label>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {PROVIDERS.map(p => (
                  <button
                    key={p.value}
                    onClick={() => updateForm("provider_type", p.value)}
                    className={`rounded-lg border p-3 text-left transition-all ${
                      form.provider_type === p.value
                        ? "border-violet-500/50 bg-violet-500/10"
                        : "border-border hover:border-violet-500/30"
                    }`}
                  >
                    <p className="text-sm font-medium">{p.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{p.description}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Metadata URL */}
            {providerHelp.fields.includes("metadata_url") && (
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  IdP Metadata URL
                  <span className="text-muted-foreground font-normal ml-1">(optional)</span>
                </label>
                <input
                  type="url"
                  value={form.idp_metadata_url}
                  onChange={e => updateForm("idp_metadata_url", e.target.value)}
                  placeholder="https://your-idp.com/metadata"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
                <p className="text-xs text-muted-foreground">
                  {providerHelp.metadataHint}
                </p>
              </div>
            )}

            {/* SSO URL */}
            <div className="space-y-2">
              <label className="text-sm font-medium">IdP SSO URL</label>
              <input
                type="url"
                value={form.idp_sso_url}
                onChange={e => updateForm("idp_sso_url", e.target.value)}
                placeholder="https://your-idp.com/sso/saml"
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              />
            </div>

            {/* Entity ID */}
            <div className="space-y-2">
              <label className="text-sm font-medium">IdP Entity ID</label>
              <input
                type="text"
                value={form.idp_entity_id}
                onChange={e => updateForm("idp_entity_id", e.target.value)}
                placeholder="http://www.okta.com/exk..."
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              />
            </div>

            {/* Certificate */}
            <div className="space-y-2">
              <label className="text-sm font-medium">IdP X.509 Certificate</label>
              <textarea
                value={form.idp_certificate}
                onChange={e => updateForm("idp_certificate", e.target.value)}
                placeholder={"-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----"}
                rows={6}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              />
              <p className="text-xs text-muted-foreground">
                Paste the full PEM-encoded certificate from your IdP
              </p>
            </div>

            {/* Break-glass admin */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Break-glass Admin</label>
              <select
                value={form.breakglass_user_id}
                onChange={e => updateForm("breakglass_user_id", e.target.value)}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
              >
                <option value="">Select an admin...</option>
                {orgAdmins.map(admin => (
                  <option key={admin.id} value={admin.id}>
                    {admin.name} ({admin.email})
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground">
                This admin can always use password login, even when SSO is enforced
              </p>
            </div>

            {/* Advanced: Attribute & Role Mapping */}
            <div className="border-t border-border pt-4">
              <button
                onClick={() => setShowAdvanced(!showAdvanced)}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <ChevronDown
                  className={`h-4 w-4 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
                />
                Advanced: Attribute &amp; Role Mapping
              </button>
              <AnimatePresence>
                {showAdvanced && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-4 space-y-4"
                  >
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        Attribute Mapping
                        <span className="text-muted-foreground font-normal ml-1">(JSON)</span>
                      </label>
                      <textarea
                        value={
                          form.attribute_mapping
                            ? JSON.stringify(form.attribute_mapping, null, 2)
                            : ""
                        }
                        onChange={e => {
                          try {
                            const parsed = e.target.value ? JSON.parse(e.target.value) : null;
                            setForm(f => ({ ...f, attribute_mapping: parsed }));
                          } catch {
                            // Let them keep typing — will validate on save
                          }
                        }}
                        placeholder={'{\n  "email": "http://schemas.xmlsoap.org/...",\n  "name": "displayName"\n}'}
                        rows={5}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                      />
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        Role Mapping
                        <span className="text-muted-foreground font-normal ml-1">(JSON)</span>
                      </label>
                      <textarea
                        value={
                          form.role_mapping
                            ? JSON.stringify(form.role_mapping, null, 2)
                            : ""
                        }
                        onChange={e => {
                          try {
                            const parsed = e.target.value ? JSON.parse(e.target.value) : null;
                            setForm(f => ({ ...f, role_mapping: parsed }));
                          } catch {}
                        }}
                        placeholder={'{\n  "Platform Admins": "admin",\n  "Engineering": "member",\n  "default": "viewer"\n}'}
                        rows={5}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                      />
                      <p className="text-xs text-muted-foreground">
                        Map IdP group names to Bonito roles (admin, member, viewer). Use
                        &quot;default&quot; for unmatched users.
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3 pt-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
              >
                {saving ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4" />
                )}
                Save Configuration
              </button>
              <button
                onClick={handleTest}
                disabled={testing || !config}
                className="flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50 transition-colors"
              >
                {testing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ExternalLink className="h-4 w-4" />
                )}
                Test Connection
              </button>
            </div>

            {/* Test Result */}
            <AnimatePresence>
              {testResult && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 space-y-2"
                >
                  <p className="text-sm text-green-400 font-medium flex items-center gap-2">
                    <Check className="h-4 w-4" />
                    {testResult.message}
                  </p>
                  {testResult.test_login_url && (
                    <a
                      href={`${API_URL}${testResult.test_login_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-violet-400 hover:text-violet-300 flex items-center gap-1"
                    >
                      <ExternalLink className="h-3 w-3" />
                      Open Test Login
                    </a>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

// ---------- Helper components ----------

function CopyField({
  label,
  value,
  copied,
  onCopy,
}: {
  label: string;
  value: string;
  copied: string | null;
  onCopy: (text: string, label: string) => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-border p-3">
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-mono truncate mt-0.5">{value}</p>
      </div>
      <button
        onClick={() => onCopy(value, label)}
        className="ml-3 p-2 rounded-md hover:bg-accent transition-colors shrink-0"
      >
        {copied === label ? (
          <Check className="h-4 w-4 text-green-500" />
        ) : (
          <Copy className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
    </div>
  );
}
