"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  UsersRound,
  Search,
  Trash2,
  AlertTriangle,
  X,
  CheckCircle2,
  XCircle,
  ChevronDown,
} from "lucide-react";

interface AdminUser {
  id: string;
  email: string;
  name: string;
  org_id: string;
  org_name: string;
  role: string;
  email_verified: boolean;
  created_at: string | null;
}

const ROLES = ["admin", "editor", "viewer"] as const;

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [editingRole, setEditingRole] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest("/api/admin/users");
      if (!res.ok) throw new Error("Failed to load users");
      const data = await res.json();
      setUsers(data);
    } catch (e: any) {
      setError(e.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const filteredUsers = useMemo(() => {
    if (!search.trim()) return users;
    const q = search.toLowerCase();
    return users.filter(
      (u) =>
        u.email.toLowerCase().includes(q) ||
        u.name.toLowerCase().includes(q) ||
        u.org_name.toLowerCase().includes(q)
    );
  }, [users, search]);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      const res = await apiRequest(`/api/admin/users/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });
      if (!res.ok) throw new Error("Failed to update role");
      const updated = await res.json();
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, ...updated } : u))
      );
    } catch (e: any) {
      setError(e.message);
    }
    setEditingRole(null);
  };

  const handleDelete = async (userId: string) => {
    setDeleting(true);
    try {
      const res = await apiRequest(`/api/admin/users/${userId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete user");
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      setDeleteConfirm(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="All Users"
        description={`${users.length} users across all organizations`}
        breadcrumbs={[
          { label: "Admin", href: "/admin/system" },
          { label: "Users" },
        ]}
      />

      {error && <ErrorBanner message={error} onRetry={fetchUsers} />}

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search by email, name, or org..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-border bg-card pl-10 pr-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/40 transition-shadow"
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <LoadingDots />
        </div>
      ) : filteredUsers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <UsersRound className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
            <p className="text-muted-foreground">
              {search ? "No users match your search." : "No users found."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden">
          {/* Table header */}
          <div className="hidden md:grid grid-cols-[2fr_2fr_1.5fr_1fr_1fr_1fr_auto] gap-4 px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider border-b border-border">
            <span>Name</span>
            <span>Email</span>
            <span>Organization</span>
            <span>Role</span>
            <span>Verified</span>
            <span>Created</span>
            <span></span>
          </div>

          <div className="divide-y divide-border">
            {filteredUsers.map((user, i) => (
              <motion.div
                key={user.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.02 }}
                className="grid grid-cols-1 md:grid-cols-[2fr_2fr_1.5fr_1fr_1fr_1fr_auto] gap-4 px-4 py-3 items-center hover:bg-accent/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="font-medium truncate">{user.name}</span>
                </div>
                <span className="text-sm text-muted-foreground truncate">{user.email}</span>
                <span className="text-sm truncate">{user.org_name}</span>

                {/* Role dropdown */}
                <div className="relative">
                  {editingRole === user.id ? (
                    <select
                      value={user.role}
                      onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      onBlur={() => setEditingRole(null)}
                      autoFocus
                      className="w-full rounded-md border border-violet-500 bg-card px-2 py-1 text-sm focus:outline-none"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <button
                      onClick={() => setEditingRole(user.id)}
                      className="flex items-center gap-1 text-sm hover:text-violet-400 transition-colors"
                    >
                      <Badge
                        variant={
                          user.role === "admin"
                            ? "default"
                            : user.role === "editor"
                            ? "secondary"
                            : "outline"
                        }
                        className="text-[10px] cursor-pointer"
                      >
                        {user.role}
                      </Badge>
                      <ChevronDown className="h-3 w-3 text-muted-foreground" />
                    </button>
                  )}
                </div>

                {/* Verified */}
                <div>
                  {user.email_verified ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-muted-foreground/50" />
                  )}
                </div>

                <span className="text-sm text-muted-foreground">{formatDate(user.created_at)}</span>

                {/* Actions */}
                <button
                  onClick={() => setDeleteConfirm(user.id)}
                  className="p-1.5 rounded-md text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  title="Delete user"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </motion.div>
            ))}
          </div>
        </Card>
      )}

      {/* Delete confirmation modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setDeleteConfirm(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-lg p-6 max-w-md w-full mx-4 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start gap-4">
                <div className="h-10 w-10 rounded-full bg-red-500/15 flex items-center justify-center shrink-0">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">Delete User</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    This will permanently delete this user account. This action cannot be undone.
                  </p>
                  <div className="flex gap-3 mt-4">
                    <button
                      onClick={() => handleDelete(deleteConfirm)}
                      disabled={deleting}
                      className="px-4 py-2 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                    >
                      {deleting ? "Deleting..." : "Delete"}
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="px-4 py-2 text-sm font-medium rounded-md border border-border hover:bg-accent transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
                <button onClick={() => setDeleteConfirm(null)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
