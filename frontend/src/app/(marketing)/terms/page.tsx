"use client";

import { motion } from "framer-motion";

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12">
      <section className="pt-20 pb-16">
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-4xl font-bold tracking-tight">
          Terms of Service
        </motion.h1>
        <p className="mt-4 text-sm text-[#666]">Last updated: February 1, 2026</p>
      </section>
      <section className="pb-24 prose prose-invert prose-sm max-w-none text-[#888] space-y-6">
        <p>Welcome to Bonito. By using our platform, you agree to the following terms and conditions. Please read them carefully.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">1. Acceptance of Terms</h2>
        <p>By accessing or using Bonito, you agree to be bound by these Terms of Service and our Privacy Policy. If you do not agree to these terms, do not use the platform.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">2. Description of Service</h2>
        <p>Bonito provides a unified control plane for managing multi-cloud AI infrastructure, including provider management, API gateway routing, cost analytics, and compliance tooling.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">3. User Accounts</h2>
        <p>You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">4. Acceptable Use</h2>
        <p>You agree not to use Bonito for any unlawful purposes or in any way that could damage, disable, or impair the service.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">5. Billing and Payments</h2>
        <p>Paid plans are billed monthly. You may cancel at any time. Refunds are handled on a case-by-case basis. AI provider costs (OpenAI, Anthropic, etc.) are billed separately by those providers.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">6. Limitation of Liability</h2>
        <p>Bonito is provided &quot;as is&quot; without warranties of any kind. We shall not be liable for any indirect, incidental, or consequential damages arising from use of the platform.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">7. Contact</h2>
        <p>For questions about these terms, contact us at <a href="mailto:support@getbonito.com" className="text-[#7c3aed]">support@getbonito.com</a>.</p>
      </section>
    </div>
  );
}
