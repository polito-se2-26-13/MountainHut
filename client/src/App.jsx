import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { ConfigProvider } from 'antd'
import { AuthProvider } from './auth/AuthContext.jsx'
import AccountMenu from './components/AccountMenu.jsx'
import ToastProvider from './components/ToastProvider.jsx'
import './App.css'

const HomePage = lazy(() => import('./pages/HomePage.jsx'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.jsx'))
const RegisterPage = lazy(() => import('./pages/RegisterPage.jsx'))
const LoginPage = lazy(() => import('./pages/LoginPage.jsx'))
const RoleHomePage = lazy(() => import('./pages/RoleHomePage.jsx'))
const EmployeeSlotConfigPage = lazy(() => import('./pages/EmployeeSlotConfigPage.jsx'))
const CustomerBookingPage = lazy(() => import('./pages/CustomerBookingPage.jsx'))
const CustomerReservationHistoryPage = lazy(() => import('./pages/CustomerReservationHistoryPage.jsx'))

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1769aa',
          colorText: '#18212f',
          colorTextSecondary: '#64748b',
          colorBorder: '#cbd5e1',
          borderRadius: 8,
          controlHeight: 46,
          fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
          fontSize: 14,
        },
      }}
    >
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <AccountMenu />
            <Suspense fallback={<div className="route-loading" role="status">Loading…</div>}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/home/:role" element={<RoleHomePage />} />
                <Route path="/employee/slots" element={<EmployeeSlotConfigPage />} />
                <Route path="/customer/book-table" element={<CustomerBookingPage />} />
                <Route path="/customer/reservations" element={<CustomerReservationHistoryPage />} />
                <Route path="/404" element={<NotFoundPage />} />
                <Route path="*" element={<Navigate to="/404" replace />} />
              </Routes>
            </Suspense>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
