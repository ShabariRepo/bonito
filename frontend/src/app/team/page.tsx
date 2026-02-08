"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Users, Plus, Mail, Shield, Edit, Trash2, X, ChevronDown, UserPlus } from "lucide-react";
import { API_URL } from "@/lib/utils";

const ROLE_STYLES: Record<string, { color: string; bg: string }> = {
  admin: { color: "text-violet-400", bg: "bg-violet-500/15" },
  editor: { color: "text-blue-400", bg: "bg-blue-500/15" },
  viewer: { color: "text-gray-400", bg: "bg-gray-500/15" },
};

function RoleBadge({ role }: { role: string }) {
  const style = ROLE_STYLES[role] || ROLE_STYLES.viewer;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${style.color} ${style.bg}`}>
      <Shield className="h-3 w-3" />
      {role}
    </span>
  );
}

function Avatar({ name }: { name: string }) {
  const initials = name.split(" ").map(n => n[0]).join("").slice(0, 2);
  const colors = ["bg-violet-600", "bg-blue-600", "bg-emerald-600", "bg-amber-600", "bg-rose-600"];
  const idx = name.charCodeAt(0) % colors.length;
  return (
    <div className={`h-10 w-10 rounded-full ${colors[idx]} flex items-center justify-center text-sm font-bold text-white`}>
      {initials}
    </div>
  );
}

export default function TeamPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("viewer");
  const [roleDropdown, setRoleDropdown] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      const res = await fetch(`${API_URL}/api/users/`);
      if (res.ok) setUsers(await res.json());
    } catch {} finally { setLoading(false); }
  };

  useEffect(() => { fetchUsers(); }, []);

  const inviteUser = async () => {
    if (!inviteEmail || !inviteName) return;
    try {
      await fetch(`${API_URL}/api/users/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail, name: inviteName, role: inviteRole }),
      });
      setShowInvite(false);
      setInviteEmail(""); setInviteName(""); setInviteRole("viewer");
      fetchUsers();
    } catch {}
  };

  const changeRole = async (id: string, role: string) => {
    try {
      await fetch(`${API_URL}/api/users/${id}/role`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      setRoleDropdown(null);
      fetchUsers();
    } catch {}
  };

  const removeUser = async (id: string) => {
    try {
      await fetch(`${API_URL}/api/users/${id}`, { method: "DELETE" });
      setDeleteConfirm(null);
      fetchUsers();
    } catch {}
  };

  if (loading) return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Team"
        description="Manage who has access to your AI platform"
        actions={
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowInvite(true)}
            className="flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
          >
            <UserPlus className="h-4 w-4" />
            Invite Member
          </motion.button>
        }
      />

      {users.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 text-center"
        >
          <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 3, repeat: Infinity }} className="text-5xl mb-4">
            👥
          </motion.div>
          <h3 className="text-xl font-semibold">Your team of one</h3>
          <p className="text-muted-foreground mt-2">Invite collaborators to get started</p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowInvite(true)}
            className="mt-6 flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700"
          >
            <Plus className="h-4 w-4" />
            Invite First Member
          </motion.button>
        </motion.div>
      ) : (
        <div className="space-y-3">
          {users.map((user, i) => (
            <motion.div
              key={user.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Card className="hover:border-violet-500/20 transition-colors">
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-4">
                    <Avatar name={user.name} />
                    <div>
                      <p className="font-medium">{user.name}</p>
                      <p className="text-sm text-muted-foreground flex items-center gap-1">
                        <Mail className="h-3 w-3" />
                        {user.email}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {/* Role dropdown */}
                    <div className="relative">
                      <button
                        onClick={() => setRoleDropdown(roleDropdown === user.id ? null : user.id)}
                        className="flex items-center gap-1 hover:opacity-80 transition-opacity"
                      >
                        <RoleBadge role={user.role} />
                        <ChevronDown className="h-3 w-3 text-muted-foreground" />
                      </button>
                      <AnimatePresence>
                        {roleDropdown === user.id && (
                          <motion.div
                            initial={{ opacity: 0, y: -5, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -5, scale: 0.95 }}
                            className="absolute right-0 top-full mt-1 z-10 w-32 rounded-md border border-border bg-card shadow-lg py-1"
                          >
                            {["admin", "editor", "viewer"].map((role) => (
                              <button
                                key={role}
                                onClick={() => changeRole(user.id, role)}
                                className={`w-full px-3 py-1.5 text-left text-sm capitalize hover:bg-accent transition-colors ${
                                  user.role === role ? "text-violet-400 font-medium" : "text-muted-foreground"
                                }`}
                              >
                                {role}
                              </button>
                            ))}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* Delete button */}
                    <div className="relative">
                      {deleteConfirm === user.id ? (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="flex items-center gap-1"
                        >
                          <button
                            onClick={() => removeUser(user.id)}
                            className="rounded px-2 py-1 text-xs bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-colors"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(null)}
                            className="rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                          >
                            Cancel
                          </button>
                        </motion.div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirm(user.id)}
                          className="rounded p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Invite Modal */}
      <AnimatePresence>
        {showInvite && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={() => setShowInvite(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold">Invite Team Member</h2>
                <button onClick={() => setShowInvite(false)} className="rounded-md p-1 hover:bg-accent transition-colors">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Name</label>
                  <input
                    type="text"
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    placeholder="Jane Doe"
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 transition-shadow"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Email</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="jane@company.com"
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 transition-shadow"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Role</label>
                  <div className="mt-1 flex gap-2">
                    {["admin", "editor", "viewer"].map((r) => (
                      <button
                        key={r}
                        onClick={() => setInviteRole(r)}
                        className={`flex-1 rounded-md border px-3 py-2 text-sm capitalize transition-all ${
                          inviteRole === r
                            ? "border-violet-500 bg-violet-500/10 text-violet-400"
                            : "border-border text-muted-foreground hover:border-violet-500/30"
                        }`}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>
                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={inviteUser}
                  disabled={!inviteEmail || !inviteName}
                  className="w-full rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Send Invite
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
