"use client";

import { useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { resetPassword } from "@/lib/auth";
import { Loader2, CheckCircle } from "lucide-react";

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!token) {
    return (
      <div className="text-center">
        <p className="text-[#888] mb-4">Invalid reset link.</p>
        <Link href="/forgot-password" className="text-[#7c3aed] hover:text-[#8b5cf6] transition">
          Request a new one
        </Link>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Reset failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="text-center">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-[#f5f0e8] mb-2">Password Reset!</h2>
        <p className="text-[#888] mb-6">Your password has been updated.</p>
        <Link
          href="/login"
          className="inline-block px-8 py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition"
        >
          Sign In
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}
      <div>
        <label className="block text-sm font-medium text-[#999] mb-2">New Password</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-3 bg-[#0a0a0a] border border-[#222] rounded-lg text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:ring-2 focus:ring-[#7c3aed]/50 focus:border-[#7c3aed] transition"
          placeholder="••••••••"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-[#999] mb-2">Confirm New Password</label>
        <input
          type="password"
          required
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="w-full px-4 py-3 bg-[#0a0a0a] border border-[#222] rounded-lg text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:ring-2 focus:ring-[#7c3aed]/50 focus:border-[#7c3aed] transition"
          placeholder="••••••••"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
      >
        {loading && <Loader2 className="w-4 h-4 animate-spin" />}
        Reset Password
      </button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="w-full max-w-md mx-auto px-6">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-[#f5f0e8] tracking-tight">Bonito</h1>
        <p className="text-[#888] mt-2">Set a new password</p>
      </div>
      <div className="bg-[#111] border border-[#222] rounded-xl p-8">
        <Suspense fallback={<div className="text-center"><Loader2 className="w-8 h-8 text-[#7c3aed] animate-spin mx-auto" /></div>}>
          <ResetPasswordContent />
        </Suspense>
      </div>
    </div>
  );
}
