import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { apiFetch, getErrorMessage } from '@/lib/api'
import { employeeAuthStorage } from '@/lib/auth-storage'
import type { KitchenStation, Location, Order } from '@/lib/types'
import { kitchenSocketUrl } from '@/lib/ws'

const NEXT_ACTION: Partial<Record<Order['status'], { label: string; action: string }>> = {
  PENDING: { label: 'Confirm', action: 'confirm' },
  PREPARING: { label: 'Mark ready', action: 'mark-ready' },
  READY: { label: 'Serve', action: 'serve' },
}

function OrderCard({
  order,
  onRefresh,
  stationId,
}: {
  order: Order
  onRefresh: () => void
  stationId: string | null
}) {
  const [busy, setBusy] = useState(false)
  const [delayReason, setDelayReason] = useState('')
  const [showDelay, setShowDelay] = useState(false)

  const runAction = async (path: string, init?: RequestInit) => {
    setBusy(true)
    try {
      await apiFetch(path, init)
      onRefresh()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const confirmIngredients = () =>
    runAction(`/orders/${order.id}/booking/confirm-ingredients`, { method: 'POST' })

  const submitDelay = async () => {
    const newTime = new Date(Date.now() + 60 * 60 * 1000).toISOString()
    await runAction(`/orders/${order.id}/booking/delay`, {
      method: 'POST',
      body: JSON.stringify({ new_scheduled_for: newTime, reason: delayReason }),
    })
    setShowDelay(false)
  }

  const handleQueue = () => {
    if (!stationId) {
      toast.error('Select a kitchen station first')
      return
    }
    const stationAssignments: Record<string, string> = {}
    order.items.forEach((item) => {
      stationAssignments[item.id] = stationId
    })
    void runAction(`/orders/${order.id}/queue`, {
      method: 'POST',
      body: JSON.stringify({ station_assignments: stationAssignments }),
    })
  }

  const next = NEXT_ACTION[order.status]
  const needsBookingReview = order.order_type === 'BOOK_FOR_LATER' && order.ingredient_status !== 'CONFIRMED'

  return (
    <Card>
      <CardContent className="flex flex-col gap-2 p-4">
        <div className="flex items-center justify-between">
          <p className="font-medium">{order.order_number}</p>
          <div className="flex gap-2">
            <Badge variant="secondary">{order.order_type.replace(/_/g, ' ')}</Badge>
            <Badge>{order.status}</Badge>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          {order.items.reduce((sum, i) => sum + i.ordered_quantity, 0)} item(s)
        </p>

        {needsBookingReview ? (
          <div className="flex flex-col gap-2 rounded-md border border-amber-400 bg-amber-50 p-2 text-sm dark:bg-amber-950">
            <p>Ingredients need review before {order.scheduled_for}</p>
            {showDelay ? (
              <div className="flex flex-col gap-2">
                <Textarea
                  placeholder="Reason for delay"
                  value={delayReason}
                  onChange={(e) => setDelayReason(e.target.value)}
                />
                <div className="flex gap-2">
                  <Button size="sm" disabled={busy || !delayReason} onClick={submitDelay}>
                    Send delay
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowDelay(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <Button size="sm" disabled={busy} onClick={confirmIngredients}>
                  Confirm available
                </Button>
                <Button size="sm" variant="outline" disabled={busy} onClick={() => setShowDelay(true)}>
                  Delay
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {order.status === 'CONFIRMED' && (
              <Button size="sm" disabled={busy} onClick={handleQueue}>
                {busy && <Spinner />}
                Queue to station
              </Button>
            )}
            {order.status === 'QUEUED' && (
              <Button
                size="sm"
                disabled={busy}
                onClick={() => runAction(`/orders/${order.id}/start-preparing`, { method: 'POST' })}
              >
                {busy && <Spinner />}
                Start preparing
              </Button>
            )}
            {next && (
              <Button
                size="sm"
                disabled={busy}
                onClick={() => runAction(`/orders/${order.id}/${next.action}`, { method: 'POST' })}
              >
                {busy && <Spinner />}
                {next.label}
              </Button>
            )}
            {order.status !== 'SERVED' && order.status !== 'CANCELLED' && (
              <Button
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => runAction(`/orders/${order.id}/serve-directly`, { method: 'POST' })}
              >
                Serve directly
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function KitchenPage() {
  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState('')
  const [stations, setStations] = useState<KitchenStation[]>([])
  const [stationId, setStationId] = useState<string>('')
  const [incoming, setIncoming] = useState<Order[]>([])
  const [queue, setQueue] = useState<Order[]>([])
  const [pendingBookings, setPendingBookings] = useState<Order[]>([])
  const [loading, setLoading] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    apiFetch<Location[]>('/locations')
      .then((all) => {
        const active = all.filter((l) => l.status === 'ACTIVE')
        setLocations(active)
        if (active.length > 0) setLocationId(active[0].id)
      })
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [])

  useEffect(() => {
    if (!locationId) return
    apiFetch<KitchenStation[]>(`/locations/${locationId}/kitchen-stations`)
      .then((all) => {
        const active = all.filter((s) => s.status === 'ACTIVE')
        setStations(active)
        setStationId((current) => (active.some((s) => s.id === current) ? current : (active[0]?.id ?? '')))
      })
      .catch((err) => toast.error(getErrorMessage(err)))
  }, [locationId])

  const refresh = useCallback(() => {
    if (!locationId) return
    setLoading(true)
    const requests: Promise<void>[] = [
      apiFetch<Order[]>(`/locations/${locationId}/orders/incoming`).then(setIncoming),
      apiFetch<Order[]>(`/locations/${locationId}/bookings/pending`).then(setPendingBookings),
    ]
    if (stationId) {
      requests.push(
        apiFetch<Order[]>(`/locations/${locationId}/kitchen-stations/${stationId}/queue`).then(
          setQueue,
        ),
      )
    } else {
      setQueue([])
    }
    Promise.all(requests)
      .catch((err) => toast.error(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [locationId, stationId])

  useEffect(refresh, [refresh])

  useEffect(() => {
    if (!locationId) return
    const token = employeeAuthStorage.getAccessToken()
    if (!token) return

    const socket = new WebSocket(kitchenSocketUrl(locationId, token))
    wsRef.current = socket
    socket.onmessage = () => refresh()
    socket.onerror = () => {
      // Connection issues surface as the display simply not live-updating;
      // the periodic manual refresh (via any user action) still works.
    }
    return () => socket.close()
  }, [locationId, refresh])

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="flex justify-end">
        <Button asChild variant="outline" size="sm">
          <Link to={`/kitchen/display${locationId ? `?location=${locationId}` : ''}`}>
            Open kitchen display screen
          </Link>
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Select value={locationId} onValueChange={setLocationId}>
          <SelectTrigger>
            <SelectValue placeholder="Location" />
          </SelectTrigger>
          <SelectContent>
            {locations.map((loc) => (
              <SelectItem key={loc.id} value={loc.id}>
                {loc.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={stationId} onValueChange={setStationId}>
          <SelectTrigger>
            <SelectValue placeholder="Kitchen station" />
          </SelectTrigger>
          <SelectContent>
            {stations.map((s) => (
              <SelectItem key={s.id} value={s.id}>
                {s.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading && incoming.length === 0 && queue.length === 0 ? (
        <div className="flex justify-center p-8">
          <Spinner className="size-6" />
        </div>
      ) : (
        <>
          {pendingBookings.length > 0 && (
            <section className="flex flex-col gap-2">
              <h2 className="text-sm font-semibold text-muted-foreground">
                Booked orders awaiting review
              </h2>
              {pendingBookings.map((o) => (
                <OrderCard key={o.id} order={o} onRefresh={refresh} stationId={stationId} />
              ))}
            </section>
          )}

          <section className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold text-muted-foreground">Incoming</h2>
            {incoming.length === 0 && (
              <p className="text-sm text-muted-foreground">Nothing waiting on confirm/queue.</p>
            )}
            {incoming.map((o) => (
              <OrderCard key={o.id} order={o} onRefresh={refresh} stationId={stationId} />
            ))}
          </section>

          <section className="flex flex-col gap-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Station queue</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                {queue.length === 0 && (
                  <p className="text-sm text-muted-foreground">Queue is empty.</p>
                )}
                {queue.map((o) => (
                  <OrderCard key={o.id} order={o} onRefresh={refresh} stationId={stationId} />
                ))}
              </CardContent>
            </Card>
          </section>
        </>
      )}
    </div>
  )
}
