import { Route, Routes } from 'react-router-dom'

import { AppLayout } from '@/components/AppLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { RoleHome } from '@/components/RoleHome'
import { AdministrationPage } from '@/features/administration/pages/AdministrationPage'
import { ActivationPage } from '@/features/auth/pages/ActivationPage'
import { ForgotPasswordPage } from '@/features/auth/pages/ForgotPasswordPage'
import { LoginPage } from '@/features/auth/pages/LoginPage'
import { RegisterPage } from '@/features/auth/pages/RegisterPage'
import { BillingPage } from '@/features/billing/pages/BillingPage'
import { GuestPortalPage } from '@/features/guests/pages/GuestPortalPage'
import { GuestsPage } from '@/features/guests/pages/GuestsPage'
import { KitchenDisplayPage } from '@/features/kitchen/pages/KitchenDisplayPage'
import { KitchenPage } from '@/features/kitchen/pages/KitchenPage'
import { OrderDetailPage } from '@/features/ordering/pages/OrderDetailPage'
import { OrderingPage } from '@/features/ordering/pages/OrderingPage'
import { OrdersPage } from '@/features/ordering/pages/OrdersPage'
import { ReviewsPage } from '@/features/reviews/pages/ReviewsPage'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/activate" element={<ActivationPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/guest" element={<GuestPortalPage />} />

      <Route element={<ProtectedRoute />}>
        {/* Full-screen wall display: deliberately outside AppLayout's nav chrome. */}
        <Route path="/kitchen/display" element={<KitchenDisplayPage />} />
        <Route element={<AppLayout />}>
          <Route path="/" element={<RoleHome />} />
          <Route path="/order" element={<OrderingPage />} />
          <Route path="/orders" element={<OrdersPage />} />
          <Route path="/orders/:orderId" element={<OrderDetailPage />} />
          <Route path="/guests" element={<GuestsPage />} />
          <Route path="/kitchen" element={<KitchenPage />} />
          <Route path="/billing" element={<BillingPage />} />
          <Route path="/reviews" element={<ReviewsPage />} />
          <Route path="/admin" element={<AdministrationPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
