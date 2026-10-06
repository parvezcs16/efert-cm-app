import { cn } from '@/lib/utils'

export interface CategoryNavEntry {
  id: string
  name: string
  count?: number
  /** Small trailing label, e.g. "Hidden" for an inactive category. */
  note?: string
}

/** Category picker: a sidebar on large screens, a horizontally scrolling
 * chip row on small ones. The parent shows only the selected category. */
export function CategoryNav({
  categories,
  selectedId,
  onSelect,
  className,
}: {
  categories: CategoryNavEntry[]
  selectedId: string | null
  onSelect: (id: string) => void
  className?: string
}) {
  if (categories.length === 0) return null

  return (
    <nav aria-label="Menu categories" className={cn('lg:sticky lg:top-24 lg:self-start', className)}>
      <p className="mb-2 hidden px-3 text-xs font-semibold tracking-wider text-muted-foreground uppercase lg:block">
        Categories
      </p>
      <ul className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 lg:mx-0 lg:flex-col lg:gap-1 lg:overflow-visible lg:px-0 lg:pb-0">
        {categories.map((category) => {
          const active = category.id === selectedId
          return (
            <li key={category.id} className="shrink-0">
              <button
                type="button"
                onClick={() => onSelect(category.id)}
                aria-current={active ? 'true' : undefined}
                className={cn(
                  'flex w-full items-center justify-between gap-3 rounded-full border px-3 py-1.5 text-left text-sm whitespace-nowrap transition-colors lg:rounded-md lg:border-0 lg:border-l-2 lg:py-2',
                  active
                    ? 'border-primary bg-accent font-medium text-primary'
                    : 'border-border bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground lg:border-transparent lg:bg-transparent',
                )}
              >
                <span>{category.name}</span>
                {category.note && (
                  <span className="text-xs text-muted-foreground italic">{category.note}</span>
                )}
                {category.count !== undefined && (
                  <span
                    className={cn(
                      'rounded-full px-1.5 text-xs',
                      active ? 'bg-primary text-primary-foreground' : 'bg-muted',
                    )}
                  >
                    {category.count}
                  </span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
