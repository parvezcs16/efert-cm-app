import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Minus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Textarea } from '@/components/ui/textarea'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { ConsumptionRecord, Order } from '@/lib/types'

// Mirrors EDITABLE_STATUSES in the backend order service: items can be
// changed until the kitchen queues the order.
const EDITABLE = new Set(['PENDING', 'CONFIRMED'])

const draftFrom = (order: Order): Record<string, number> =>
  Object.fromEntries(order.items.map((item) => [item.id, item.ordered_quantity]))

export function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const navigate = useNavigate()
  const [order, setOrder] = useState<Order | null>(null)
  const [consumption, setConsumption] = useState<Record<string, ConsumptionRecord>>({})
  // Item id -> quantity to keep; items absent from the map are removed.
  const [draft, setDraft] = useState<Record<string, number>>({})
  const [saving, setSaving] = useState(false)
  const [correctionItemId, setCorrectionItemId] = useState<string | null>(null)
  const [requestedQuantity, setRequestedQuantity] = useState('0')
  const [reason, setReason] = useState('')
  const [submittingCorrection, setSubmittingCorrection] = useState(false)

  const load = () => {
    if (!orderId) return
    apiFetch<Order>(`/orders/${orderId}`)
      .then((loaded) => {
        setOrder(loaded)
        setDraft(draftFrom(loaded))
      })
      .catch((err) => toast.error(getErrorMessage(err)))
  }

  useEffect(load, [orderId])

  useEffect(() => {
    if (!order || order.status !== 'SERVED') return
    order.items.forEach((item) => {
      apiFetch<ConsumptionRecord>(`/orders/${order.id}/items/${item.id}/consumption`)
        .then((record) => setConsumption((prev) => ({ ...prev, [item.id]: record })))
        .catch(() => {
          // Not yet served/no record -- fine to leave unset.
        })
    })
  }, [order])

  if (!order) {
    return (
      <div className="flex justify-center p-8">
        <Spinner className="size-6" />
      </div>
    )
  }

  const editable = EDITABLE.has(order.status)
  const draftEntries = Object.entries(draft)
  const dirty = order.items.some((item) => draft[item.id] !== item.ordered_quantity)

  const handleUpdate = async () => {
    // Removing every item leaves nothing to serve, so it cancels the order.
    const cancelling = draftEntries.length === 0
    if (cancelling && !window.confirm('You removed every item. Cancel the whole order?')) return

    setSaving(true)
    try {
      if (cancelling) {
        await apiFetch(`/orders/${order.id}/cancel`, { method: 'POST' })
      } else {
        await apiFetch(`/orders/${order.id}/items`, {
          method: 'PUT',
          body: JSON.stringify({
            items: draftEntries.map(([order_item_id, quantity]) => ({ order_item_id, quantity })),
          }),
        })
      }
      toast.success(cancelling ? 'Order cancelled' : 'Order updated')
      load()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const openCorrection = (itemId: string) => {
    setCorrectionItemId(itemId)
    setRequestedQuantity(String(consumption[itemId]?.served_quantity ?? 0))
    setReason('')
  }

  const submitCorrection = async () => {
    if (!correctionItemId) return
    setSubmittingCorrection(true)
    try {
      const record = await apiFetch<ConsumptionRecord>(
        `/orders/${order.id}/items/${correctionItemId}/consumption/request-correction`,
        {
          method: 'POST',
          body: JSON.stringify({
            requested_quantity: Number(requestedQuantity),
            reason,
          }),
        },
      )
      setConsumption((prev) => ({ ...prev, [correctionItemId]: record }))
      toast.success('Correction requested — a server will need to validate it')
      setCorrectionItemId(null)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setSubmittingCorrection(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate('/orders')}>
        ← Back to orders
      </Button>

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>{order.order_number}</CardTitle>
          <Badge>{order.status}</Badge>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="text-sm text-muted-foreground">
            <p>Type: {order.order_type.replace(/_/g, ' ')}</p>
            {order.scheduled_for && (
              <p>Scheduled for: {new Date(order.scheduled_for).toLocaleString()}</p>
            )}
          </div>

          {order.ingredient_status && (
            <div className="rounded-md border p-3 text-sm">
              <p className="font-medium">Booking status: {order.ingredient_status}</p>
              {order.ingredient_response_message && (
                <p className="text-muted-foreground">{order.ingredient_response_message}</p>
              )}
            </div>
          )}

          <div className="flex flex-col gap-2">
            {order.items.map((item) => {
              if (editable && !(item.id in draft)) return null
              const record = consumption[item.id]
              const quantity = editable ? draft[item.id] : item.ordered_quantity
              return (
                <div key={item.id} className="flex items-center justify-between gap-2 border-b pb-2">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium">{item.menu_item_name ?? 'Item'}</p>
                    <p className="text-sm">Qty ordered: {quantity}</p>
                    {record && (
                      <p className="text-sm text-muted-foreground">
                        Served: {record.served_quantity}
                        {record.status === 'CORRECTION_REQUESTED' &&
                          ' (correction pending review)'}
                      </p>
                    )}
                  </div>
                  {editable && (
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        size="icon"
                        aria-label="Decrease quantity"
                        disabled={saving || quantity <= 1}
                        onClick={() => setDraft((prev) => ({ ...prev, [item.id]: quantity - 1 }))}
                      >
                        <Minus />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        aria-label="Remove item"
                        className="text-destructive"
                        disabled={saving}
                        onClick={() =>
                          setDraft((prev) => {
                            const { [item.id]: _removed, ...rest } = prev
                            return rest
                          })
                        }
                      >
                        <Trash2 />
                      </Button>
                    </div>
                  )}
                  {record && record.status === 'VALIDATED' && (
                    <Button variant="outline" size="sm" onClick={() => openCorrection(item.id)}>
                      Report an issue
                    </Button>
                  )}
                </div>
              )
            })}
          </div>

          {editable && (
            <>
              {draftEntries.length === 0 && (
                <p className="text-sm text-destructive">
                  All items removed — updating will cancel this order.
                </p>
              )}
              <div className="flex gap-2">
                {dirty && (
                  <Button
                    variant="outline"
                    className="flex-1"
                    disabled={saving}
                    onClick={() => setDraft(draftFrom(order))}
                  >
                    Undo changes
                  </Button>
                )}
                <Button className="flex-1" onClick={handleUpdate} disabled={saving || !dirty}>
                  {saving && <Spinner />}
                  Update order
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Dialog open={correctionItemId !== null} onOpenChange={(open) => !open && setCorrectionItemId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request a correction</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="requested_quantity">Actual quantity received</Label>
              <Input
                id="requested_quantity"
                type="number"
                min={0}
                value={requestedQuantity}
                onChange={(e) => setRequestedQuantity(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="reason">Reason</Label>
              <Textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
            </div>
            <Button onClick={submitCorrection} disabled={submittingCorrection || !reason}>
              {submittingCorrection && <Spinner />}
              Submit for server validation
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
