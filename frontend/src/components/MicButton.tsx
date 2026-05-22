import { Mic, MicOff, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

interface Props {
  /** Called when the user finishes recording. Receives the audio Blob. */
  onRecorded?: (blob: Blob) => void
  /** Compact pill style for inline use. */
  size?: 'sm' | 'md'
  /** Label shown next to the icon (omit for icon-only). */
  label?: string
}

/**
 * "Whisper-powered" mic affordance. Uses MediaRecorder if available; otherwise
 * falls back to a disabled state that explains the UX intent.
 */
export default function MicButton({ onRecorded, size = 'md', label = 'Whisper voice note' }: Props) {
  const [recording, setRecording] = useState(false)
  const [duration, setDuration] = useState(0)
  const [supported, setSupported] = useState(true)
  const recRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const intervalRef = useRef<number | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    setSupported(!!navigator.mediaDevices && typeof window.MediaRecorder !== 'undefined')
  }, [])

  const start = async () => {
    if (!supported) return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      chunksRef.current = []
      rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach((t) => t.stop())
        onRecorded?.(blob)
      }
      rec.start()
      recRef.current = rec
      setRecording(true)
      setDuration(0)
      intervalRef.current = window.setInterval(() => setDuration((d) => d + 1), 1000)
    } catch {
      setSupported(false)
    }
  }
  const stop = () => {
    recRef.current?.stop()
    recRef.current = null
    setRecording(false)
    if (intervalRef.current != null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  const pad = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3 py-2 text-sm'
  if (!supported) {
    return (
      <button disabled className={`btn-secondary ${pad} opacity-60`} title="Browser does not support voice capture">
        <MicOff size={size === 'sm' ? 14 : 16} />
        {label}
      </button>
    )
  }
  return (
    <button
      onClick={recording ? stop : start}
      className={`relative inline-flex items-center gap-2 rounded-lg font-semibold transition ${pad} ${
        recording
          ? 'bg-red-600 hover:bg-red-700 text-white animate-pulse-glow'
          : 'btn-ai'
      }`}
    >
      {recording ? <Mic size={size === 'sm' ? 14 : 16} /> : <Sparkles size={size === 'sm' ? 14 : 16} />}
      {recording ? `Recording… ${formatDuration(duration)}` : label}
    </button>
  )
}

function formatDuration(s: number): string {
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${r.toString().padStart(2, '0')}`
}
