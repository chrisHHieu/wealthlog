'use client'

import React, { useState, useEffect } from 'react'
import { PageTransition } from '@/components/ui/PageTransition'
import { PageHeader } from '@/components/ui/PageHeader'
import { Portal } from '@/components/ui/Portal'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Save, Trash2, Plus, Edit2, Moon, Sun, Brain,
  FileText, Tag, Info, User, Palette, Shield,
  RefreshCw, CheckCircle, ChevronRight, Sparkles, Filter,
  AlertTriangle,
} from 'lucide-react'
import { useToast } from '@/components/ui/toaster'
import { useAppStore } from '@/store/useAppStore'
import { apiDelete, apiGet, apiJson, queryKeys } from '@/lib/api'
import { Select } from '@/components/ui/Select'
import { Stat } from '@/components/ui/Stat'
import { useMemoryFacts, useDeleteFact, useVerifyFact, UserFact } from '@/hooks/useMemoryFacts'

// ── Types ────────────────────────────────────────────────────────────────────

interface Category {
  id: string; name: string; icon: string; color: string
  type: string; budgetGroup?: string | null; isDefault: boolean
}
interface Digest {
  id: string; content: string; generatedForMonth: string; createdAt: string
}

type SectionId = 'profile' | 'appearance' | 'memory' | 'digest' | 'categories' | 'about'

const SECTIONS: { id: SectionId; label: string; icon: React.ElementType }[] = [
  { id: 'profile',    label: 'Profile',        icon: User },
  { id: 'appearance', label: 'Appearance',     icon: Palette },
  { id: 'memory',     label: 'AI Memory',      icon: Brain },
  { id: 'digest',     label: 'Monthly digest', icon: FileText },
  { id: 'categories', label: 'Category',       icon: Tag },
  { id: 'about',      label: 'About',          icon: Info },
]

// ── Category constants ────────────────────────────────────────────────────────

const CAT_COLORS = ['#00C896','#3b82f6','#f59e0b','#ef4444','#8b5cf6','#d946ef','#06b6d4','#84cc16','#f97316','#ec4899']
const CAT_ICONS = [
  '📦','🍜','🍔','☕','🍺','🚗','🚌','🚕','🏍️','🚄','⛽',
  '🛍️','👗','👟','📱','🎮','💻','🎬','🎵','📸','🎨','🏖️',
  '🏥','💊','🏃','🏋️‍♀️','🧘‍♀️','📚','🎓','✏️','💡','🧠',
  '🏠','🛋️','🧹','🔧','🪴','⚡','💧','🗑️','🌐','📞',
  '💄','💈','💅','💆‍♀️','🎀','✈️','🚂','🛳️','🗺️','🏕️',
  '👨‍👩‍👧','👶','🐶','🐱','💝','💰','🎁','📈','💵','🏦','💳','🧾',
  '💼','🛠️','🤖','⚙️','🔒','🛡️','🤝','🎉','🔥','✨','⭐',
]

const BUDGET_GROUPS = [
  { value: '', label: 'Uncategorized', color: '#6b7280' },
  { value: 'needs', label: 'Needs (50%)', color: '#3b82f6' },
  { value: 'wants', label: 'Wants (30%)', color: '#10b981' },
]

// ── Memory helpers ────────────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  preference:'Preferences', habit:'Habits', goal:'Goals',
  context:'Context', pattern:'Patterns', commitment:'Commitments',
  emotion:'Emotions', general:'General',
}
const CATEGORY_COLORS: Record<string, string> = {
  preference:'var(--accent-blue)', habit:'var(--accent-purple)',
  goal:'var(--accent-green)', context:'var(--accent-gold)',
  pattern:'var(--accent-amber)', commitment:'var(--accent-red)',
  emotion:'var(--accent-purple-light)', general:'var(--text-secondary)',
}

