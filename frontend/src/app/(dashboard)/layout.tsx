"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { CommandBar } from "@/components/ai/command-bar";
import { ChatPanel } from "@/components/ai/chat-panel";
import { NotificationBell } from "@/components/layout/notification-bell";
import { useAuth } from "@/components/auth/auth-context";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0a0a]">
        <div className="w-8 h-8 border-2 border-[#7c3aed] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="flex justify-end px-8 pt-4">
          <NotificationBell />
        </div>
        <div className="p-8 pt-2">{children}</div>
      </main>
      <CommandBar />
      <ChatPanel />
    </div>
  );
}
