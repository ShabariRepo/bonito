"use client";

import { motion } from "framer-motion";
import { Mail, Building2, MessageSquare, Loader2, CheckCircle } from "lucide-react";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default function RequestAccessPage() {
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    use_case: "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/access-requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to submit request");
      }
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      <section className="pt-20 pb-16">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Request Access
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-4 text-lg text-[#888] max-w-2xl"
        >
          The Free plan is invite-only while we scale. Tell us about yourself and we&apos;ll get back to you within 24 hours.
        </motion.p>
      </section>

      <section className="pb-24 grid md:grid-cols-2 gap-12">
        {/* Form */}
        <div>
          {submitted ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-[#111] border border-[#7c3aed]/30 rounded-xl p-10 text-center"
            >
              <CheckCircle className="w-12 h-12 text-[#7c3aed] mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">Request Received</h2>
              <p className="text-[#888]">
                We&apos;ll be in touch within 24 hours. Keep an eye on your inbox — we&apos;ll send your invite code there once approved.
              </p>
            </motion.div>
          ) : (
            <motion.form
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              onSubmit={handleSubmit}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-8 space-y-5"
            >
              {/* Name */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[#ccc]" htmlFor="name">
                  Full name <span className="text-red-500">*</span>
                </label>
                <input
                  id="name"
                  type="text"
                  required
                  placeholder="Jane Smith"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg px-4 py-3 text-sm text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:border-[#7c3aed] transition-colors"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[#ccc]" htmlFor="email">
                  Work email <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
                  <input
                    id="email"
                    type="email"
                    required
                    placeholder="jane@acmecorp.com"
                    value={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                    className="w-full bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg pl-11 pr-4 py-3 text-sm text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:border-[#7c3aed] transition-colors"
                  />
                </div>
              </div>

              {/* Company */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[#ccc]" htmlFor="company">
                  Company <span className="text-[#555]">(optional)</span>
                </label>
                <div className="relative">
                  <Building2 className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
                  <input
                    id="company"
                    type="text"
                    placeholder="Acme Corp"
                    value={form.company}
                    onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                    className="w-full bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg pl-11 pr-4 py-3 text-sm text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:border-[#7c3aed] transition-colors"
                  />
                </div>
              </div>

              {/* Use Case */}
              <div>
                <label className="block text-sm font-medium mb-2 text-[#ccc]" htmlFor="use_case">
                  How are you planning to use Bonito? <span className="text-[#555]">(optional)</span>
                </label>
                <div className="relative">
                  <MessageSquare className="absolute left-4 top-4 w-4 h-4 text-[#555]" />
                  <textarea
                    id="use_case"
                    rows={4}
                    placeholder="We're building a multi-cloud AI gateway for our internal dev platform and need unified routing and cost visibility across AWS Bedrock and Azure OpenAI..."
                    value={form.use_case}
                    onChange={(e) => setForm((f) => ({ ...f, use_case: e.target.value }))}
                    className="w-full bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg pl-11 pr-4 py-3 text-sm text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:border-[#7c3aed] transition-colors resize-none"
                  />
                </div>
              </div>

              {error && (
                <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-2">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={sending}
                className="w-full bg-[#7c3aed] hover:bg-[#6d28d9] disabled:bg-[#7c3aed]/50 text-white font-semibold py-3 rounded-lg transition flex items-center justify-center gap-2"
              >
                {sending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Submitting...
                  </>
                ) : (
                  "Request Access"
                )}
              </button>
            </motion.form>
          )}
        </div>

        {/* Sidebar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-8">
            <h3 className="text-lg font-semibold mb-4">What you get with the Free plan</h3>
            <ul className="space-y-3">
              {[
                "Up to 1 cloud provider connection (AWS, Azure, or GCP)",
                "25,000 gateway API calls / month",
                "Automatic failover routing",
                "Model catalog & playground",
                "1 BonBon Simple agent (rate-limited)",
                "Standard request logging",
                "AI Code Review — 6 reviews / month",
                "Community support (Discord)",
                "1 team member",
              ].map((feat) => (
                <li key={feat} className="flex items-start gap-3 text-sm text-[#999]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#7c3aed] mt-2 flex-shrink-0" />
                  {feat}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-8">
            <h3 className="text-lg font-semibold mb-3">Ready to skip the queue?</h3>
            <p className="text-sm text-[#888] mb-4">
              Pro comes with a 14-day free trial — no credit card required, full access to all features.
            </p>
            <a
              href="/pricing"
              className="text-sm text-[#7c3aed] hover:text-[#8b5cf6] font-medium transition"
            >
              View all plans →
            </a>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
