import type { Metadata, Viewport } from "next";

import "./globals.css";


export const metadata: Metadata = {
  title: {
    default: "UserOps AI",
    template: "%s · UserOps AI",
  },
  description:
    "A secure operational chatbot for creating, finding, updating, and deleting users with natural-language commands.",
  applicationName: "UserOps AI",
};

export const viewport: Viewport = {
  themeColor: "#020617",
  colorScheme: "dark",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full bg-slate-950 antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
