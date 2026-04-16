import type { Metadata } from 'next'
import { Geist } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'

const geistSans = Geist({
  variable: '--font-geist-sans',
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
      <body className={`${geistSans.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
