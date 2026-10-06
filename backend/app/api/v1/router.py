from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    billing,
    booking,
    consumption,
    employees,
    guest_portal,
    guests,
    health,
    kitchen,
    locations,
    menu,
    notifications,
    orders,
    reports,
    reviews,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(locations.router)
api_router.include_router(menu.router)
api_router.include_router(orders.router)
api_router.include_router(kitchen.router)
api_router.include_router(booking.router)
api_router.include_router(booking.pending_router)
api_router.include_router(consumption.router)
api_router.include_router(billing.router)
api_router.include_router(guests.router)
api_router.include_router(guest_portal.router)
api_router.include_router(reviews.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
