import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, Check } from 'lucide-react'

export interface SelectOption {
  value: string
  label: React.ReactNode
  searchableText?: string
}

interface SelectProps {
  value: string
  onChange: (val: string) => void
  options: SelectOption[]
  placeholder?: string
  width?: string | number
  minWidth?: string | number
}

export function Select({ value, onChange, options, placeholder = 'Select...', width, minWidth = 150 }: SelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const selectedOpt = options.find(o => o.value === value)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={containerRef} style={{ position: 'relative', width, minWidth }}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="input"
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          height: 36,
          background: 'var(--surface)',
          border: `1px solid ${isOpen ? 'var(--accent-green)' : 'var(--surface-border)'}`,
          color: selectedOpt ? 'var(--text-primary)' : 'var(--text-secondary)',
          cursor: 'pointer',
          borderRadius: 10,
          transition: 'border-color 0.15s, box-shadow 0.15s',
          ...(isOpen ? { boxShadow: '0 0 0 3px rgba(0,200,150,0.1)' } : {})
        }}
      >
        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 13 }}>
          {selectedOpt ? selectedOpt.label : placeholder}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          style={{ flexShrink: 0, marginLeft: 8 }}
        >
          <ChevronDown size={14} style={{ color: 'var(--text-tertiary)' }} />
        </motion.div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -5, scaleY: 0.95 }}
            animate={{ opacity: 1, y: 0, scaleY: 1 }}
            exit={{ opacity: 0, y: -5, scaleY: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            style={{
              position: 'absolute',
              top: 'calc(100% + 4px)',
              left: 0,
              right: 0,
              background: 'var(--bg-secondary)',
              border: '1px solid var(--surface-border)',
              borderRadius: 10,
              boxShadow: 'var(--shadow-dropdown)',
              zIndex: 50,
              maxHeight: 280,
              overflowY: 'auto',
              padding: 4,
              transformOrigin: 'top',
            }}
          >
            {options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => {
                  onChange(opt.value)
                  setIsOpen(false)
                }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 10px',
                  borderRadius: 6,
                  border: 'none',
                  background: value === opt.value ? 'rgba(0,200,150,0.1)' : 'transparent',
                  color: value === opt.value ? 'var(--accent-green)' : 'var(--text-primary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: 13,
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => {
                  if (value !== opt.value) e.currentTarget.style.background = 'var(--surface-hover)'
                }}
                onMouseLeave={(e) => {
                  if (value !== opt.value) e.currentTarget.style.background = 'transparent'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {opt.label}
                  </span>
                </div>
                {value === opt.value && <Check size={14} style={{ flexShrink: 0 }} />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
