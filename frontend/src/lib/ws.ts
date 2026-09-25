export function kitchenSocketUrl(locationId: string, token: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/kitchen/${locationId}?token=${encodeURIComponent(token)}`
}
