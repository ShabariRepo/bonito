"use client";

import { motion } from "framer-motion";
import { Mail, Clock, MessageSquare, Loader2 } from "lucide-react";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://celebrated-contentment-production-0fc4.up.railway.app";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", email: "", company: "", message: "" });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSending(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("Failed to send");
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Please email us directly at sales@getbonito.com");
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
          Get in touch
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-4 text-lg text-[#888] max-w-2xl"
        >
          Have a question, need a demo, or want to discuss enterprise pricing? We&apos;d love to hear from you.
        </motion.p>
      </section>

      <section className="pb-24 grid md:grid-cols-2 gap-12">
        {/* Form */}
        <div>
          {submitted ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-[#111] border border-[#7c3aed]/30 rounded-xl p-12 text-center"
            >
              <MessageSquare className="w-12 h-12 text-[#7c3aed] mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">Message sent!</h3>
              <p className="text-sm text-[#888]">We&apos;ll get back to you within 24 hours.</p>
            </motion.div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Name</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition"
                  placeholder="Your name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Email</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition"
                  placeholder="you@company.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Company</label>
                <input
                  type="text"
                  value={form.company}
                  onChange={(e) => setForm({ ...form, company: e.target.value })}
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition"
                  placeholder="Your company (optional)"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Message</label>
                <textarea
                  required
                  rows={5}
                  value={form.message}
                  onChange={(e) => setForm({ ...form, message: e.target.value })}
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition resize-none"
                  placeholder="How can we help?"
                />
              </div>
              {error && <p className="text-red-400 text-sm">{error}</p>}
              <button
                type="submit"
                disabled={sending}
                className="w-full py-3 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
              >
                {sending ? <><Loader2 className="w-4 h-4 animate-spin" /> Sending...</> : "Send Message"}
              </button>
            </form>
          )}
        </div>

        {/* Info */}
        <div className="space-y-6">
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6">
            <Mail className="w-6 h-6 text-[#7c3aed] mb-3" />
            <h3 className="font-semibold mb-2">Email Us</h3>
            <p className="text-sm text-[#888] mb-1">Sales: <a href="mailto:sales@getbonito.com" className="text-[#7c3aed] hover:underline">sales@getbonito.com</a></p>
            <p className="text-sm text-[#888]">Support: <a href="mailto:support@getbonito.com" className="text-[#7c3aed] hover:underline">support@getbonito.com</a></p>
          </div>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6">
            <Clock className="w-6 h-6 text-[#7c3aed] mb-3" />
            <h3 className="font-semibold mb-2">Response Times</h3>
            <p className="text-sm text-[#888] mb-1">Sales inquiries: within 24 hours</p>
            <p className="text-sm text-[#888] mb-1">Support (Pro): within 24 hours</p>
            <p className="text-sm text-[#888]">Support (Enterprise): within 4 hours</p>
          </div>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6">
            <h3 className="font-semibold mb-2">Office Hours</h3>
            <p className="text-sm text-[#888] mb-1">Monday — Friday</p>
            <p className="text-sm text-[#888]">9:00 AM — 6:00 PM EST</p>
          </div>
        </div>
      </section>
    </div>
  );
}
