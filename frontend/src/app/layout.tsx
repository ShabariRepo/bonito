import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Providers } from "@/components/layout/providers";
import { CommandBar } from "@/components/ai/command-bar";
import { ChatPanel } from "@/components/ai/chat-panel";
import { NotificationBell } from "@/components/layout/notification-bell";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Bonito — Enterprise AI Platform",
  description: "Unified AI model management and deployment platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
              <div className="flex justify-end px-8 pt-4">
                <NotificationBell />
              </div>
              <div className="p-8 pt-2">{children}</div>
            </main>
          </div>
          <CommandBar />
          <ChatPanel />
        </Providers>
      </body>
    </html>
  );
}
