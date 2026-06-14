import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'

interface MonthPickerProps {
  value: string // format: YYYY-MM
  onChange: (val: string) => void
}

const MONTHS = [
  'Month 1', 'Month 2', 'Month 3', 'Month 4',
  'Month 5', 'Month 6', 'Month 7', 'Month 8',
  'Month 9', 'Month 10', 'Month 11', 'Month 12'
]

export function MonthPicker({ value, onChange }: MonthPickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  
  // Parse current value or use current date
  const selectedYear = value ? parseInt(value.split('-')[0]) : new Date().getFullYear()
  const selectedMonth = value ? parseInt(value.split('-')[1]) : null
  
  const [viewYear, setViewYear] = useState(selectedYear)
  const containerRef = useRef<HTMLDivElement>(null)

  const now = new Date()
  const currentYear = now.getFullYear()
  const currentMonthIdx = now.getMonth() // 0-11

  useEffect(() => {
    if (isOpen) {
      setViewYear(value ? parseInt(value.split('-')[0]) : new Date().getFullYear())
    }
  }, [isOpen, value])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSelectMonth(monthIndex: number) {
    const y = viewYear
    const m = String(monthIndex + 1).padStart(2, '0')
    onChange(`${y}-${m}`)
    setIsOpen(false)
  }

  function handleSetCurrent() {
    const now = new Date()
    const y = now.getFullYear()
    const m = String(now.getMonth() + 1).padStart(2, '0')
    onChange(`${y}-${m}`)
    setIsOpen(false)
  }

  let displayText = 'Select months...'
  if (value) {
    displayText = `Month ${selectedMonth}, ${selectedYear}`
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', width: 150 }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="input"
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8,
          padding: '0 12px', height: 36,
          background: 'var(--surface)',
          border: `1px solid ${isOpen ? 'var(--accent-green)' : 'var(--surface-border)'}`,
          color: value ? 'var(--text-primary)' : 'var(--text-secondary)',
          cursor: 'pointer', borderRadius: 10,
          transition: 'all 0.15s',
          ...(isOpen ? { boxShadow: '0 0 0 3px rgba(0,200,150,0.1)' } : {})
        }}
      >
        <Calendar size={14} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
        <span style={{ flex: 1, textAlign: 'left', fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {displayText}
        </span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -5, scaleY: 0.95 }}
            animate={{ opacity: 1, y: 0, scaleY: 1 }}
            exit={{ opacity: 0, y: -5, scaleY: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            style={{
              position: 'absolute', top: 'calc(100% + 6px)', left: 0,
              background: 'var(--bg-secondary)', border: '1px solid var(--surface-border)',
              borderRadius: 12, boxShadow: 'var(--elevation-3)', zIndex: 50,
              width: 220, padding: '12px', transformOrigin: 'top',
            }}
          >
            {/* Header: Year navigation */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <button 
                onClick={() => setViewYear(y => y - 1)}
                className="btn btn-ghost"
                style={{ width: 28, height: 28, padding: 0 }}
              >
                <ChevronLeft size={16} />
              </button>
              <span style={{ fontSize: 14, fontWeight: 600 }}>{viewYear}</span>
              <button 
                onClick={() => setViewYear(y => y + 1)}
                className="btn btn-ghost"
                style={{ width: 28, height: 28, padding: 0, opacity: viewYear >= currentYear ? 0.3 : 1 }}
                disabled={viewYear >= currentYear}
              >
                <ChevronRight size={16} />
              </button>
            </div>

            {/* Grid of months */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6, marginBottom: 16 }}>
              {MONTHS.map((mName, i) => {
                const isSelected = selectedYear === viewYear && selectedMonth === i + 1
                const isFuture = viewYear > currentYear || (viewYear === currentYear && i > currentMonthIdx)
                
                return (
                  <button
                    key={i}
                    onClick={() => isFuture ? null : handleSelectMonth(i)}
                    disabled={isFuture}
                    style={{
                      padding: '8px 4px',
                      borderRadius: 8,
                      border: 'none',
                      fontSize: 12,
                      fontWeight: isSelected ? 600 : 400,
                      background: isSelected ? 'var(--accent-green)' : 'transparent',
                      color: isFuture ? 'var(--text-tertiary)' : (isSelected ? '#0f0f14' : 'var(--text-primary)'),
                      cursor: isFuture ? 'not-allowed' : 'pointer',
                      opacity: isFuture ? 0.3 : 1,
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => {
                      if (!isSelected && !isFuture) e.currentTarget.style.background = 'var(--surface-hover)'
                    }}
                    onMouseLeave={e => {
                      if (!isSelected && !isFuture) e.currentTarget.style.background = 'transparent'
                    }}
                  >
                    {mName.replace('Month ', 'T')}
                  </button>
                )
              })}
            </div>

            {/* Footer buttons */}
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--surface-border)', paddingTop: 10 }}>
              <button 
                onClick={() => { onChange(''); setIsOpen(false) }}
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 12, padding: '4px 8px', color: 'var(--text-tertiary)' }}
              >
                Clear
              </button>
              <button 
                onClick={handleSetCurrent}
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 12, padding: '4px 8px', color: 'var(--accent-green)' }}
              >
                This month
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
