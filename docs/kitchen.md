# Kitchen Operations

## Stations
Each location can have multiple kitchen stations.

Examples:
- Main Kitchen
- Beverages
- Snacks
- Dessert

Order items may be routed to different stations.

## Queue
Priority:
1. Immediate orders
2. Released booked orders

Within each priority, FIFO.

## Booked Orders
Booked orders remain visible to kitchen/management.

The kitchen/management workflow must verify ingredients.

If unavailable:
- Trigger a prominent animated manager alert/bell.
- Manager reviews the order.
- Manager can confirm availability or return a delay response.
- Employee receives the response/update.
- Serving time can be updated.

Once confirmed, booked order enters the queue according to priority.

## Realtime
Kitchen displays should receive queue/status changes through WebSockets.

## Served
Server marks food served when handed to the customer.
The served quantity becomes the basis for consumption billing after validation.
