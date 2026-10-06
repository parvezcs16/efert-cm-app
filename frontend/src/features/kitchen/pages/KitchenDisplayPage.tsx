import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { apiFetch, getErrorMessage } from '@/lib/api'
import { employeeAuthStorage } from '@/lib/auth-storage'
import type { KitchenBoardOrder, KitchenStation, Location, OrderStatus } from '@/lib/types'
import { cn } from '@/lib/utils'
import { kitchenSocketUrl } from '@/lib/ws'

// Wall-mounted kitchen display ("KDS"): read-only, large type, three
// columns that orders move across as the kitchen works them. Location and
// station live in the URL so a screen can be bookmarked/kiosked, e.g.
// /kitchen/display?location=<id>&station=<id>.

const COLUMNS: { key: string; title: string; statuses: OrderStatus[]; accent: string }[] = [
  { key: 'next', title: 'Up next', statuses: ['PENDING', 'CONFIRMED', 'QUEUED'], accent: 'bg-sky-500' },
  { key: 'preparing', title: 'Preparing', statuses: ['PREPARING'], accent: 'bg-amber-500' },
  { key: 'ready', title: 'Ready', statuses: ['READY'], accent: 'bg-emerald-500' },
]

const STATUS_LABEL: Partial<Record<OrderStatus, string>> = {
  PENDING: 'New',
  CONFIRMED: 'Confirmed',
  QUEUED: 'Queued',
}

const TYPE_LABEL: Record<KitchenBoardOrder['order_type'], string> = {
  DINE_IN: 'Dine in',
  TAKEAWAY: 'Takeaway',
  BOOK_FOR_LATER: 'Booked',
}

// Minutes since an order was placed before its ticket turns amber / red.
const WARN_AFTER_MIN = 8
const LATE_AFTER_MIN = 15

// Fallback refresh in case the WebSocket drops silently.
const POLL_MS = 20_000
const RECONNECT_MS = 5_000

