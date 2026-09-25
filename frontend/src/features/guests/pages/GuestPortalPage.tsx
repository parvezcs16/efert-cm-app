import { Minus, Plus } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
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
import { guestApiFetch } from '@/lib/api'
import { guestAuthStorage } from '@/lib/auth-storage'
import type { Location, MenuBrowseCategory, Order } from '@/lib/types'

export function GuestPortalPage() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'authenticating' | 'ready' | 'error'>('authenticating')
  const [error, setError] = useState('')

  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState('')
  const [categories, setCategories] = useState<MenuBrowseCategory[]>([])
  const [cart, setCart] = useState<Record<string, number>>({})
  const [orders, setOrders] = useState<Order[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const urlToken = searchParams.get('token')
    const authenticate = async () => {
      try {
        if (urlToken) {
          const result = await fetch(`/api/v1/guest/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: urlToken }),
          })
          if (!result.ok) throw new Error('This QR code is no longer valid.')
          const body = await result.json()
          guestAuthStorage.setAccessToken(body.access_token)
        } else if (!guestAuthStorage.getAccessToken()) {
          throw new Error('Scan a guest QR code to get started.')
        }
        setStatus('ready')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to start your session')
        setStatus('error')
      }
    }
    void authenticate()
  }, [searchParams])

  useEffect(() => {
    if (status !== 'ready') return
    guestApiFetch<Location[]>('/guest/locations')
      .then((all) => {
        const active = all.filter((l) => l.status === 'ACTIVE')
        setLocations(active)
        if (active.length > 0) setLocationId(active[0].id)
      })
      .catch(() => toast.error('Could not load locations'))
    guestApiFetch<Order[]>('/guest/orders')
      .then(setOrders)
      .catch(() => {
        // No orders yet is fine.
      })
  }, [status])

  useEffect(() => {
    if (!locationId) return
    setCart({})
    guestApiFetch<MenuBrowseCategory[]>(`/guest/locations/${locationId}/menu`)
      .then(setCategories)
      .catch(() => toast.error('Could not load the menu'))
  }, [locationId])

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
    } catch {
      toast.error('Could not place your order — your host may have closed this session')
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

  if (status === 'error') {
    return (
      <div className="flex min-h-svh items-center justify-center p-4">
        <Card className="max-w-sm">
          <CardContent className="p-6 text-center text-sm text-muted-foreground">{error}</CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-2xl flex-col gap-4 p-4">
      <h1 className="text-lg font-semibold">Welcome</h1>

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
          <CardContent className="flex flex-col gap-3">
            {category.items.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{item.name}</p>
                  {item.description && (
                    <p className="text-sm text-muted-foreground">{item.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    onClick={() => adjustCart(item.id, -1)}
                    disabled={!cart[item.id]}
                  >
                    <Minus />
                  </Button>
                  <span className="w-4 text-center text-sm">{cart[item.id] ?? 0}</span>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    onClick={() => adjustCart(item.id, 1)}
                  >
                    <Plus />
                  </Button>
                </div>
              </div>
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
