import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import { BrandLogo, BrandStripe } from '@/components/BrandLogo'
import { MenuItemTile } from '@/components/MenuItemTile'
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
import { GuestSessionEnded } from '@/features/guests/components/GuestSessionEnded'
import type { GuestEndReason } from '@/features/guests/components/GuestSessionEnded'
import { ApiError, guestApiFetch } from '@/lib/api'
import { guestAuthStorage } from '@/lib/auth-storage'
import type { GuestSession, Location, MenuBrowseCategory, Order } from '@/lib/types'

interface GuestAuthResponse {
  access_token: string
  session: GuestSession
}

// How often an open portal re-checks the session, so a guest sees the
// "session ended" screen soon after the host closes it.
const SESSION_CHECK_MS = 30_000

/** A closed session answers 403 and an expired/invalid token 401 (see
 * backend app/api/v1/deps.py:get_current_guest_session). */
function endReasonFor(err: unknown): GuestEndReason | null {
  if (err instanceof ApiError) {
    if (err.status === 403) return 'closed'
    if (err.status === 401) return 'expired'
  }
  return null
}

export function GuestPortalPage() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'authenticating' | 'ready' | 'ended'>('authenticating')
  const [endReason, setEndReason] = useState<GuestEndReason>('closed')

  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState('')
  const [categories, setCategories] = useState<MenuBrowseCategory[]>([])
  const [cart, setCart] = useState<Record<string, number>>({})
  const [orders, setOrders] = useState<Order[]>([])
  const [submitting, setSubmitting] = useState(false)

  const endSession = useCallback((reason: GuestEndReason) => {
    guestAuthStorage.clear()
    // A closed session's QR token can still ask the host to reopen it.
    if (reason !== 'closed') guestAuthStorage.clearQrToken()
    setEndReason(reason)
    setStatus('ended')
  }, [])

  const resumeSession = useCallback((accessToken: string) => {
    guestAuthStorage.setAccessToken(accessToken)
    setStatus('ready')
  }, [])

  /** Ends the portal on a closed/expired session; otherwise shows `message`. */
  const handleGuestError = useCallback(
    (err: unknown, message: string) => {
      const reason = endReasonFor(err)
      if (reason) endSession(reason)
      else toast.error(message)
    },
    [endSession],
  )

  useEffect(() => {
    const urlToken = searchParams.get('token')
    const authenticate = async () => {
      if (!urlToken) {
        if (guestAuthStorage.getAccessToken()) setStatus('ready')
        else endSession('missing')
        return
      }
      try {
        const result = await fetch(`/api/v1/guest/auth`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: urlToken }),
        })
        if (!result.ok) {
          endSession('expired')
          return
        }
        const body: GuestAuthResponse = await result.json()
        guestAuthStorage.setQrToken(urlToken)
        // The QR stays valid for 24h after the host closes the session, so
        // auth can succeed for a session that can no longer order.
        if (body.session.status !== 'ACTIVE') {
          endSession('closed')
          return
        }
        guestAuthStorage.setAccessToken(body.access_token)
        setStatus('ready')
      } catch {
        toast.error('Unable to reach Central Mess. Please check your connection and try again.')
      }
    }
    void authenticate()
  }, [searchParams, endSession])

  useEffect(() => {
    if (status !== 'ready') return
    guestApiFetch<Location[]>('/guest/locations')
      .then((all) => {
        const active = all.filter((l) => l.status === 'ACTIVE')
        setLocations(active)
        if (active.length > 0) setLocationId(active[0].id)
      })
      .catch((err) => handleGuestError(err, 'Could not load locations'))

    const loadOrders = () =>
      guestApiFetch<Order[]>('/guest/orders')
        .then(setOrders)
        .catch((err) => {
          // A transient failure just keeps the last list; only a
          // closed/expired session ends the portal.
          const reason = endReasonFor(err)
          if (reason) endSession(reason)
        })
    void loadOrders()
    const timer = window.setInterval(loadOrders, SESSION_CHECK_MS)
    return () => window.clearInterval(timer)
  }, [status, handleGuestError, endSession])

  useEffect(() => {
    if (!locationId) return
    setCart({})
    guestApiFetch<MenuBrowseCategory[]>(`/guest/locations/${locationId}/menu`)
      .then(setCategories)
      .catch((err) => handleGuestError(err, 'Could not load the menu'))
  }, [locationId, handleGuestError])

  const itemCount = useMemo(() => Object.values(cart).reduce((sum, q) => sum + q, 0), [cart])

  const adjustCart = (itemId: string, delta: number) => {
    setCart((prev) => {
      const next = { ...prev }
      const updated = (next[itemId] ?? 0) + delta
      if (updated <= 0) delete next[itemId]
      else next[itemId] = updated
      return next
    })
  }

  const placeOrder = async () => {
    setSubmitting(true)
    try {
      const order = await guestApiFetch<Order>('/guest/orders', {
        method: 'POST',
        body: JSON.stringify({
          location_id: locationId,
          order_type: 'DINE_IN',
          items: Object.entries(cart).map(([menu_item_id, quantity]) => ({
            menu_item_id,
            quantity,
          })),
        }),
      })
      toast.success(`Order ${order.order_number} placed`)
      setCart({})
      setOrders((prev) => [order, ...prev])
    } catch (err) {
      handleGuestError(err, 'Could not place your order. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (status === 'authenticating') {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Spinner className="size-6" />
      </div>
    )
  }

  if (status === 'ended') {
    return (
      <GuestSessionEnded
        reason={endReason}
        qrToken={guestAuthStorage.getQrToken()}
        onResumed={resumeSession}
      />
    )
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-3xl flex-col gap-4 p-4">
      <div className="flex flex-col gap-3">
        <BrandLogo />
        <BrandStripe className="rounded-full" />
        <h1 className="text-lg font-semibold">Welcome</h1>
      </div>

      <Select value={locationId} onValueChange={setLocationId}>
        <SelectTrigger>
          <SelectValue placeholder="Select a location" />
        </SelectTrigger>
        <SelectContent>
          {locations.map((loc) => (
            <SelectItem key={loc.id} value={loc.id}>
              {loc.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {categories.map((category) => (
        <Card key={category.id}>
          <CardHeader>
            <CardTitle className="text-base">{category.name}</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {category.items.map((item) => (
              <MenuItemTile
                key={item.id}
                item={item}
                quantity={cart[item.id] ?? 0}
                onAdjust={(delta) => adjustCart(item.id, delta)}
              />
            ))}
          </CardContent>
        </Card>
      ))}

      <div className="sticky bottom-4 flex justify-end">
        <Button size="lg" onClick={placeOrder} disabled={submitting || itemCount === 0}>
          {submitting && <Spinner />}
          Place order ({itemCount})
        </Button>
      </div>

      {orders.length > 0 && (
        <div className="flex flex-col gap-2">
          <h2 className="text-sm font-semibold text-muted-foreground">Your orders</h2>
          {orders.map((order) => (
            <Card key={order.id}>
              <CardContent className="flex items-center justify-between p-3 text-sm">
                <span>{order.order_number}</span>
                <Badge>{order.status}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
