import React from 'react'

interface AmountInputProps {
  value: string
  onChange: (val: string) => void
  color?: string
  autoFocus?: boolean
}

export function AmountInput({ value, onChange, color = 'var(--text-primary)', autoFocus }: AmountInputProps) {
  // If no value, we show an empty space or a subtle 0 in the data-value so the width doesn't collapse to 0.
  const displayValue = value || ''
  
  return (
    <div style={{
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'center',
      gap: 6,
      marginBottom: 32, // Some breathing room
    }}>
      {/* The auto-sizing wrapper trick using CSS Grid */}
      <div
        style={{
          display: 'grid',
          // The magic of auto-sizing: grid makes both child items occupy the same cell.
          // The wrapper expands to fit the widest child (the hidden ::after or span).
        }}
        className="auto-size-input-wrapper"
        data-value={displayValue || '0'}
      >
        {/* We use a hidden span instead of ::after because pseudo-elements can be tricky with exact font rendering in React */}
        <span 
          style={{ 
            gridArea: '1 / 1', 
            visibility: 'hidden', 
            whiteSpace: 'pre',
            fontSize: displayValue.length > 10 ? 36 : 48,
            fontWeight: 700,
            fontFamily: 'inherit',
          }}
        >
          {displayValue || '0'}
        </span>

        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="0"
          autoFocus={autoFocus}
          style={{
            gridArea: '1 / 1',
            width: '100%',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            textAlign: 'center',
            fontSize: displayValue.length > 10 ? 36 : 48,
            fontWeight: 700,
            fontFamily: 'inherit',
            color: value ? color : 'var(--text-tertiary)',
            caretColor: color, // Caret matches the context color
            transition: 'font-size 0.2s',
            padding: 0,
            margin: 0,
          }}
        />
      </div>

      <span style={{ 
        fontSize: displayValue.length > 10 ? 20 : 26, 
        fontWeight: 600, 
        color: value ? color : 'var(--text-tertiary)',
        opacity: value ? 0.7 : 0.3,
        transition: 'all 0.2s',
        userSelect: 'none'
      }}>
        đ
      </span>
    </div>
  )
}
