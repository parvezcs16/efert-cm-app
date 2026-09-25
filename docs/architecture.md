# Architecture

## Style
Modular monolith.

## High-level flow

React PWA
  |
  | HTTPS / WebSocket
  v
FastAPI
  |
  +-- Auth
  +-- Employee
  +-- Guest
  +-- Menu
  +-- Ordering
  +-- Kitchen
  +-- Consumption
  +-- Billing
  +-- Reviews
  +-- Notifications
  +-- Administration
  |
  v
PostgreSQL

## Core domain separation

Ordering:
What was requested?

Kitchen:
What is being prepared?

Consumption:
What was actually served?

Billing:
Who is financially responsible?

These must not be collapsed into one model.

## Realtime
Use WebSockets for:
- kitchen queue changes
- order status changes
- manager alerts
- ingredient confirmation changes

REST remains the primary command/query API.

## Notifications
Use an internal notification service/interface.
Email is the initial provider.
Additional providers can be implemented later.

## Suggested backend layout

backend/app/
  core/
  models/
  schemas/
  repositories/
  services/
  api/v1/
  websocket/
  workers/

Prefer domain-oriented service modules over a large generic service file.
