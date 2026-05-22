import { useEffect, useState } from 'react'

interface Props {
  text: string
  /** Characters per second. */
  cps?: number
  /** Show blinking cursor while streaming. */
  cursor?: boolean
  className?: string
  /** Force-skip animation (e.g. for screenshots). */
  instant?: boolean
}

/** Renders ``text`` one character at a time to imitate an LLM stream. */
export default function StreamingText({
  text,
  cps = 60,
  cursor = true,
  className = '',
  instant = false,
}: Props) {
  const [shown, setShown] = useState(instant ? text : '')

  useEffect(() => {
    if (instant) {
      setShown(text)
      return
    }
    setShown('')
    if (!text) return
    let i = 0
    const ms = Math.max(8, 1000 / cps)
    const interval = window.setInterval(() => {
      i += 1
      setShown(text.slice(0, i))
      if (i >= text.length) window.clearInterval(interval)
    }, ms)
    return () => window.clearInterval(interval)
  }, [text, cps, instant])

  const streaming = shown.length < text.length
  return (
    <span className={className}>
      {shown}
      {cursor && streaming && (
        <span
          className="inline-block w-[2px] h-[1em] bg-ai-600 align-text-bottom ml-0.5 animate-cursor-blink"
          aria-hidden="true"
        />
      )}
    </span>
  )
}
