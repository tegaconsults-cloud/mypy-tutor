import React, { createContext, useCallback, useContext, useRef, useState } from 'react'
import { getProgress } from '../api'

export interface TopicProgress {
  topic: string; lessons_completed: number
  exercises_attempted: number; exercises_passed: number
  quiz_scores: number[]; weak: boolean
}

export interface Progress {
  learner_id: string; level: string; tier: string; xp: number
  badges: string[]; topics_seen: string[]; knowledge_gaps: string[]
  current_course: string | null; current_course_step: number
  completed_projects: string[]; topic_progress: Record<string, TopicProgress>
  updated_at?: number   // Unix epoch — used to detect admin tier changes
}

interface ProgressCtx {
  progress: Progress | null
  progressError: string | null
  refresh: (learnerId: string, force?: boolean) => Promise<void>
}

const ProgressContext = createContext<ProgressCtx>({} as ProgressCtx)

export function ProgressProvider({ children }: { children: React.ReactNode }) {
  const [progress, setProgress]           = useState<Progress | null>(null)
  const [progressError, setProgressError] = useState<string | null>(null)

  // Use refs for lastFetch and progress snapshot used inside refresh so the
  // callback identity is stable — avoids re-creating refresh on every XP tick
  // which caused Header/XPBar/ChatPanel to re-render on every chat message.
  const lastFetchRef   = useRef(0)
  const progressRef    = useRef<Progress | null>(null)

  const refresh = useCallback(async (learnerId: string, force = false) => {
    const now     = Date.now()
    const last    = lastFetchRef.current
    const current = progressRef.current

    // Cache: skip if fetched <60s ago unless force=true or admin changed tier
    const serverUpdatedAt = (current?.updated_at ?? 0) * 1000
    const cacheStale      = current && now - last >= 60_000
    const adminChanged    = current && serverUpdatedAt > last
    if (!force && !cacheStale && !adminChanged) return

    try {
      const p = await getProgress(learnerId)
      if (p) {
        setProgress(p)
        progressRef.current  = p
        lastFetchRef.current = now
        setProgressError(null)
      } else {
        setProgressError('Could not load progress.')
      }
    } catch (_) {
      setProgressError('Could not load progress. Check your connection.')
    }
  }, []) // stable — no deps needed because we use refs

  return (
    <ProgressContext.Provider value={{ progress, progressError, refresh }}>
      {children}
    </ProgressContext.Provider>
  )
}

export const useProgress = () => useContext(ProgressContext)
