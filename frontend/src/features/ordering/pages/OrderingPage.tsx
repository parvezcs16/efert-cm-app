import { ShoppingCart } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { CategoryNav } from '@/components/CategoryNav'
import { MenuItemTile } from '@/components/MenuItemTile'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { Location, MenuBrowseCategory, Order, OrderType } from '@/lib/types'

const ORDER_TYPES: { value: OrderType; label: string }[] = [
  { value: 'DINE_IN', label: 'Dine in' },
  { value: 'TAKEAWAY', label: 'Takeaway' },
  { value: 'BOOK_FOR_LATER', label: 'Book for later' },
]

export function OrderingPage() {
  const navigate = useNavigate()
  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState<string>('')
  const [categories, setCategories] = useState<MenuBrowseCategory[]>([])
  const [menuLoading, setMenuLoading] = useState(false)
  const [cart, setCart] = useState<Record<string, number>>({})
  const [orderType, setOrderType] = useState<OrderType>('DINE_IN')
  const [scheduledFor, setScheduledFor] = useState('')
  const [submitting, setSubmitting] = useState(false)

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
    setMenuLoading(true)
    setCart({})
    apiFetch<MenuBrowseCategory[]>(`/locations/${locationId}/menu/browse`)
      .then(setCategories)
      .catch((err) => toast.error(getErrorMessage(err)))
      .finally(() => setMenuLoading(false))
  }, [locationId])

  const itemCount = useMemo(() => Object.values(cart).reduce((sum, q) => sum + q, 0), [cart])
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null)
  // Falls back to the first category when the menu (re)loads, e.g. after
  // switching location. The cart is kept across category switches.
  const selectedCategory =
    categories.find((c) => c.id === selectedCategoryId) ?? categories[0] ?? null
  const navEntries = useMemo(
    () => categories.map((c) => ({ id: c.id, name: c.name, count: c.items.length })),
    [categories],
  )

  const adjustCart = (itemId: string, delta: number) => {
    setCart((prev) => {
      const next = { ...prev }
      const updated = (next[itemId] ?? 0) + delta
      if (updated <= 0) {
        delete next[itemId]
      } else {
        next[itemId] = updated
      }
      return next
    })
  }

  const handleSubmit = async () => {
    if (itemCount === 0) {
      toast.error('Add at least one item to your order')
      return
    }
    if (orderType === 'BOOK_FOR_LATER' && !scheduledFor) {
      toast.error('Choose a time for your booking')
      return
    }
    setSubmitting(true)
    try {
      const order = await apiFetch<Order>('/orders', {
        method: 'POST',
        body: JSON.stringify({
          location_id: locationId,
          order_type: orderType,
          scheduled_for:
            orderType === 'BOOK_FOR_LATER' ? new Date(scheduledFor).toISOString() : null,
          items: Object.entries(cart).map(([menu_item_id, quantity]) => ({
            menu_item_id,
            quantity,
          })),
        }),
      })
      toast.success(`Order ${order.order_number} placed`)
      navigate(`/orders/${order.id}`)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Place an order</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label>Location</Label>
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
            </div>
            <div className="flex flex-col gap-2">
              <Label>Order type</Label>
              <Select value={orderType} onValueChange={(v) => setOrderType(v as OrderType)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ORDER_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {orderType === 'BOOK_FOR_LATER' && (
            <div className="flex flex-col gap-2">
              <Label htmlFor="scheduled_for">Serving time</Label>
              <Input
                id="scheduled_for"
                type="datetime-local"
                value={scheduledFor}
                onChange={(e) => setScheduledFor(e.target.value)}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {menuLoading ? (
        <div className="flex justify-center p-8">
          <Spinner className="size-6" />
        </div>
      ) : categories.length === 0 ? (
        <p className="p-8 text-center text-sm text-muted-foreground">
          No items available at this location right now.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[12rem_1fr] lg:gap-6">
          <CategoryNav
            categories={navEntries}
            selectedId={selectedCategory?.id ?? null}
            onSelect={setSelectedCategoryId}
          />
          {selectedCategory && (
            <Card className="min-w-0">
              <CardHeader>
                <CardTitle className="text-base">{selectedCategory.name}</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {selectedCategory.items.map((item) => (
                  <MenuItemTile
                    key={item.id}
                    item={item}
                    quantity={cart[item.id] ?? 0}
                    onAdjust={(delta) => adjustCart(item.id, delta)}
                  />
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      <div className="sticky bottom-4 flex justify-end">
        <Button size="lg" onClick={handleSubmit} disabled={submitting || itemCount === 0}>
          {submitting ? <Spinner /> : <ShoppingCart />}
          Place order ({itemCount})
        </Button>
      </div>
    </div>
  )
}
