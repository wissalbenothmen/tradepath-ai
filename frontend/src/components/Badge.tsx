type Variant = 'green' | 'red' | 'yellow' | 'blue' | 'gray' | 'orange'

const styles: Record<Variant, string> = {
  green: 'bg-green-100 text-green-800',
  red: 'bg-red-100 text-red-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  blue: 'bg-blue-100 text-blue-800',
  gray: 'bg-gray-100 text-gray-700',
  orange: 'bg-orange-100 text-orange-800',
}

interface BadgeProps {
  label: string
  variant: Variant
}

export default function Badge({ label, variant }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[variant]}`}>
      {label}
    </span>
  )
}

export function statusVariant(status: string): Variant {
  const map: Record<string, Variant> = {
    draft: 'gray', screening: 'blue', classification: 'blue',
    declaration_ready: 'yellow', filed: 'yellow', cleared: 'green',
    hold: 'orange', blocked: 'red',
    clear: 'green', potential_match: 'yellow', positive_match: 'red',
    CLEAR: 'green', LICENSE_REQUIRED: 'yellow', QUOTA_CHECK: 'orange', PROHIBITED: 'red',
    pending: 'gray', classified: 'blue', confirmed: 'green', disputed: 'orange', escalated: 'red',
  }
  return map[status] || 'gray'
}
