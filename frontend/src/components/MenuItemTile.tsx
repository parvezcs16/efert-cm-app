import { Minus, Plus, UtensilsCrossed } from 'lucide-react'

import { Button } from '@/components/ui/button'
import type { MenuBrowseItem } from '@/lib/types'
import { cn } from '@/lib/utils'

/** Square item photo, or a neutral placeholder when none is attached. */
export function MenuItemImage({
  src,
  alt,
  className,
}: {
  src: string | null
  alt: string
  className?: string
}) {
  if (!src) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-secondary text-brand-lime',
          className,
        )}
      >
        <UtensilsCrossed className="size-1/3" />
      </div>
    )
  }
  return <img src={src} alt={alt} loading="lazy" className={cn('object-cover', className)} />
}

/** Orderable menu card used by both employee ordering and the guest portal. */
export function MenuItemTile({
  item,
  quantity,
  onAdjust,
}: {
  item: MenuBrowseItem
  quantity: number
  onAdjust: (delta: number) => void
}) {
  return (
    <div
      className={cn(
        'flex overflow-hidden rounded-lg border bg-card transition-shadow',
        quantity > 0 && 'border-primary ring-1 ring-primary',
      )}
    >
      <MenuItemImage src={item.image_url} alt={item.name} className="size-24 shrink-0 sm:size-28" />
      <div className="flex min-w-0 flex-1 flex-col justify-between gap-2 p-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{item.name}</p>
          {item.description && (
            <p className="line-clamp-2 text-xs text-muted-foreground">{item.description}</p>
          )}
        </div>
        <div className="flex items-center justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            size="icon-sm"
            onClick={() => onAdjust(-1)}
            disabled={quantity === 0}
            aria-label={`Remove one ${item.name}`}
          >
            <Minus />
          </Button>
          <span className="w-5 text-center text-sm font-medium">{quantity}</span>
          <Button
            type="button"
            size="icon-sm"
            onClick={() => onAdjust(1)}
            aria-label={`Add one ${item.name}`}
          >
            <Plus />
          </Button>
        </div>
      </div>
    </div>
  )
}
