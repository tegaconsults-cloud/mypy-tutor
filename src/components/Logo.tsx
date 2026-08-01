import React from 'react'

interface LogoProps {
  size?: number
  className?: string
  style?: React.CSSProperties
  /** 'full' shows the complete logo; 'icon' shows just the icon mark cropped */
  variant?: 'full' | 'icon'
  shape?: 'circle' | 'rounded' | 'square' | 'none'
}

/**
 * Official MyPy Tutor logo — mypytutor logo.jpg
 * Blue (#0D47A1) & Gold (#E0A300) brand mark with graduation cap,
 * Python logo, open book, "MYPY TUTOR · LEARN PYTHON. BUILD THE FUTURE."
 * Do NOT alter proportions, colors, or symbolism.
 */
export default function Logo({
  size = 36,
  className = '',
  style,
  variant = 'full',
  shape = 'none',
}: LogoProps) {
  const radius =
    shape === 'circle'  ? '50%'  :
    shape === 'rounded' ? '16px' :
    shape === 'square'  ? '0'    : undefined

  return (
    <div
      className={className}
      style={{
        width:  size,
        height: size,
        borderRadius: radius,
        overflow: radius ? 'hidden' : undefined,
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: shape !== 'none' ? '#fff' : 'transparent',
        ...style,
      }}
    >
      <img
        src="/icons/mypytutor_logo.jpg"
        alt="MyPy Tutor — Learn Python. Build the Future."
        width={size}
        height={size}
        style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
        draggable={false}
        onError={e => {
          // Fallback to png
          const img = e.target as HTMLImageElement
          if (!img.src.endsWith('.png')) img.src = '/icons/mypytutor_logo.png'
        }}
      />
    </div>
  )
}
