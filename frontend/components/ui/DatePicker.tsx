import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from 'lucide-react'
import { formatDateVI } from '@/lib/utils'

interface DatePickerProps {
  value: string // format: YYYY-MM-DD
  onChange: (val: string) => void
  placeholder?: string
  disableFuture?: boolean
}

export function DatePicker({ value, onChange, placeholder = 'Select date...', disableFuture = false }: DatePickerProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [viewDate, setViewDate] = useState(() => value ? new Date(value) : new Date())
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen) {
      setViewDate(value ? new Date(value) : new Date())
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

  const viewYear = viewDate.getFullYear()
  const viewMonth = viewDate.getMonth()

  const firstDayOfMonth = new Date(viewYear, viewMonth, 1).getDay() // 0 = Sun
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate()
  
  const days: (number | null)[] = []
  for (let i = 0; i < firstDayOfMonth; i++) days.push(null)
  for (let i = 1; i <= daysInMonth; i++) days.push(i)

  const WEEKDAYS = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']

  const now = new Date()
  const todayY = now.getFullYear()
  const todayM = now.getMonth()
  const todayD = now.getDate()

  let selectedY: number | null = null
  let selectedM: number | null = null
  let selectedD: number | null = null

  if (value) {
    const [y, m, d] = value.split('-').map(Number)
    selectedY = y
    selectedM = m - 1
    selectedD = d
  }

  function handleSelect(day: number) {
    const m = String(viewMonth + 1).padStart(2, '0')
    const d = String(day).padStart(2, '0')
    onChange(`${viewYear}-${m}-${d}`)
    setIsOpen(false)
  }

  function handleSetToday() {
    const m = String(todayM + 1).padStart(2, '0')
    const d = String(todayD).padStart(2, '0')
    onChange(`${todayY}-${m}-${d}`)
    setIsOpen(false)
  }

  const prevMonth = () => setViewDate(new Date(viewYear, viewMonth - 1, 1))
  const nextMonth = () => setViewDate(new Date(viewYear, viewMonth + 1, 1))

  let displayText = placeholder
  if (value) {
    displayText = formatDateVI(value)
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%' }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="input"
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8,
          padding: '0 12px', height: 42,
          background: 'var(--surface)',
          border: `1px solid ${isOpen ? 'var(--accent-green)' : 'var(--surface-border)'}`,
          color: value ? 'var(--text-primary)' : 'var(--text-secondary)',
          cursor: 'pointer', borderRadius: 10,
          transition: 'all 0.15s',
          ...(isOpen ? { boxShadow: '0 0 0 3px rgba(0,200,150,0.1)' } : {})
        }}
      >
        <CalendarIcon size={16} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
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
              borderRadius: 12, boxShadow: 'var(--shadow-dropdown)', zIndex: 100,
              width: 280, padding: '16px', transformOrigin: 'top',
            }}
          >
            {/* Header: Month/Year navigation */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <button 
                onClick={prevMonth}
                className="btn btn-ghost"
                type="button"
                style={{ width: 32, height: 32, padding: 0, borderRadius: 8 }}
              >
                <ChevronLeft size={18} />
              </button>
              <span style={{ fontSize: 14, fontWeight: 600 }}>Month {viewMonth + 1}, {viewYear}</span>
              <button 
                onClick={nextMonth}
                className="btn btn-ghost"
                type="button"
                style={{ width: 32, height: 32, padding: 0, borderRadius: 8, opacity: (disableFuture && viewYear === todayY && viewMonth >= todayM) ? 0.3 : 1 }}
                disabled={disableFuture && viewYear === todayY && viewMonth >= todayM}
              >
                <ChevronRight size={18} />
              </button>
            </div>

            {/* Weekdays */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 8 }}>
              {WEEKDAYS.map(wd => (
                <div key={wd} style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textAlign: 'center' }}>
                  {wd}
                </div>
              ))}
            </div>

            {/* Days Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 16 }}>
              {days.map((day, i) => {
                if (!day) return <div key={`empty-${i}`} />
                
                const isSelected = selectedY === viewYear && selectedM === viewMonth && selectedD === day
                const isToday = todayY === viewYear && todayM === viewMonth && todayD === day
                
                const isFutureMonth = viewYear > todayY || (viewYear === todayY && viewMonth > todayM)
                const isFutureDate = isFutureMonth || (viewYear === todayY && viewMonth === todayM && day > todayD)
                const isFuture = disableFuture && isFutureDate

                return (
                  <button
                    key={i}
                    onClick={() => isFuture ? null : handleSelect(day)}
                    disabled={isFuture}
                    type="button"
                    style={{
                      height: 32,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      borderRadius: '50%',
                      border: isToday && !isSelected ? '1px solid var(--accent-green)' : '1px solid transparent',
                      fontSize: 13,
                      fontWeight: isSelected ? 600 : (isToday ? 600 : 400),
                      background: isSelected ? 'var(--accent-green)' : 'transparent',
                      color: isFuture ? 'var(--text-tertiary)' : (isSelected ? '#0f0f14' : (isToday ? 'var(--accent-green)' : 'var(--text-primary)')),
                      cursor: isFuture ? 'not-allowed' : 'pointer',
                      opacity: isFuture ? 0.3 : 1,
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => {
                      if (!isSelected && !isFuture) e.currentTarget.style.background = 'var(--surface-hover)'
                    }}
                    onMouseLeave={e => {
                      if (!isSelected && !isFuture) e.currentTarget.style.background = 'transparent'
                    }}
                  >
                    {day}
                  </button>
                )
              })}
            </div>

            {/* Footer buttons */}
            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--surface-border)', paddingTop: 12 }}>
              <button 
                type="button"
                onClick={() => { onChange(''); setIsOpen(false) }}
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 12, padding: '4px 10px', color: 'var(--text-tertiary)' }}
              >
                Delete
              </button>
              <button 
                type="button"
                onClick={handleSetToday}
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 12, padding: '4px 10px', color: 'var(--accent-green)' }}
              >
                Today
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
