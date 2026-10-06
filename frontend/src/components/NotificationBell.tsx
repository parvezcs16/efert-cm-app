import { Bell, BellRing, CheckCheck, UtensilsCrossed, UserRoundPlus } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { InAppNotification, InAppNotificationType } from '@/lib/types'
import { cn } from '@/lib/utils'

// How often the header re-checks for new notifications (guest access
// requests should surface reasonably quickly).
const POLL_MS = 30_000

const TYPE_ICON: Record<InAppNotificationType, typeof Bell> = {
  DAILY_SERVED_SUMMARY: UtensilsCrossed,
  GUEST_REOPEN_REQUEST: UserRoundPlus,
}

function timeAgo(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

/** Header bell: unread badge plus a dropdown inbox of the employee's
 * in-app notifications (daily served summaries, guest access requests). */
export function NotificationBell() {
  const navigate = useNavigate()
  const [unread, setUnread] = useState(0)
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<InAppNotification[] | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const refreshCount = useCallback(() => {
    apiFetch<{ unread: number }>('/notifications/unread-count')
      .then((r) => setUnread(r.unread))
      .catch(() => {
        // Keep the last known count on a transient failure.
      })
  }, [])

  useEffect(() => {
    refreshCount()
    const timer = window.setInterval(refreshCount, POLL_MS)
    return () => window.clearInterval(timer)
  }, [refreshCount])

  useEffect(() => {
    if (!open) return
    setItems(null)
    apiFetch<InAppNotification[]>('/notifications')
      .then(setItems)
      .catch((err) => {
        toast.error(getErrorMessage(err))
        setItems([])
      })

    const onPointerDown = (e: PointerEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false)
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  const openNotification = async (n: InAppNotification) => {
    if (!n.read_at) {
      const readAt = new Date().toISOString()
      setItems((prev) => prev?.map((x) => (x.id === n.id ? { ...x, read_at: readAt } : x)) ?? prev)
      setUnread((u) => Math.max(0, u - 1))
      apiFetch(`/notifications/${n.id}/read`, { method: 'POST' }).catch(refreshCount)
    }
    if (n.link) {
      setOpen(false)
      navigate(n.link)
    }
  }

  const markAllRead = async () => {
    try {
      await apiFetch('/notifications/read-all', { method: 'POST' })
      const readAt = new Date().toISOString()
      setItems((prev) => prev?.map((x) => ({ ...x, read_at: x.read_at ?? readAt })) ?? prev)
      setUnread(0)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <Button
        variant="ghost"
        size="icon"
        aria-label={unread ? `Notifications (${unread} unread)` : 'Notifications'}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="relative"
      >
        {unread ? <BellRing className="text-primary" /> : <Bell />}
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold leading-none text-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-full z-20 mt-2 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-lg border bg-popover text-popover-foreground shadow-lg">
          <div className="flex items-center justify-between border-b px-4 py-2.5">
            <span className="text-sm font-semibold">Notifications</span>
            {unread > 0 && (
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={markAllRead}>
                <CheckCheck className="size-3.5" />
                Mark all read
              </Button>
            )}
          </div>
          <div className="max-h-[min(28rem,70vh)] overflow-y-auto">
            {items === null ? (
              <div className="flex justify-center p-6">
                <Spinner />
              </div>
            ) : items.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                You're all caught up.
              </p>
            ) : (
              <ul className="divide-y">
                {items.map((n) => {
                  const Icon = TYPE_ICON[n.type] ?? Bell
                  return (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => void openNotification(n)}
                        className={cn(
                          'flex w-full gap-3 px-4 py-3 text-left hover:bg-accent',
                          !n.read_at && 'bg-secondary/60',
                        )}
                      >
                        <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-primary">
                          <Icon className="size-4" />
                        </span>
                        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                          <span className="flex items-start justify-between gap-2">
                            <span className={cn('text-sm', !n.read_at && 'font-semibold')}>
                              {n.title}
                            </span>
                            {!n.read_at && (
                              <span className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" />
                            )}
                          </span>
                          <span className="whitespace-pre-line text-xs leading-relaxed text-muted-foreground">
                            {n.body}
                          </span>
                          <span className="text-[11px] text-muted-foreground/80">
                            {timeAgo(n.created_at)}
                          </span>
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