function ImportanceDots({ value }: { value: number }) {
  return (
    <span style={{ display:'flex', gap:2 }}>
      {Array.from({ length:10 }).map((_,i) => (
        <span key={i} style={{ width:5,height:5,borderRadius:'50%',
          background: i < value ? 'var(--accent-green)' : 'var(--surface-border)' }} />
      ))}
    </span>
  )
}

// ── Digest renderer ───────────────────────────────────────────────────────────

function DigestContent({ content }: { content: string }) {
  const parts = content.split(/\n(?=## )/)
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20 }}>
      {parts.map((block, i) => {
        const lines = block.split('\n')
        const isHeader = lines[0].startsWith('## ')
        const title = isHeader ? lines[0].replace('## ','') : null
        const body = isHeader ? lines.slice(1).join('\n').trim() : block.trim()
        return (
          <div key={i}>
            {title && (
              <div style={{ fontSize:13, fontWeight:700, color:'var(--text-primary)',
                borderBottom:'1px solid var(--surface-border)', paddingBottom:6, marginBottom:8 }}>
                {title}
              </div>
            )}
            <div style={{ fontSize:13, color:'var(--text-secondary)', lineHeight:1.8,
              whiteSpace:'pre-wrap' }}>
              {body}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function SettingsPage() {
  const { toast } = useToast()
  const qc = useQueryClient()
  const { theme, toggleTheme } = useAppStore()
  const [activeSection, setActiveSection] = useState<SectionId>('profile')

  // Profile
  const [userName, setUserName] = useState('')
  const [saving, setSaving] = useState(false)

  // Categories
  const [showCatForm, setShowCatForm] = useState(false)
  const [catName, setCatName] = useState('')
  const [catType, setCatType] = useState<'income'|'expense'|'both'>('expense')
  const [catBudgetGroup, setCatBudgetGroup] = useState('')
  const [catIcon, setCatIcon] = useState('📦')
  const [catColor, setCatColor] = useState('#6366f1')
  const [editCat, setEditCat] = useState<Category | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  // Memory
  const [filterCat, setFilterCat] = useState('all')
  const [deleteFactTarget, setDeleteFactTarget] = useState<UserFact | null>(null)

  // Queries
  const { data: settings } = useQuery<Record<string,string>>({
    queryKey: queryKeys.settings,
    queryFn: async () => {
      const response = await apiGet<unknown>('/api/settings')
      if (
        response &&
        typeof response === 'object' &&
        'data' in response &&
        typeof (response as { data?: unknown }).data === 'object'
      ) {
        return (response as { data: Record<string,string> }).data
      }
      return (response ?? {}) as Record<string,string>
    },
  })
  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: queryKeys.categories(),
    queryFn: () => apiGet<Category[]>('/api/categories'),
  })
  const { data: latestDigest, isLoading: digestLoading } = useQuery<Digest|null>({
    queryKey: queryKeys.digest,
    queryFn: () => apiGet<Digest|null>('/api/digest/latest'),
  })
  const { data: facts = [], isLoading: factsLoading } = useMemoryFacts()
  const deleteFact = useDeleteFact()
  const verifyFact = useVerifyFact()

  const generateDigest = useMutation({
    mutationFn: () => apiJson('/api/digest/generate',{method:'POST'}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.digest })
      toast('New digest generated')
    },
    onError: () => toast('Unable to generate digest - please try again later'),
  })

  useEffect(() => {
    if (settings?.userName) setUserName(settings.userName)
  }, [settings])

  // ── Handlers ────────────────────────────────────────────────────────────────

  async function saveProfile() {
    setSaving(true)
    try {
      await apiJson('/api/settings',{
        method:'PUT',
        body: { data:{ userName } },
      })
      await qc.invalidateQueries({ queryKey: queryKeys.settings })
      toast('Profile saved')
    } finally { setSaving(false) }
  }

  async function saveCat() {
    if (!catName.trim()) return
    const payload = { name:catName, type:catType, budgetGroup:catBudgetGroup||null, icon:catIcon, color:catColor }
    if (editCat) {
      await apiJson('/api/categories',{ method:'PUT', body:{id:editCat.id,...payload} })
      toast('Category updated')
    } else {
      await apiJson('/api/categories',{ method:'POST', body:payload })
      toast('Category added')
    }
    await qc.invalidateQueries({ queryKey: queryKeys.categories() })
    setShowCatForm(false); resetCatForm()
  }

  function resetCatForm() {
    setCatName(''); setCatBudgetGroup(''); setCatIcon('📦'); setCatColor('#6366f1'); setEditCat(null); setCatType('expense')
  }
  function openEditCat(cat: Category) {
    setEditCat(cat); setCatName(cat.name); setCatType(cat.type as 'income'|'expense'|'both')
    setCatBudgetGroup(cat.budgetGroup??''); setCatIcon(cat.icon); setCatColor(cat.color); setShowCatForm(true)
  }
  async function deleteCat(id: string) {
    await apiDelete(`/api/categories?id=${id}`)
    await qc.invalidateQueries({ queryKey: queryKeys.categories() })
    setDeleteConfirm(null); toast('Category deleted')
  }

  const incomeCategories = categories.filter(c => c.type==='income' || c.type==='both')
  const expenseCategories = categories.filter(c => c.type==='expense' || c.type==='both')

  const factCategories = ['all', ...Array.from(new Set(facts.map(f=>f.category)))]
  const filteredFacts = filterCat==='all' ? facts : facts.filter(f=>f.category===filterCat)
  const verifiedCount = facts.filter(f=>f.verifiedByUser).length

  // ── Section renderers ────────────────────────────────────────────────────────

  function renderProfile() {
    return (
      <div className="settings-section">
        <SectionHeader icon={User} title="Profile information" subtitle="Display name used in the app" />
        <div style={{ display:'flex', alignItems:'center', gap:20 }}>
          <div style={{ width:72, height:72, borderRadius:'50%', flexShrink:0,
            background:'var(--accent-green)',
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:28, fontWeight:700, color:'var(--text-inverse)' }}>
            {userName.charAt(0)?.toUpperCase() ?? '?'}
          </div>
          <div style={{ flex:1 }}>
            <label className="label" htmlFor="settings-name">Display name</label>
            <input id="settings-name" type="text" value={userName}
              onChange={e=>setUserName(e.target.value)}
              placeholder="Enter your name" className="input" />
          </div>
        </div>
        <div>
          <button className="btn btn-primary btn-sm" onClick={saveProfile} disabled={saving}>
            <Save size={14} />
            {saving ? 'Saving...' : 'Save changes'}
          </button>
        </div>
      </div>
    )
  }

  function renderAppearance() {
    return (
      <div className="settings-section">
        <SectionHeader icon={Palette} title="Appearance" subtitle="Display mode" />
        <div className="surface-row" style={{ justifyContent:'space-between' }}>
          <div style={{ display:'flex', alignItems:'center', gap:12 }}>
            {theme==='dark' ? <Moon size={18} /> : <Sun size={18} />}
            <div>
              <div style={{ fontSize:14, fontWeight:500 }}>{theme==='dark' ? 'Dark mode' : 'Light mode'}</div>
              <div style={{ fontSize:12, color:'var(--text-secondary)' }}>
                {theme==='dark' ? 'Best for dark environments' : 'Best for daylight'}
              </div>
            </div>
          </div>
          <button onClick={toggleTheme} aria-label="Toggle theme" style={{
            width:48, height:26, borderRadius:13, border:'none', cursor:'pointer',
            background:'var(--accent-green)',
            position:'relative', transition:'background 0.2s',
          }}>
            <motion.div style={{ position:'absolute', top:3, width:20, height:20,
              borderRadius:'50%', background:'#fff', boxShadow:'0 1px 4px rgba(0,0,0,0.3)' }}
              animate={{ left: theme==='dark'?'100%':'3px', x: theme==='dark'?'calc(-100% - 3px)':0 }}
              transition={{ type:'spring', stiffness:500, damping:30 }} />
          </button>
        </div>
      </div>
    )
  }

  function renderMemory() {
    return (
      <div className="settings-section" style={{ gap:20 }}>
        <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:16 }}>
          <SectionHeader icon={Brain} title="AI Memory"
            subtitle="What the assistant remembers about you" />
          <div className="stat-strip" style={{ gap:'var(--space-4)', flexShrink:0 }}>
            <Stat label="Total facts" value={facts.length} />
            <Stat label="Confirmed" value={verifiedCount} color="var(--accent-green)" />
          </div>
        </div>

        {/* Category filter */}
        <div style={{ display:'flex', gap:6, flexWrap:'wrap', alignItems:'center' }}>
          <Filter size={12} color="var(--text-secondary)" />
          {factCategories.map(cat => {
            const active = filterCat === cat
            const color = CATEGORY_COLORS[cat] ?? 'var(--accent-blue)'
            return (
              <button
                key={cat}
                onClick={() => setFilterCat(cat)}
                className={`chip-toggle${active ? ' active' : ''}`}
                style={active ? {
                  borderColor: color,
                  background: `color-mix(in srgb, ${color} 10%, transparent)`,
                  color,
                } : undefined}
              >
                {cat==='all' ? 'All' : CATEGORY_LABELS[cat]??cat}
              </button>
            )
          })}
        </div>

        {/* Facts list */}
        {factsLoading ? (
          <div style={{ color:'var(--text-secondary)', textAlign:'center', padding:32 }}>Loading...</div>
        ) : filteredFacts.length===0 ? (
          <div style={{ textAlign:'center', padding:40, color:'var(--text-secondary)',
            border:'1px dashed var(--surface-border)', borderRadius:12 }}>
            <Brain size={28} style={{ opacity:0.25, display:'block', margin:'0 auto 8px' }} />
            No facts yet. Chat with AI to get started.
          </div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:8, maxHeight:420, overflowY:'auto', paddingRight:4 }}>
            {filteredFacts.map(fact => {
              const catColor = CATEGORY_COLORS[fact.category] ?? 'var(--surface-border)'
              return (
                <motion.div key={fact.id} layout
                  style={{ background:'var(--surface)',
                    border:`1px solid ${fact.verifiedByUser ? `color-mix(in srgb, var(--accent-green) 20%, transparent)` : 'var(--surface-border)'}`,
                    borderLeft:`3px solid ${catColor}`,
                    borderRadius:10, padding:'12px 14px',
                    display:'flex', gap:12, alignItems:'flex-start' }}>
                  {/* Left */}
                  <div style={{ minWidth:80, flexShrink:0 }}>
                    <div style={{ fontSize:11, fontWeight:600, marginBottom:4, color:catColor }}>
                      {CATEGORY_LABELS[fact.category]??fact.category}
                    </div>
                    <ImportanceDots value={fact.importance} />
                    <div style={{ fontSize:10, color:'var(--text-secondary)', marginTop:2 }}>{fact.importance}/10</div>
                  </div>
                  {/* Middle */}
                  <div style={{ flex:1, minWidth:0 }}>
                    <div style={{ fontSize:13, lineHeight:1.5, marginBottom: fact.topics.length ? 5 : 0 }}>
                      {fact.verifiedByUser && <Shield size={11} color="var(--accent-green)" style={{ marginRight:4, verticalAlign:'middle', display:'inline' }} />}
                      {fact.fact}
                    </div>
                    {fact.topics.length>0 && (
                      <div style={{ display:'flex', gap:4, flexWrap:'wrap' }}>
                        {fact.topics.map(t => (
                          <span key={t} style={{ fontSize:10, padding:'1px 6px', borderRadius:8,
                            background:'var(--surface)', border:'1px solid var(--surface-border)',
                            color:'var(--text-secondary)' }}>{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {/* Right actions */}
                  <div style={{ display:'flex', gap:4, flexShrink:0 }}>
                    {!fact.verifiedByUser && (
                      <button onClick={() => verifyFact.mutate(fact)} title="Confirm"
                        className="btn btn-ghost btn-sm"
                        style={{ padding:5, color:'var(--accent-green)', border:'1px solid var(--surface-border)' }}>
                        <CheckCircle size={13} />
                      </button>
                    )}
                    <button onClick={() => setDeleteFactTarget(fact)} title="Delete"
                      className="btn btn-ghost btn-sm"
                      style={{ padding:5, border:'1px solid var(--surface-border)' }}>
                      <Trash2 size={13} />
                    </button>
                  </div>
                </motion.div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  function renderDigest() {
    const isGenerating = generateDigest.isPending
    return (
      <div className="settings-section">
        <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between', gap:12 }}>
          <SectionHeader icon={FileText} title="Monthly digest"
            subtitle="AI summarizes your finances and suggests actions" />
          <button onClick={() => generateDigest.mutate()} disabled={isGenerating}
            className="btn btn-primary btn-sm"
            style={{ flexShrink:0, whiteSpace:'nowrap' }}>
            {isGenerating
              ? <><RefreshCw size={13} style={{ animation:'spin 1s linear infinite' }} /> Generating...</>
              : <><Sparkles size={13} /> Generate new digest</>}
          </button>
        </div>

        {isGenerating && (
          <div style={{ background:'var(--surface)', border:'1px solid var(--surface-border)', borderRadius:12,
            padding:24, textAlign:'center', color:'var(--text-secondary)', fontSize:13 }}>
            <RefreshCw size={20} style={{ animation:'spin 1s linear infinite', display:'block', margin:'0 auto 8px' }} />
            AI is analyzing your financial data... (5-15 seconds)
          </div>
        )}

        {!isGenerating && !latestDigest && !digestLoading && (
          <div style={{ textAlign:'center', padding:48, color:'var(--text-secondary)',
            border:'1px dashed var(--surface-border)', borderRadius:12, fontSize:13 }}>
            <FileText size={28} style={{ opacity:0.25, display:'block', margin:'0 auto 10px' }} />
            No digests yet. Click &quot;Generate new digest&quot; to get started.
          </div>
        )}

        {latestDigest && !isGenerating && (
          <div style={{ background:'var(--surface)', border:'1px solid var(--surface-border)', borderRadius:12, padding:24 }}>
            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20,
              paddingBottom:14, borderBottom:'1px solid var(--surface-border)' }}>
              <div>
                <div style={{ fontSize:14, fontWeight:700 }}>Monthly digest {latestDigest.generatedForMonth}</div>
                <div style={{ fontSize:11, color:'var(--text-secondary)', marginTop:2 }}>
                  Generated at {new Date(latestDigest.createdAt).toLocaleString('en-US')}
                </div>
              </div>
              <span className="badge badge-green">Latest</span>
            </div>
            <DigestContent content={latestDigest.content} />
          </div>
        )}
      </div>
    )
  }

  function renderCategories() {
    return (
      <div className="settings-section" style={{ gap:20 }}>
        <div style={{ display:'flex', alignItems:'flex-start', justifyContent:'space-between' }}>
          <SectionHeader icon={Tag} title="Manage categories"
            subtitle="Customize income and expense categories" />
          <button onClick={() => { resetCatForm(); setShowCatForm(true) }}
            className="btn btn-primary btn-sm" style={{ flexShrink:0 }}>
            <Plus size={13} /> Add category
          </button>
        </div>

        <AnimatePresence>
          {showCatForm && (
            <motion.div initial={{ opacity:0, height:0 }} animate={{ opacity:1, height:'auto' }}
              exit={{ opacity:0, height:0 }}
              style={{ background:'var(--bg-tertiary)', border:'1px solid var(--surface-border)',
                borderRadius:12, padding:16, overflow:'hidden' }}>
              <div style={{ fontSize:14, fontWeight:600, marginBottom:12 }}>{editCat ? 'Edit category' : 'New category'}</div>
              {/* Icons */}
              <div style={{ display:'flex', gap:6, flexWrap:'wrap', marginBottom:12,
                maxHeight:140, overflowY:'auto', paddingRight:4 }}>
                {CAT_ICONS.map(i => (
                  <button key={i} onClick={()=>setCatIcon(i)} style={{
                    fontSize:18, width:38, height:38, borderRadius:8, cursor:'pointer',
                    border:`2px solid ${catIcon===i ? catColor : 'var(--surface-border)'}`,
                    background: catIcon===i ? `${catColor}20` : 'var(--surface)',
                  }}>{i}</button>
                ))}
              </div>
              {/* Colors */}
              <div style={{ display:'flex', gap:8, flexWrap:'wrap', marginBottom:12 }}>
                {CAT_COLORS.map(c => (
                  <button key={c} onClick={()=>setCatColor(c)} aria-label={`Color ${c}`} style={{
                    width:26, height:26, borderRadius:'50%', background:c, cursor:'pointer',
                    border:`3px solid ${catColor===c ? 'var(--text-primary)' : 'transparent'}`,
                  }} />
                ))}
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'1fr auto', gap:10, alignItems:'end', marginBottom:12 }}>
                <div>
                  <label className="label">Category name</label>
                  <input type="text" value={catName} onChange={e=>setCatName(e.target.value)}
                    placeholder="Example: Coffee" className="input" />
                </div>
                <div>
                  <label className="label">Type</label>
                  <Select value={catType} onChange={v=>setCatType(v as 'income'|'expense'|'both')}
                    options={[{value:'income',label:'Income'},{value:'expense',label:'Expense'},{value:'both',label:'Both'}]} />
                </div>
              </div>
              {(catType==='expense'||catType==='both') && (
                <div style={{ marginBottom:12 }}>
                  <label className="label" style={{ marginBottom:6, display:'block' }}>50/30/20 group</label>
                  <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                    {BUDGET_GROUPS.map(opt => {
                      const active = catBudgetGroup === opt.value
                      return (
                        <button key={opt.value} type="button" onClick={()=>setCatBudgetGroup(opt.value)}
                          className={`chip-toggle${active ? ' active' : ''}`}
                          style={active ? {
                            borderColor: opt.color,
                            background: `${opt.color}20`,
                            color: opt.color,
                          } : undefined}>
                          {opt.label}
                        </button>
                      )
                    })}
                  </div>
                </div>
              )}
              <div style={{ display:'flex', gap:8, justifyContent:'flex-end' }}>
                <button className="btn btn-secondary btn-sm" onClick={()=>{setShowCatForm(false);resetCatForm()}}>Cancel</button>
                <button className="btn btn-primary btn-sm" onClick={saveCat} disabled={!catName.trim()}>Save</button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="settings-category-grid">
          <div>
            <div className="stat-label" style={{ marginBottom:8 }}>
              Income ({incomeCategories.length})
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:4 }}>
              {incomeCategories.map(cat => <CatRow key={cat.id} cat={cat} onEdit={openEditCat} onDelete={setDeleteConfirm} />)}
            </div>
          </div>
          <div>
            <div className="stat-label" style={{ marginBottom:8 }}>
              Expense ({expenseCategories.length})
            </div>
            <div style={{ display:'flex', flexDirection:'column', gap:4 }}>
              {expenseCategories.map(cat => <CatRow key={cat.id} cat={cat} onEdit={openEditCat} onDelete={setDeleteConfirm} />)}
            </div>
          </div>
        </div>
      </div>
    )
  }

  function renderAbout() {
    return (
      <div className="settings-section">
        <SectionHeader icon={Info} title="About" subtitle="Version information" />
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          {[
            { label:'Version', value:'1.0.0' },
            { label:'AI Model', value:'Claude Sonnet 4.6' },
            { label:'Tech Stack', value:'Next.js + FastAPI + PostgreSQL' },
            { label:'Created by', value:'WealthLog Team' },
          ].map(item => (
            <div key={item.label} className="surface-row" style={{ justifyContent:'space-between' }}>
              <span style={{ fontSize:13, color:'var(--text-secondary)' }}>{item.label}</span>
              <span style={{ fontSize:13, fontWeight:600 }}>{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const sectionContent: Record<SectionId, () => React.ReactElement> = {
    profile: renderProfile,
    appearance: renderAppearance,
    memory: renderMemory,
    digest: renderDigest,
    categories: renderCategories,
    about: renderAbout,
  }

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <PageTransition>
      <div>
        {/* Page header */}
        <PageHeader
          eyebrow="Preferences"
          title="Settings"
          subtitle="Customize the app to your preferences"
        />

        {/* Two-column layout */}
        <div className="settings-shell-grid">
          {/* Left nav */}
          <nav className="settings-nav">
            {SECTIONS.map(sec => {
              const Icon = sec.icon
              const active = activeSection === sec.id
              return (
                <button key={sec.id} onClick={() => setActiveSection(sec.id)}
                  className={`settings-nav-item${active ? ' active' : ''}`}>
                  <Icon size={15} />
                  <span style={{ flex:1 }}>{sec.label}</span>
                  {active && <ChevronRight size={13} />}
                </button>
              )
            })}
          </nav>

          {/* Right content */}
          <AnimatePresence mode="wait">
            <motion.div key={activeSection}
              initial={{ opacity:0, x:8 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-8 }}
              transition={{ duration:0.15 }}
              className="card" style={{ padding:28, minHeight:300 }}>
              {sectionContent[activeSection]()}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Delete fact confirm */}
      <Portal>
        {deleteFactTarget && (
          <>
            <div className="overlay" onClick={() => setDeleteFactTarget(null)} />
            <div className="modal" style={{ padding:28, textAlign:'center' }}>
              <div style={{ width:48, height:48, borderRadius:'50%', background:'var(--accent-red-subtle)', display:'flex', alignItems:'center', justifyContent:'center', margin:'0 auto 12px' }}>
                <Trash2 size={22} style={{ color:'var(--accent-red)' }} />
              </div>
              <h3 style={{ fontSize:16, fontWeight:700, marginBottom:8 }}>Delete this fact?</h3>
              <p style={{ fontSize:13, color:'var(--text-secondary)', marginBottom:24 }}>{deleteFactTarget.fact}</p>
              <div style={{ display:'flex', gap:10 }}>
                <button className="btn btn-secondary" style={{ flex:1 }} onClick={()=>setDeleteFactTarget(null)}>Cancel</button>
                <button className="btn btn-danger" style={{ flex:1 }} onClick={async()=>{
                  await deleteFact.mutateAsync(deleteFactTarget.id)
                  toast('Fact deleted'); setDeleteFactTarget(null)
                }}>Delete</button>
              </div>
            </div>
          </>
        )}
      </Portal>

      {/* Delete category confirm */}
      <Portal>
        {deleteConfirm && (
          <>
            <div className="overlay" onClick={()=>setDeleteConfirm(null)} />
            <div className="modal" style={{ padding:28, textAlign:'center' }}>
              <div style={{ width:48, height:48, borderRadius:'50%', background:'var(--accent-red-subtle)', display:'flex', alignItems:'center', justifyContent:'center', margin:'0 auto 12px' }}>
                <AlertTriangle size={22} style={{ color:'var(--accent-red)' }} />
              </div>
              <h3 style={{ fontSize:16, fontWeight:700, marginBottom:8 }}>Delete category?</h3>
              <p style={{ fontSize:13, color:'var(--text-secondary)', marginBottom:24 }}>
                Related transactions will not be deleted, but they will lose this category.
              </p>
              <div style={{ display:'flex', gap:10 }}>
                <button className="btn btn-secondary" style={{ flex:1 }} onClick={()=>setDeleteConfirm(null)}>Cancel</button>
                <button className="btn btn-danger" style={{ flex:1 }} onClick={()=>deleteCat(deleteConfirm!)}>Delete</button>
              </div>
            </div>
          </>
        )}
      </Portal>

      <style jsx>{`
        .settings-shell-grid {
          display: grid;
          grid-template-columns: 200px minmax(0, 1fr);
          gap: 24px;
          align-items: start;
        }

        .settings-nav {
          position: sticky;
          top: calc(var(--header-height) + var(--space-6));
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .settings-section,
        :global(.settings-section) {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .settings-nav :global(.settings-nav-item) {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 9px 12px;
          border-radius: var(--radius-md);
          border: none;
          cursor: pointer;
          text-align: left;
          background: transparent;
          color: var(--text-secondary);
          font-weight: 400;
          font-size: 13px;
          transition: color var(--duration-fast) ease, background var(--duration-fast) ease;
        }

        .settings-nav :global(.settings-nav-item:hover) {
          background: var(--surface-hover);
          color: var(--text-primary);
        }

        .settings-nav :global(.settings-nav-item.active) {
          background: var(--accent-green-subtle);
          color: var(--accent-green);
          font-weight: 600;
        }

        .settings-category-grid,
        :global(.settings-category-grid) {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
        }

        @media (max-width: 900px) {
          .settings-shell-grid {
            grid-template-columns: 1fr;
          }

          .settings-nav {
            position: static;
            flex-direction: row;
            overflow-x: auto;
            padding-bottom: 4px;
            scrollbar-width: thin;
          }

          .settings-nav :global(.settings-nav-item) {
            flex: 0 0 auto;
          }
        }

        @media (max-width: 720px) {
          .settings-category-grid,
          :global(.settings-category-grid) {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </PageTransition>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, subtitle }: {
  icon: React.ElementType; title: string; subtitle: string
}) {
  return (
    <div className="section-header">
      <div className="icon-tile">
        <Icon size={18} />
      </div>
      <div>
        <div className="section-header-title">{title}</div>
        <div className="section-header-sub">{subtitle}</div>
      </div>
    </div>
  )
}

function CatRow({ cat, onEdit, onDelete }: {
  cat: Category
  onEdit: (c: Category) => void
  onDelete: (id: string) => void
}) {
  return (
    <div className="surface-row" style={{ gap:8, padding:'8px 10px' }}>
      <span style={{ fontSize:15 }}>{cat.icon}</span>
      <span style={{ flex:1, fontSize:13, fontWeight:500, display:'flex', alignItems:'center', gap:5, flexWrap:'wrap' }}>
        {cat.name}
        {cat.budgetGroup && (
          <span style={{ fontSize:9, padding:'1px 5px', borderRadius:4, lineHeight:'14px', fontWeight:600,
            background: cat.budgetGroup==='needs' ? '#3b82f615' : '#10b98115',
            color: cat.budgetGroup==='needs' ? '#3b82f6' : '#10b981' }}>
            {cat.budgetGroup==='needs' ? 'Needs' : 'Wants'}
          </span>
        )}
      </span>
      <div style={{ width:9, height:9, borderRadius:'50%', background:cat.color, flexShrink:0 }} />
      {!cat.isDefault && (
        <>
          <button onClick={()=>onEdit(cat)} className="btn btn-ghost btn-sm" aria-label="Edit category"
            style={{ width:24,height:24,padding:0,borderRadius:'50%' }}><Edit2 size={11}/></button>
          <button onClick={()=>onDelete(cat.id)} className="btn btn-ghost btn-sm" aria-label="Delete category"
            style={{ width:24,height:24,padding:0,borderRadius:'50%',color:'var(--accent-red)' }}><Trash2 size={11}/></button>
        </>
      )}
    </div>
  )
}
