import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AppSidebar } from "@/components/app-sidebar";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Hunar Hiring Assistant",
  description: "AI-powered voice hiring platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground">
        <div className="flex h-screen overflow-hidden">
          <AppSidebar />
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-7xl p-6 md:p-8">
              {children}
            </div>
          </main>
        </div>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