function formatElapsed(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${seconds.toString().padStart(2, '0')}`
}

function playChime() {
  try {
    const ctx = new AudioContext()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(880, ctx.currentTime)
    osc.frequency.setValueAtTime(1320, ctx.currentTime + 0.15)
    gain.gain.setValueAtTime(0.25, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5)
    osc.connect(gain).connect(ctx.destination)
    osc.start()
    osc.stop(ctx.currentTime + 0.5)
    osc.onended = () => void ctx.close()
  } catch {
    // Audio is a nice-to-have; browsers may block it until a user gesture.
  }
}

function Ticket({
  order,
  now,
  isNew,
  showStation,
}: {
  order: KitchenBoardOrder
  now: number
  isNew: boolean
  showStation: boolean
}) {
  const elapsedMs = now - new Date(order.created_at).getTime()
  const minutes = elapsedMs / 60_000
  const isReady = order.status === 'READY'
  const urgency = isReady ? 'ready' : minutes >= LATE_AFTER_MIN ? 'late' : minutes >= WARN_AFTER_MIN ? 'warn' : 'ok'

  return (
    <article
      className={cn(
        'flex flex-col overflow-hidden rounded-xl border-2 bg-zinc-900 shadow-lg',
        urgency === 'ok' && 'border-zinc-700',
        urgency === 'warn' && 'border-amber-400',
        urgency === 'late' && 'border-red-500',
        urgency === 'ready' && 'border-emerald-400',
        isNew && 'kds-flash',
      )}
    >
      <header
        className={cn(
          'flex items-center justify-between gap-3 px-4 py-2',
          urgency === 'ok' && 'bg-zinc-800',
          urgency === 'warn' && 'bg-amber-400 text-zinc-950',
          urgency === 'late' && 'animate-pulse bg-red-600 text-white',
          urgency === 'ready' && 'bg-emerald-500 text-zinc-950',
        )}
      >
        <span className="text-3xl font-black tracking-tight tabular-nums">#{order.order_number}</span>
        <span className="text-2xl font-bold tabular-nums">{formatElapsed(elapsedMs)}</span>
      </header>

      <div className="flex flex-wrap items-center gap-2 px-4 pt-2 text-sm font-semibold uppercase tracking-wide">
        <span
          className={cn(
            'rounded px-2 py-0.5',
            order.order_type === 'TAKEAWAY' ? 'bg-fuchsia-600 text-white' : 'bg-zinc-700 text-zinc-100',
            order.order_type === 'BOOK_FOR_LATER' && 'bg-indigo-600 text-white',
          )}
        >
          {TYPE_LABEL[order.order_type]}
        </span>
        {order.customer_type === 'GUEST' && (
          <span className="rounded bg-yellow-300 px-2 py-0.5 text-zinc-950">Guest</span>
        )}
        {STATUS_LABEL[order.status] && (
          <span className="rounded border border-zinc-600 px-2 py-0.5 text-zinc-300">
            {STATUS_LABEL[order.status]}
          </span>
        )}
      </div>

      <ul className="flex flex-col gap-1 px-4 py-3">
        {order.items.map((item, index) => (
          <li key={index} className="flex items-baseline gap-3 text-2xl leading-tight">
            <span className="min-w-[2.5ch] font-black text-amber-300 tabular-nums">{item.quantity}×</span>
            <span className="font-semibold text-zinc-50">
              {item.menu_item_name}
              {showStation && item.kitchen_station_name && (
                <span className="ml-2 align-middle text-sm font-medium text-zinc-400">
                  · {item.kitchen_station_name}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </article>
  )
}

export function KitchenDisplayPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const locationId = searchParams.get('location') ?? ''
  const stationId = searchParams.get('station') ?? ''

  const [locations, setLocations] = useState<Location[]>([])
  const [stations, setStations] = useState<KitchenStation[]>([])
  const [orders, setOrders] = useState<KitchenBoardOrder[]>([])
  const [error, setError] = useState<string | null>(null)
  const [live, setLive] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const [soundOn, setSoundOn] = useState(false)
  const [newIds, setNewIds] = useState<Set<string>>(new Set())
  const knownIds = useRef<Set<string> | null>(null)
  const soundOnRef = useRef(soundOn)
  soundOnRef.current = soundOn

  const updateParams = useCallback(
    (next: { location?: string; station?: string }) => {
      const params = new URLSearchParams(searchParams)
      for (const [key, value] of Object.entries(next)) {
        if (value) params.set(key, value)
        else params.delete(key)
      }
      setSearchParams(params, { replace: true })
    },
    [searchParams, setSearchParams],
  )

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    apiFetch<Location[]>('/locations')
      .then((all) => {
        const active = all.filter((l) => l.status === 'ACTIVE')
        setLocations(active)
        if (!locationId && active.length > 0) updateParams({ location: active[0].id })
      })
      .catch((err) => setError(getErrorMessage(err)))
    // Only on mount: picks a default location when the URL has none.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!locationId) return
    apiFetch<KitchenStation[]>(`/locations/${locationId}/kitchen-stations`)
      .then((all) => setStations(all.filter((s) => s.status === 'ACTIVE')))
      .catch((err) => setError(getErrorMessage(err)))
  }, [locationId])

  useEffect(() => {
    knownIds.current = null
    setOrders([])
  }, [locationId, stationId])

  const refresh = useCallback(() => {
    if (!locationId) return
    const query = stationId ? `?station_id=${encodeURIComponent(stationId)}` : ''
    apiFetch<KitchenBoardOrder[]>(`/locations/${locationId}/kitchen/board${query}`)
      .then((board) => {
        setError(null)
        const ids = new Set(board.map((o) => o.id))
        if (knownIds.current) {
          const fresh = board.filter((o) => !knownIds.current!.has(o.id)).map((o) => o.id)
          if (fresh.length > 0) {
            setNewIds(new Set(fresh))
            if (soundOnRef.current) playChime()
          }
        }
        knownIds.current = ids
        setOrders(board)
      })
      .catch((err) => setError(getErrorMessage(err)))
  }, [locationId, stationId])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(timer)
  }, [refresh])

  useEffect(() => {
    if (!locationId) return
    let socket: WebSocket | null = null
    let reconnectTimer: number | undefined
    let disposed = false

    const connect = () => {
      // Re-read each time: the polling apiFetch keeps the access token
      // refreshed, so a reconnect after expiry picks up the new one.
      const token = employeeAuthStorage.getAccessToken()
      if (!token) return
      socket = new WebSocket(kitchenSocketUrl(locationId, token))
      socket.onopen = () => {
        setLive(true)
        refresh()
      }
      socket.onmessage = () => refresh()
      socket.onclose = () => {
        setLive(false)
        if (!disposed) reconnectTimer = window.setTimeout(connect, RECONNECT_MS)
      }
    }
    connect()

    return () => {
      disposed = true
      window.clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [locationId, refresh])

  useEffect(() => {
    if (newIds.size === 0) return
    const timer = window.setTimeout(() => setNewIds(new Set()), 6000)
    return () => window.clearTimeout(timer)
  }, [newIds])

  const columns = useMemo(
    () => COLUMNS.map((col) => ({ ...col, orders: orders.filter((o) => col.statuses.includes(o.status)) })),
    [orders],
  )

  const toggleFullscreen = () => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void document.documentElement.requestFullscreen().catch(() => undefined)
  }

  const toggleSound = () => {
    const next = !soundOn
    setSoundOn(next)
    // Clicking the toggle is the user gesture browsers need to unlock audio.
    if (next) playChime()
  }

  const locationName = locations.find((l) => l.id === locationId)?.name
  const clock = new Date(now).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const selectClass =
    'rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-sm text-zinc-100 focus:outline-none focus:ring-2 focus:ring-emerald-500'

  return (
    <div className="flex h-svh flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-zinc-800 px-5 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-black uppercase tracking-wider">Kitchen</h1>
          <span className="text-lg text-zinc-400">{locationName ?? '—'}</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Location"
            className={selectClass}
            value={locationId}
            onChange={(e) => updateParams({ location: e.target.value, station: '' })}
          >
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
          <select
            aria-label="Kitchen station"
            className={selectClass}
            value={stationId}
            onChange={(e) => updateParams({ station: e.target.value })}
          >
            <option value="">All stations</option>
            {stations.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div className="ml-auto flex items-center gap-4">
          <span className="flex items-center gap-2 text-sm text-zinc-400">
            <span className={cn('size-2.5 rounded-full', live ? 'bg-emerald-400' : 'bg-red-500')} />
            {live ? 'Live' : 'Reconnecting…'}
          </span>
          <button
            type="button"
            onClick={toggleSound}
            className="rounded-md border border-zinc-700 px-3 py-1 text-sm hover:bg-zinc-800"
          >
            Sound {soundOn ? 'on' : 'off'}
          </button>
          <button
            type="button"
            onClick={toggleFullscreen}
            className="rounded-md border border-zinc-700 px-3 py-1 text-sm hover:bg-zinc-800"
          >
            Full screen
          </button>
          <Link to="/kitchen" className="text-sm text-zinc-400 underline-offset-4 hover:underline">
            Exit
          </Link>
          <span className="text-3xl font-bold tabular-nums">{clock}</span>
        </div>
      </header>

      {error && (
        <div className="bg-red-700 px-5 py-2 text-center text-sm font-medium text-white">{error}</div>
      )}

      <main className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[2fr_1.4fr_1fr]">
        {columns.map((col) => (
          <section key={col.key} className="flex min-h-0 flex-col rounded-2xl bg-zinc-900/50">
            <h2 className="flex items-center justify-between px-4 py-3 text-xl font-bold uppercase tracking-widest">
              <span className="flex items-center gap-3">
                <span className={cn('h-6 w-1.5 rounded-full', col.accent)} />
                {col.title}
              </span>
              <span className="rounded-full bg-zinc-800 px-3 py-0.5 text-lg tabular-nums">
                {col.orders.length}
              </span>
            </h2>
            <div
              className={cn(
                'grid min-h-0 flex-1 auto-rows-min content-start gap-3 overflow-y-auto px-3 pb-3',
                col.key === 'next' ? 'grid-cols-[repeat(auto-fill,minmax(17rem,1fr))]' : 'grid-cols-1 xl:grid-cols-[repeat(auto-fill,minmax(17rem,1fr))]',
              )}
            >
              {col.orders.length === 0 ? (
                <p className="col-span-full py-10 text-center text-lg text-zinc-600">No orders</p>
              ) : (
                col.orders.map((order) => (
                  <Ticket
                    key={order.id}
                    order={order}
                    now={now}
                    isNew={newIds.has(order.id)}
                    showStation={!stationId}
                  />
                ))
              )}
            </div>
          </section>
        ))}
      </main>
    </div>
  )
}
