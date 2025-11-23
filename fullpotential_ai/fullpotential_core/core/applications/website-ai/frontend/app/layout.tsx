import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Full Potential AI",
  description: "Conscious operating system for regenerative systems.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

