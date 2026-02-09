"use client";

import { useState } from "react";
import Link from "next/link";
import { forgotPassword } from "@/lib/auth";
import { Loader2, ArrowLeft } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-6">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-[#f5f0e8] tracking-tight">Bonito</h1>
        <p className="text-[#888] mt-2">Reset your password</p>
      </div>
      <div className="bg-[#111] border border-[#222] rounded-xl p-8">
        {sent ? (
          <div className="text-center">
            <p className="text-[#f5f0e8] mb-2">Check your email</p>
            <p className="text-[#888] text-sm mb-6">If an account exists, we sent a reset link.</p>
            <Link href="/login" className="text-[#7c3aed] hover:text-[#8b5cf6] text-sm transition">
              Back to login
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#999] mb-2">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-[#0a0a0a] border border-[#222] rounded-lg text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:ring-2 focus:ring-[#7c3aed]/50 focus:border-[#7c3aed] transition"
                placeholder="you@company.com"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Send Reset Link
            </button>
            <Link href="/login" className="flex items-center justify-center gap-2 text-sm text-[#666] hover:text-[#999] transition">
              <ArrowLeft className="w-4 h-4" /> Back to login
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
