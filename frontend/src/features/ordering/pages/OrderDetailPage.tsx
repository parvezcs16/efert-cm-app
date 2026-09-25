import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
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

const CANCELLABLE = new Set(['PENDING', 'CONFIRMED', 'QUEUED', 'PREPARING', 'READY'])

export function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>()
  const navigate = useNavigate()
  const [order, setOrder] = useState<Order | null>(null)
  const [consumption, setConsumption] = useState<Record<string, ConsumptionRecord>>({})
  const [cancelling, setCancelling] = useState(false)
  const [correctionItemId, setCorrectionItemId] = useState<string | null>(null)
  const [requestedQuantity, setRequestedQuantity] = useState('0')
  const [reason, setReason] = useState('')
  const [submittingCorrection, setSubmittingCorrection] = useState(false)

  const load = () => {
    if (!orderId) return
    apiFetch<Order>(`/orders/${orderId}`)
      .then(setOrder)
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

  const handleCancel = async () => {
    setCancelling(true)
    try {
      await apiFetch(`/orders/${order.id}/cancel`, { method: 'POST' })
      toast.success('Order cancelled')
      load()
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setCancelling(false)
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
              const record = consumption[item.id]
              return (
                <div key={item.id} className="flex items-center justify-between border-b pb-2">
                  <div>
                    <p className="text-sm">Qty ordered: {item.ordered_quantity}</p>
                    {record && (
                      <p className="text-sm text-muted-foreground">
                        Served: {record.served_quantity}
                        {record.status === 'CORRECTION_REQUESTED' &&
                          ' (correction pending review)'}
                      </p>
                    )}
                  </div>
                  {record && record.status === 'VALIDATED' && (
                    <Button variant="outline" size="sm" onClick={() => openCorrection(item.id)}>
                      Report an issue
                    </Button>
                  )}
                </div>
              )
            })}
          </div>

          {CANCELLABLE.has(order.status) && (
            <Button variant="destructive" onClick={handleCancel} disabled={cancelling}>
              {cancelling && <Spinner />}
              Cancel order
            </Button>
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
