import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SUPERCELL | ATC Emergency Triage Environment",
  description:
    "OpenEnv-compliant reinforcement learning environment for AI-powered air traffic control emergency triage. Prioritize landings under fuel, weather, and emergency constraints.",
  keywords: [
    "SUPERCELL",
    "ATC",
    "air traffic control",
    "reinforcement learning",
    "OpenEnv",
    "PyTorch",
    "Meta",
    "AI agent",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="preconnect"
          href="https://fonts.googleapis.com"
        />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen antialiased overflow-hidden">
        {children}
      </body>
    </html>
  );
}
