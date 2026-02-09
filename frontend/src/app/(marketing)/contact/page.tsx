"use client";

import { motion } from "framer-motion";
import { Mail, Clock, MessageSquare } from "lucide-react";
import { useState } from "react";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

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
            <form
              onSubmit={(e) => {
                e.preventDefault();
                setSubmitted(true);
              }}
              className="space-y-5"
            >
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Name</label>
                <input
                  type="text"
                  required
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition"
                  placeholder="Your name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Email</label>
                <input
                  type="email"
                  required
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition"
                  placeholder="you@company.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Company</label>
                <input
                  type="text"
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition"
                  placeholder="Your company (optional)"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2 text-[#999]">Message</label>
                <textarea
                  required
                  rows={5}
                  className="w-full px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-lg text-[#f5f0e8] text-sm focus:border-[#7c3aed] focus:ring-1 focus:ring-[#7c3aed] outline-none transition resize-none"
                  placeholder="How can we help?"
                />
              </div>
              <button
                type="submit"
                className="w-full py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition"
              >
                Send Message
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
