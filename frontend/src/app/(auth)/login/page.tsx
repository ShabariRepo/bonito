"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login } from "@/lib/auth";
import { Loader2 } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    // Read directly from DOM to handle password manager autofill
    const emailVal = emailRef.current?.value || email;
    const passwordVal = passwordRef.current?.value || password;
    try {
      await login(emailVal, passwordVal);
      router.push("/dashboard");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-6">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-[#f5f0e8] tracking-tight">Bonito</h1>
        <p className="text-[#888] mt-2">Sign in to your account</p>
      </div>
      <div className="bg-[#111] border border-[#222] rounded-xl p-8">
        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-[#999] mb-2">Email</label>
            <input
              type="email"
              required
              ref={emailRef}
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
              ref={passwordRef}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-[#0a0a0a] border border-[#222] rounded-lg text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:ring-2 focus:ring-[#7c3aed]/50 focus:border-[#7c3aed] transition"
              placeholder="••••••••"
            />
          </div>
          <div className="flex justify-end">
            <Link href="/forgot-password" className="text-sm text-[#7c3aed] hover:text-[#8b5cf6] transition">
              Forgot password?
            </Link>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Sign In
          </button>
        </form>
        <p className="text-center text-sm text-[#666] mt-6">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-[#7c3aed] hover:text-[#8b5cf6] transition">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
