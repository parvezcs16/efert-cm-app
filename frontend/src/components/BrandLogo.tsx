import { cn } from '@/lib/utils'

/** EFERT mark + app name. `size` controls the mark height. */
export function BrandLogo({
  size = 'sm',
  showName = true,
  className,
}: {
  size?: 'sm' | 'lg'
  showName?: boolean
  className?: string
}) {
  return (
    <span className={cn('flex items-center gap-2', className)}>
      <img
        src="/efert-logo.png"
        alt="EFERT"
        className={size === 'lg' ? 'h-16 w-auto' : 'h-8 w-auto'}
      />
      {showName && (
        <span className="flex flex-col leading-tight">
          <span
            className={cn(
              'font-bold tracking-wide text-brand-dark',
              size === 'lg' ? 'text-2xl' : 'text-base',
            )}
          >
            EFERT
          </span>
          <span
            className={cn(
              'text-muted-foreground',
              size === 'lg' ? 'text-sm' : 'text-[11px] uppercase tracking-wider',
            )}
          >
            Central Mess
          </span>
        </span>
      )}
    </span>
  )
}

/** Thin dark-green -> green -> lime strip echoing the logo's layers. */
export function BrandStripe({ className }: { className?: string }) {
  return (
    <div
      className={cn('h-1 w-full bg-gradient-to-r from-brand-dark via-brand to-brand-lime', className)}
    />
  )
}
