import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import HomePage from './pages/HomePage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import RoleHomePage from './pages/RoleHomePage.jsx'
import { AuthProvider } from './auth/AuthContext.jsx'
import EmployeeSlotConfigPage from './pages/EmployeeSlotConfigPage.jsx'
import CustomerBookingPage from './pages/CustomerBookingPage.jsx'
import AccountMenu from './components/AccountMenu.jsx'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AccountMenu />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/home/:role" element={<RoleHomePage />} />
          <Route path="/employee/slots" element={<EmployeeSlotConfigPage />} />
          <Route path="/customer/book-table" element={<CustomerBookingPage />} />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
