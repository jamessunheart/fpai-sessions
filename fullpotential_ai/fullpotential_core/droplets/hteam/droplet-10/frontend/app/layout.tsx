import './globals.css';

export const metadata = {
  title: 'Orchestrator Dashboard',
  description: 'Next.js powered dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
