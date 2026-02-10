"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { verifyEmail, resendVerification } from "@/lib/auth";
import { CheckCircle, XCircle, Mail, Loader2, RefreshCw } from "lucide-react";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const email = searchParams.get("email");
  const [status, setStatus] = useState<"pending" | "verifying" | "success" | "error">(
    token ? "verifying" : "pending"
  );
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    if (!token) return;
    verifyEmail(token)
      .then(() => setStatus("success"))
      .catch((err) => {
        setStatus("error");
        setErrorMsg(err.message);
      });
  }, [token]);

  if (status === "verifying") {
    return (
      <div className="text-center">
        <Loader2 className="w-12 h-12 text-[#7c3aed] animate-spin mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-[#f5f0e8]">Verifying your email...</h2>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="text-center">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-[#f5f0e8] mb-2">Email Verified!</h2>
        <p className="text-[#888] mb-6">Your account is ready. You can now sign in.</p>
        <Link
          href="/login"
          className="inline-block px-8 py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition"
        >
          Sign In
        </Link>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="text-center">
        <XCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-[#f5f0e8] mb-2">Verification Failed</h2>
        <p className="text-[#888] mb-6">{errorMsg || "The link may be invalid or expired."}</p>
        <Link
          href="/login"
          className="inline-block px-8 py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition"
        >
          Go to Login
        </Link>
      </div>
    );
  }

  // Pending - show "check your email" message
  const [resending, setResending] = useState(false);
  const [resendMsg, setResendMsg] = useState("");

  const handleResend = async () => {
    if (!email || resending) return;
    setResending(true);
    setResendMsg("");
    try {
      await resendVerification(email);
      setResendMsg("Verification email sent!");
    } catch (err: unknown) {
      setResendMsg(err instanceof Error ? err.message : "Failed to resend");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="text-center">
      <Mail className="w-16 h-16 text-[#7c3aed] mx-auto mb-4" />
      <h2 className="text-2xl font-bold text-[#f5f0e8] mb-2">Check your email</h2>
      <p className="text-[#888] mb-2">
        We sent a verification link to{" "}
        {email ? <span className="text-[#f5f0e8] font-medium">{email}</span> : "your email"}
      </p>
      <p className="text-[#666] text-sm mb-6">Click the link in the email to verify your account.</p>
      {email && (
        <button
          onClick={handleResend}
          disabled={resending}
          className="inline-flex items-center gap-2 px-4 py-2 bg-[#1a1a1a] hover:bg-[#222] border border-[#333] text-[#f5f0e8] text-sm rounded-lg transition mb-4 disabled:opacity-50"
        >
          {resending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          Resend verification email
        </button>
      )}
      {resendMsg && <p className="text-sm text-[#888] mb-4">{resendMsg}</p>}
      <div>
        <Link
          href="/login"
          className="text-[#7c3aed] hover:text-[#8b5cf6] text-sm transition"
        >
          Back to login
        </Link>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <div className="w-full max-w-md mx-auto px-6">
      <div className="bg-[#111] border border-[#222] rounded-xl p-8">
        <Suspense fallback={<div className="text-center"><Loader2 className="w-8 h-8 text-[#7c3aed] animate-spin mx-auto" /></div>}>
          <VerifyEmailContent />
        </Suspense>
      </div>
    </div>
  );
}
