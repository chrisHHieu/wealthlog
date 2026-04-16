import React, { useState } from 'react'

interface BankLogoProps {
  iconStr: string
  color: string
  size?: number
}

// A mapping of our hardcoded strings to standard VietQR codes or special case handling
const BANK_CODE_MAP: Record<string, string> = {
  VCB: 'VCB',
  TCB: 'TCB',
  ACB: 'ACB',
  MB: 'MB',
  MOMO: 'momo',
  ZALO: 'ZaloPay', // VietQR might not have ZaloPay, but we handle error graceful fallback
  VPB: 'VPB',
  BIDV: 'BIDV',
  VBA: 'VBA',
  TPB: 'TPB',
  STB: 'STB',
  VIB: 'VIB',
}

export function BankLogo({ iconStr, color, size = 40 }: BankLogoProps) {
  const [imgError, setImgError] = useState(false)

  // Is it potentially a bank code? (All letters, length > 2)
  const isBankCode = iconStr.length > 2 && /^[a-zA-Z]+$/.test(iconStr)
  
  if (isBankCode && !imgError) {
    const code = BANK_CODE_MAP[iconStr.toUpperCase()] || iconStr
    // Try to load from VietQR CDN
    return (
      <div style={{
        width: size, 
        height: size, 
        background: '#fff', // White background so logos look proper
        borderRadius: '25%', // Slight squircle matching standard app icons
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.05)', // Inner border to frame white logos
        overflow: 'hidden'
      }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img 
          src={`https://cdn.vietqr.io/img/${code}.png`} 
          alt={iconStr}
          onError={() => setImgError(true)}
          style={{ width: '100%', height: '100%', objectFit: 'contain', padding: '10%' }}
        />
      </div>
    )
  }

  // Fallback: Custom text or emoji rendering
  return (
    <div style={{
      width: size, 
      height: size, 
      borderRadius: '25%',
      background: `${color}20`,
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      fontSize: size * 0.5,
    }}>
      {isBankCode ? (
         <span style={{ fontSize: size * 0.28, fontWeight: 800, color, letterSpacing: -0.5 }}>{iconStr}</span>
      ) : (
         iconStr
      )}
    </div>
  )
}
