import React, { useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useProgress } from '../context/ProgressContext'

export default function ProgressPanel() {
  const { user } = useAuth()
  const { progress, refresh } = useProgress()

  useEffect(() => { if (user) refresh(user.learner_id, true) }, [user])

  if (!progress) return (
    <div style={{ padding: 20, color: '#718096' }}>
      {user ? 'Loading progress…' : 'Sign in to track your progress.'}
    </div>
  )

  const { xp, level, badges, topics_seen, completed_projects, topic_progress } = progress

  return (
    <div style={{ overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 14, WebkitOverflowScrolling: 'touch' }}>

      {/* Stats */}
      <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 12, padding: 14 }}>
        <h3 style={{ color: '#90cdf4', fontSize: '.93rem', marginBottom: 10 }}>📊 Your Stats</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          {[
            { val: xp, key: 'Total XP' },
            { val: level.charAt(0).toUpperCase() + level.slice(1), key: 'Level' },
            { val: topics_seen.length, key: 'Topics' },
            { val: completed_projects.length, key: 'Courses Done' },
          ].map(s => (
            <div key={s.key} style={{ background: '#0f1117', border: '1px solid #2d3748', borderRadius: 8, padding: '10px 12px' }}>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#63b3ed' }}>{s.val}</div>
              <div style={{ fontSize: '.7rem', color: '#718096', marginTop: 2 }}>{s.key}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Badges */}
      <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 12, padding: 14 }}>
        <h3 style={{ color: '#90cdf4', fontSize: '.93rem', marginBottom: 10 }}>🏅 Badges</h3>
        {badges.length ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {badges.map(b => (
              <span key={b} style={{ display: 'inline-block', background: 'rgba(139,92,246,.12)', border: '1px solid rgba(139,92,246,.25)', borderRadius: 999, padding: '3px 10px', fontSize: '.76rem', color: '#c4b5fd' }}>
                {b}
              </span>
            ))}
          </div>
        ) : <span style={{ fontSize: '.82rem', color: '#4a5568' }}>No badges yet — keep learning!</span>}
      </div>

      {/* Topic progress */}
      <div style={{ background: '#1a202c', border: '1px solid #2d3748', borderRadius: 12, padding: 14 }}>
        <h3 style={{ color: '#90cdf4', fontSize: '.93rem', marginBottom: 10 }}>📈 Topic Progress</h3>
        {Object.keys(topic_progress).length ? (
          Object.values(topic_progress).map(tp => {
            const avg = tp.quiz_scores.length ? Math.round(tp.quiz_scores.reduce((a, b) => a + b, 0) / tp.quiz_scores.length) : null
            return (
              <div key={tp.topic} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #2d3748', fontSize: '.84rem', flexWrap: 'wrap', gap: 4 }}>
                <span>{tp.topic}</span>
                <span style={{ fontSize: '.75rem', color: '#718096' }}>
                  {tp.lessons_completed} lessons · {tp.exercises_passed}/{tp.exercises_attempted} ex
                  {avg !== null ? ` · ${avg}%` : ''}
                </span>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: tp.weak ? '#fc8181' : '#68d391', flexShrink: 0 }} />
              </div>
            )
          })
        ) : <span style={{ fontSize: '.82rem', color: '#4a5568' }}>Start chatting to track topics.</span>}
      </div>

    </div>
  )
}
