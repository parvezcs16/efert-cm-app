const ACCESS_TOKEN_KEY = 'mess_access_token'
const REFRESH_TOKEN_KEY = 'mess_refresh_token'
const GUEST_TOKEN_KEY = 'mess_guest_access_token'
const GUEST_QR_TOKEN_KEY = 'mess_guest_qr_token'

export const employeeAuthStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },
  setAccessToken: (accessToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}

// Guest sessions are per-visit, so sessionStorage (cleared when the tab
// closes) rather than localStorage is the more appropriate fit.
export const guestAuthStorage = {
  getAccessToken: () => sessionStorage.getItem(GUEST_TOKEN_KEY),
  setAccessToken: (accessToken: string) => {
    sessionStorage.setItem(GUEST_TOKEN_KEY, accessToken)
  },
  clear: () => {
    sessionStorage.removeItem(GUEST_TOKEN_KEY)
  },
  // The raw QR token outlives the access token: it still authenticates a
  // closed session (for 24h), which the "ask your host" flow relies on.
  getQrToken: () => sessionStorage.getItem(GUEST_QR_TOKEN_KEY),
  setQrToken: (qrToken: string) => {
    sessionStorage.setItem(GUEST_QR_TOKEN_KEY, qrToken)
  },
  clearQrToken: () => {
    sessionStorage.removeItem(GUEST_QR_TOKEN_KEY)
  },
}
