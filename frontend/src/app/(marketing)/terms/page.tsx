"use client";

import { motion } from "framer-motion";

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12">
      <section className="pt-20 pb-16">
        <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-4xl font-bold tracking-tight">
          Terms of Service
        </motion.h1>
        <p className="mt-4 text-sm text-[#666]">Last updated: February 14, 2026</p>
      </section>
      <section className="pb-24 prose prose-invert prose-sm max-w-none text-[#888] space-y-6">
        <p>Welcome to Bonito. By using our platform, you agree to the following terms and conditions. Please read them carefully.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">1. Acceptance of Terms</h2>
        <p>By accessing or using Bonito, you agree to be bound by these Terms of Service and our Privacy Policy. If you do not agree to these terms, do not use the platform.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">2. Description of Service</h2>
        <p>Bonito provides a unified control plane for managing multi-cloud AI infrastructure, including provider management (AWS Bedrock, Azure OpenAI, Google Cloud Vertex AI), API gateway routing, deployment provisioning, model activation, routing policies, cost analytics, notifications, and compliance tooling. Bonito connects to your existing cloud provider accounts using credentials you supply.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">3. User Accounts</h2>
        <p>You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account. This includes safeguarding any cloud provider credentials (IAM keys, service principal secrets, service account JSON) you provide to Bonito.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">4. Cloud Provider Resources</h2>
        <p>Bonito creates and manages resources in your cloud accounts on your behalf, including model deployments (e.g., AWS Provisioned Throughput, Azure OpenAI deployments), model activations, and gateway routing configurations. You are solely responsible for any costs incurred by your cloud providers as a result of resources created through Bonito. We recommend reviewing deployments regularly and using the least-privilege IAM configurations described in our documentation.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">5. Acceptable Use</h2>
        <p>You agree not to use Bonito for any unlawful purposes or in any way that could damage, disable, or impair the service.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">6. Billing and Payments</h2>
        <p>Paid plans are billed monthly. You may cancel at any time. Refunds are handled on a case-by-case basis. Bonito charges only for platform access — your AI provider costs (AWS, Azure, GCP) are billed separately by those providers through your own cloud accounts.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">7. Limitation of Liability</h2>
        <p>Bonito is provided &quot;as is&quot; without warranties of any kind. We shall not be liable for any indirect, incidental, or consequential damages arising from use of the platform, including but not limited to costs incurred by cloud provider resources deployed through Bonito.</p>
        <h2 className="text-lg font-semibold text-[#f5f0e8]">8. Contact</h2>
        <p>For questions about these terms, contact us at <a href="mailto:support@getbonito.com" className="text-[#7c3aed]">support@getbonito.com</a>.</p>
      </section>
    </div>
  );
}
