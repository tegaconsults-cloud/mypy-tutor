import React from 'react'

interface LogoProps {
  /** Diameter in pixels */
  size?: number
  /** Extra className */
  className?: string
  /** Inline style overrides */
  style?: React.CSSProperties
  /** Border radius: 'circle' (50%), 'rounded' (20%), 'square' */
  shape?: 'circle' | 'rounded' | 'square'
}

/**
 * Official MyPy Tutor logo wrapped in a circle.
 * Replaces every 🐍 snake emoji used as a brand/logo icon.
 */
export default function Logo({ size = 32, className = '', style, shape = 'circle' }: LogoProps) {
  const radius = shape === 'circle' ? '50%' : shape === 'rounded' ? '20%' : '0'
  return (
    <div
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: radius,
        overflow: 'hidden',
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#fff',
        ...style,
      }}
    >
      <img
        src="/icons/mypytutor_logo.png"
        alt="MyPy Tutor"
        width={size}
        height={size}
        style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        draggable={false}
      />
    </div>
  )
}
