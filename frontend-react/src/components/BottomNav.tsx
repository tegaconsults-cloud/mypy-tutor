import React, { memo } from 'react'
import { MessageSquare, BookOpen, Trophy, BarChart2, CreditCard } from 'lucide-react'

type Panel = 'chat' | 'courses' | 'quiz' | 'progress' | 'certificates' | 'pricing'

const TABS: { id: Panel; icon: React.ReactNode; label: string }[] = [
  { id: 'chat',     icon: <MessageSquare size={20} />, label: 'AI Tutor' },
  { id: 'courses',  icon: <BookOpen size={20} />,      label: 'Learn' },
  { id: 'quiz',     icon: <Trophy size={20} />,        label: 'Quiz' },
  { id: 'progress', icon: <BarChart2 size={20} />,     label: 'Stats' },
  { id: 'pricing',  icon: <CreditCard size={20} />,    label: 'Plans' },
]

interface Props { panel: Panel; onPanelChange: (p: Panel) => void }

// Memoised — no framer-motion layout recalcs, pure CSS active state
const BottomNav = memo(function BottomNav({ panel, onPanelChange }: Props) {
  return (
    <nav className="bottom-nav safe-bottom shrink-0 px-1"
      style={{
        background: 'rgba(6,13,28,0.98)',
        borderTop: '1px solid rgba(13,71,161,0.25)',
        backdropFilter: 'blur(20px)',
      }}>
      {TABS.map(t => {
        const isActive = panel === t.id
        return (
          <button key={t.id} onClick={() => onPanelChange(t.id)}
            className="flex flex-col items-center gap-0.5 flex-1 py-2 px-1 rounded-xl relative"
            style={{
              color: isActive ? '#E0A300' : '#4d6080',
              minHeight: 52,
              transition: 'color 0.15s ease',
            }}>
            {/* Active indicator — CSS only, no layout recalculation */}
            <span
              style={{
                position: 'absolute', top: 0, left: '50%',
                transform: 'translateX(-50%)',
                width: 32, height: 2, borderRadius: 99,
                background: isActive ? '#E0A300' : 'transparent',
                transition: 'background 0.15s ease',
              }} />
            <span style={{ transform: isActive ? 'scale(1.1)' : 'scale(1)', transition: 'transform 0.15s ease' }}>
              {t.icon}
            </span>
            <span className="text-[9px] font-semibold tracking-wide">{t.label}</span>
          </button>
        )
      })}
    </nav>
  )
})

export default BottomNav
