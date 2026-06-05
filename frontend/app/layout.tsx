import type { Metadata } from 'next'
import { Plus_Jakarta_Sans } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const jakarta = Plus_Jakarta_Sans({
  variable: '--font-inter',
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'WealthLog - Personal Finance Manager',
  description: 'A personal finance app for tracking spending, budgets, goals, and investments.',
  keywords: ['personal finance', 'spending', 'saving', 'investing', 'budget'],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning data-scroll-behavior="smooth">
      <body className={`${jakarta.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
