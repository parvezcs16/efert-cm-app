# Functional Requirements

## Actors
- Employee
- Guest
- Server
- Kitchen Operator
- Location Manager
- System Manager
- Finance/Admin
- System Administrator

## Employee
- Register using P-Number and allowed company email domain.
- Registration can remain pending.
- Login using P-Number and password.
- First activation requires OTP and mandatory password change.
- Password changes/resets require OTP.
- View personal mess ledger.
- View private guest charges.
- View official guest records where permitted.
- Order from any location.
- Place dine-in, takeaway, or booked orders.
- Request served quantity correction.
- Choose statement frequency.
- Submit reviews.

## Guest
- Registered with name, company, CNIC, host employee, and accompanying-person count.
- Access via temporary QR/session.
- Place multiple orders during an active session.
- Order quantities greater than one.
- Guest history remains linked to the guest.

## Server
- Create orders for walk-up customers.
- Verify served quantities.
- Mark orders served.
- Process eligible corrections.
- Handle orders in normal service workflow.

## Kitchen
- View active queues.
- Work by kitchen station.
- Prepare orders in priority sequence.
- Mark preparing/ready.
- See booked orders and ingredient status.
- Receive manager alerts.

## Management
- Manage employees and pending registrations.
- Manage locations.
- Manage menus, prices, availability, and kitchen stations.
- Confirm booked-order ingredient availability.
- Delay/update booked serving times.
- Adjust/reverse billing.
- Configure review categories/questions.
- Review reports and audit logs.
