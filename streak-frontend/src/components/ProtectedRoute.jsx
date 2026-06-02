import { Navigate, Outlet } from 'react-router-dom';

import { getStoredAccessToken } from '../api/axios';

export default function ProtectedRoute() {
  if (!getStoredAccessToken()) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}