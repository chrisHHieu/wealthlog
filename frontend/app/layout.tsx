import type { Metadata } from 'next'
import { Plus_Jakarta_Sans } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const jakarta = Plus_Jakarta_Sans({
  variable: '--font-inter', /* Keeping the variable name same to avoid changing css everywhere */
  subsets: ['latin'],
})

export const metadata: Metadata = {
  title: 'WealthLog — Quản lý tài chính cá nhân',
  description: 'Ứng dụng quản lý tài chính cá nhân phong cách Luxury Fintech. Theo dõi chi tiêu, ngân sách, mục tiêu và đầu tư của bạn.',
  keywords: ['quản lý tài chính', 'chi tiêu', 'tiết kiệm', 'đầu tư', 'ngân sách'],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="vi" suppressHydrationWarning data-scroll-behavior="smooth">
      <body className={`${jakarta.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
