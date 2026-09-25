import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { apiFetch, getErrorMessage } from '@/lib/api'
import type { Order, OrderStatus } from '@/lib/types'

const STATUS_VARIANT: Record<OrderStatus, 'default' | 'secondary' | 'success' | 'destructive'> = {
  PENDING: 'secondary',
  CONFIRMED: 'secondary',
  QUEUED: 'default',
  PREPARING: 'default',
  READY: 'default',
  SERVED: 'success',
  CANCELLED: 'destructive',
}

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiFetch<Order[]>('/orders')
      .then(setOrders)
      .catch((err) => setError(getErrorMessage(err)))
  }, [])

  if (error) return <p className="text-sm text-destructive">{error}</p>
  if (orders === null) {
    return (
      <div className="flex justify-center p-8">
        <Spinner className="size-6" />
      </div>
    )
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-3">
      <h1 className="text-lg font-semibold">My orders</h1>
      {orders.length === 0 && (
        <p className="text-sm text-muted-foreground">You haven't placed any orders yet.</p>
      )}
      {orders.map((order) => (
        <Link key={order.id} to={`/orders/${order.id}`}>
          <Card className="transition-colors hover:bg-accent/50">
            <CardContent className="flex items-center justify-between gap-3 p-4">
              <div>
                <p className="text-sm font-medium">{order.order_number}</p>
                <p className="text-sm text-muted-foreground">
                  {order.order_type.replace(/_/g, ' ')} · {order.items.length} item
                  {order.items.length === 1 ? '' : 's'}
                </p>
              </div>
              <Badge variant={STATUS_VARIANT[order.status]}>{order.status}</Badge>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  )
}
