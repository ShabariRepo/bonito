"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setTokens } from "@/lib/auth";
import { useAuth } from "@/components/auth/auth-context";
import Image from "next/image";
import { Loader2, AlertTriangle } from "lucide-react";

/**
 * SSO Callback Page
 *
 * This page handles the redirect from the SAML ACS endpoint.
 * Tokens are passed in the URL fragment (hash) for security.
 * Errors are passed as query parameters.
 */

function SSOCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(true);

  useEffect(() => {
    // Check for error in query params first
    const queryError = searchParams.get("error");
    if (queryError) {
      setError(queryError);
      setProcessing(false);
      return;
    }

    // Extract tokens from URL fragment (hash)
    const hash = window.location.hash.substring(1); // remove the #
    if (!hash) {
      setError("No authentication data received. Please try again.");
      setProcessing(false);
      return;
    }

    const params = new URLSearchParams(hash);
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");

    if (!accessToken || !refreshToken) {
      setError("Incomplete authentication data. Please try again.");
      setProcessing(false);
      return;
    }

    // Store tokens and redirect to dashboard
    setTokens({ access_token: accessToken, refresh_token: refreshToken });

    // Clean the URL (remove hash with tokens)
    window.history.replaceState(null, "", window.location.pathname);

    // Refresh auth context and navigate
    refresh().then(() => {
      router.push("/dashboard");
    });
  }, [searchParams, refresh, router]);

  if (error) {
    return (
      <div className="w-full max-w-md mx-auto px-6">
        <div className="text-center mb-8">
          <Image src="/bonito-logo-400.png" alt="Bonito" width={64} height={43} className="mx-auto mb-4" />
        </div>
        <div className="bg-[#111] border border-[#222] rounded-xl p-8">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="h-12 w-12 rounded-full bg-red-500/10 flex items-center justify-center">
              <AlertTriangle className="h-6 w-6 text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-[#f5f0e8]">SSO Login Failed</h2>
              <p className="text-sm text-[#888] mt-2">{error}</p>
            </div>
            <button
              onClick={() => router.push("/login")}
              className="w-full py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition mt-4"
            >
              Back to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto px-6">
      <div className="text-center mb-8">
        <Image src="/bonito-logo-400.png" alt="Bonito" width={64} height={43} className="mx-auto mb-4" />
      </div>
      <div className="bg-[#111] border border-[#222] rounded-xl p-8">
        <div className="flex flex-col items-center text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-[#7c3aed]" />
          <div>
            <h2 className="text-lg font-semibold text-[#f5f0e8]">Completing Sign In</h2>
            <p className="text-sm text-[#888] mt-1">
              {processing ? "Verifying your identity..." : "Redirecting to dashboard..."}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SSOCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-md mx-auto px-6">
          <div className="text-center mb-8">
            <Image src="/bonito-logo-400.png" alt="Bonito" width={64} height={43} className="mx-auto mb-4" />
          </div>
          <div className="bg-[#111] border border-[#222] rounded-xl p-8">
            <div className="flex flex-col items-center text-center space-y-4">
              <Loader2 className="h-8 w-8 animate-spin text-[#7c3aed]" />
              <div>
                <h2 className="text-lg font-semibold text-[#f5f0e8]">Loading...</h2>
              </div>
            </div>
          </div>
        </div>
      }
    >
      <SSOCallbackContent />
    </Suspense>
  );
}
