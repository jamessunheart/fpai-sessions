import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Concierge — Agent Console",
  description: "Single pane of glass for Full Potential Concierge agents",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
