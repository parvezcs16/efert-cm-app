import { Star } from 'lucide-react'

import { cn } from '@/lib/utils'

export function StarRating({
  value,
  onChange,
  size = 20,
}: {
  value: number
  onChange: (value: number) => void
  size?: number
}) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          onClick={() => onChange(n)}
          className="text-muted-foreground transition-colors hover:text-amber-500"
          aria-label={`${n} star${n === 1 ? '' : 's'}`}
        >
          <Star
            size={size}
            className={cn(n <= value && 'fill-amber-500 text-amber-500')}
          />
        </button>
      ))}
    </div>
  )
}
