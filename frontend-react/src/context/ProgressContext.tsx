import React, { createContext, useCallback, useContext, useState } from 'react'
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
  const [progress, setProgress]         = useState<Progress | null>(null)
  const [progressError, setProgressError] = useState<string | null>(null)
  const [lastFetch, setLastFetch]       = useState(0)

  const refresh = useCallback(async (learnerId: string, force = false) => {
    const now = Date.now()
    // Respect the 60-second cache for passive calls, but always honour force=true
    // (called after chat responses so XP/level update without waiting 60 s).
    // Also bypass cache if server reports a newer updated_at than what we have
    // (handles admin tier changes becoming visible without a manual page reload).
    const serverUpdatedAt = (progress?.updated_at ?? 0) * 1000  // convert to ms
    const cacheStale = progress && now - lastFetch >= 60_000
    const adminChanged = progress && serverUpdatedAt > lastFetch
    if (!force && !cacheStale && !adminChanged) return
    try {
      const p = await getProgress(learnerId)
      if (p) {
        setProgress(p)
        setProgressError(null)
        setLastFetch(now)
      } else {
        setProgressError('Could not load progress. Check your connection.')
      }
    } catch (_) {
      setProgressError('Could not load progress. Check your connection.')
    }
  }, [progress, lastFetch])

  return (
    <ProgressContext.Provider value={{ progress, progressError, refresh }}>
      {children}
    </ProgressContext.Provider>
  )
}

export const useProgress = () => useContext(ProgressContext)
