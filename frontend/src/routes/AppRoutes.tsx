import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../layouts/AppShell';
import { LoginPage } from '../features/auth/pages/LoginPage';
import { DashboardPage } from '../features/dashboard/pages/DashboardPage';
import { CrmPage } from '../features/crm/pages/CrmPage';
import { WhatsappPage } from '../features/whatsapp/pages/WhatsappPage';
import { AdminPage } from '../features/settings/pages/AdminPage';
import { SuperAdminPage } from '../features/super-admin/pages/SuperAdminPage';

const fallbackRoute = String.fromCharCode(42);

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AppShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/crm" element={<CrmPage />} />
        <Route path="/whatsapp" element={<WhatsappPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/super-admin" element={<SuperAdminPage />} />
      </Route>
      <Route path={fallbackRoute} element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
