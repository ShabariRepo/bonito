"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { register } from "@/lib/auth";
import Image from "next/image";
import { Loader2 } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
      await register(email, password, name);
      router.push(`/verify-email?email=${encodeURIComponent(email)}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Registration failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-6">
      <div className="text-center mb-8">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Image src="/bonito-icon.png" alt="Bonito" width={80} height={40} className="object-contain" />
          <span className="text-3xl font-bold text-white">Bonito</span>
        </div>
        <p className="text-[#888] mt-2">Create your account</p>
      </div>
      <div className="bg-[#111] border border-[#222] rounded-xl p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-[#999] mb-2">Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-[#222] rounded-lg text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:ring-2 focus:ring-[#7c3aed]/50 focus:border-[#7c3aed] transition"
              placeholder="Your name"
            />
          </div>
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
          <div>
            <label className="block text-sm font-medium text-[#999] mb-2">Password</label>
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
            <label className="block text-sm font-medium text-[#999] mb-2">Confirm Password</label>
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
            Create Account
          </button>
        </form>
        <p className="text-center text-sm text-[#666] mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-[#7c3aed] hover:text-[#8b5cf6] transition">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
