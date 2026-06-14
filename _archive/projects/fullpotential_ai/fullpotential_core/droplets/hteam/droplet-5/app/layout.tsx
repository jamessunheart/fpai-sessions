import './globals.css'
import { Inter } from 'next/font/google'
import { ThemeProvider } from './shared/contexts/ThemeContext'
import { NotificationProvider } from './shared/contexts/NotificationContext'
import { AuthProvider } from './shared/contexts/AuthContext'
import './lib/startup' // Initialize UDC services

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Full Potential Dashboard',
  description: 'Modern dashboard for managing Airtable system with real-time monitoring',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <AuthProvider>
          <ThemeProvider>
            <NotificationProvider>
              <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
                {children}
              </div>
            </NotificationProvider>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  )
}