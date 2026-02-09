"use client";

import { motion } from "framer-motion";

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12">
      <section className="pt-20 pb-16">
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-4xl font-bold tracking-tight">
          Privacy Policy
        </motion.h1>
        <p className="mt-4 text-sm text-[#666]">Last updated: February 1, 2026</p>
      </section>
      <section className="pb-24 prose prose-invert prose-sm max-w-none text-[#888] space-y-6">
        <p>Your privacy is important to us. This policy explains how Bonito collects, uses, and protects your information.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">1. Information We Collect</h2>
        <p>We collect account information (name, email, company), usage data (API call counts, feature usage), and billing information for paid plans.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">2. What We Don&apos;t Collect</h2>
        <p>Bonito does not store the content of your AI requests or responses. Your prompts and completions pass through our gateway but are never persisted.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">3. How We Use Your Information</h2>
        <p>We use your information to provide and improve the service, send important notifications, and process payments. We do not sell your data to third parties.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">4. Data Security</h2>
        <p>We use industry-standard encryption at rest and in transit. Access to customer data is restricted and audited. Enterprise plans include additional compliance certifications.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">5. Cookies and Analytics</h2>
        <p>We use Microsoft Clarity for analytics to understand how users interact with our platform. This helps us improve the user experience.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">6. Contact</h2>
        <p>For privacy concerns, contact us at <a href="mailto:support@getbonito.com" className="text-[#7c3aed]">support@getbonito.com</a>.</p>
      </section>
    </div>
  );
}
