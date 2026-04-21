import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, useLocation, Navigate, Outlet } from 'react-router-dom'
import Layout from './Layout'
import Dashboard from './Pages/Dashboard'
import AdminDashboard from './Pages/AdminDashboard'
import AuditLog from './Pages/AuditLog'
import LandingPage from './Pages/LandingPage'
import LoginPage from './Pages/LoginPage'
import RegisterPage from './Pages/RegisterPage'

const queryClient = new QueryClient()

/** Read the stored user object from localStorage */
function getStoredUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); } catch { return null; }
}

// ── Protected layout: requires login ────────────────────────────────
function ProtectedLayout() {
  const location = useLocation();
  const isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const getPageName = (pathname) => {
    if (pathname === '/audit') return 'AuditLog';
    if (pathname === '/admin') return 'Admin';
    return 'Dashboard';
  };

  return (
    <Layout currentPageName={getPageName(location.pathname)}>
      <Outlet />
    </Layout>
  );
}

// ── Admin-only guard ─────────────────────────────────────────────────
function AdminRoute() {
  const user = getStoredUser();
  if (user?.role !== 'Administrator') {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}

// ── Doctor-only guard (blocks admin from doctor views) ───────────────
function DoctorRoute() {
  const user = getStoredUser();
  if (user?.role === 'Administrator') {
    return <Navigate to="/admin" replace />;
  }
  return <Outlet />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Routes */}
          <Route element={<ProtectedLayout />}>
            {/* Doctor routes */}
            <Route element={<DoctorRoute />}>
              <Route path="/dashboard" element={<Dashboard />} />
            </Route>

            {/* Admin routes */}
            <Route element={<AdminRoute />}>
              <Route path="/admin" element={<AdminDashboard />} />
            </Route>

            {/* Shared routes */}
            <Route path="/audit" element={<AuditLog />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
