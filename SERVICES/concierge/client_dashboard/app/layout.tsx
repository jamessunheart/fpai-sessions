import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Concierge — Client Dashboard",
  description: "Manage your Full Potential Concierge",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
