/**
 * Application Root.
 *
 * Sets up providers, routing, and route protection.
 */

import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryProvider } from "@/contexts/QueryProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { AppShell } from "@/layouts/AppShell";
import { Toaster } from "sonner";
import { PageLoader } from "@/components/shared/PageLoader";

// Page components are lazy-loaded so each route ships in its own chunk — the
// initial bundle stays small and a patient never downloads admin/DPO/doctor code.
// (Named exports -> map to a default for React.lazy.)
const LoginPage = lazy(() => import("@/pages/auth/LoginPage").then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import("@/pages/auth/RegisterPage").then((m) => ({ default: m.RegisterPage })));
const PatientDashboard = lazy(() => import("@/pages/patient/PatientDashboard").then((m) => ({ default: m.PatientDashboard })));
const PersonalDataCenter = lazy(() => import("@/pages/patient/PersonalDataCenter").then((m) => ({ default: m.PersonalDataCenter })));
const ConsentCenter = lazy(() => import("@/pages/patient/ConsentCenter").then((m) => ({ default: m.ConsentCenter })));
const AuditTimeline = lazy(() => import("@/pages/patient/AuditTimeline").then((m) => ({ default: m.AuditTimeline })));
const IntegrityVerification = lazy(() => import("@/pages/patient/IntegrityVerification").then((m) => ({ default: m.IntegrityVerification })));
const ChameleonHashCenter = lazy(() => import("@/pages/patient/ChameleonHashCenter").then((m) => ({ default: m.ChameleonHashCenter })));
const DPODashboard = lazy(() => import("@/pages/dpo/DPODashboard").then((m) => ({ default: m.DPODashboard })));
const DoctorDashboard = lazy(() => import("@/pages/doctor/DoctorDashboard").then((m) => ({ default: m.DoctorDashboard })));
const ComplianceDashboard = lazy(() => import("@/pages/dpo/ComplianceDashboard").then((m) => ({ default: m.ComplianceDashboard })));
const IdentityGovernance = lazy(() => import("@/pages/admin/IdentityGovernance").then((m) => ({ default: m.IdentityGovernance })));
const RegisterPatient = lazy(() => import("@/pages/admin/RegisterPatient").then((m) => ({ default: m.RegisterPatient })));
const DPDPOperationsCenter = lazy(() => import("@/pages/admin/DPDPOperationsCenter").then((m) => ({ default: m.DPDPOperationsCenter })));
const BlockchainExplorer = lazy(() => import("@/pages/admin/BlockchainExplorer").then((m) => ({ default: m.BlockchainExplorer })));
const PhysicalAccessLog = lazy(() => import("@/pages/admin/PhysicalAccessLog").then((m) => ({ default: m.PhysicalAccessLog })));
const ProfilePage = lazy(() => import("@/pages/shared/ProfilePage").then((m) => ({ default: m.ProfilePage })));
const IdentityCenter = lazy(() => import("@/pages/identity/IdentityCenter").then((m) => ({ default: m.IdentityCenter })));
const DigitalAssetCenter = lazy(() => import("@/pages/assets/DigitalAssetCenter").then((m) => ({ default: m.DigitalAssetCenter })));
const AccessControlCenter = lazy(() => import("@/pages/access/AccessControlCenter").then((m) => ({ default: m.AccessControlCenter })));
const UnauthorizedPage = lazy(() => import("@/pages/UnauthorizedPage").then((m) => ({ default: m.UnauthorizedPage })));

function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-right" richColors closeButton />
          <Suspense fallback={<PageLoader message="Loading..." />}>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/unauthorized" element={<UnauthorizedPage />} />

            {/* Shared (all authenticated roles) */}
            <Route
              element={
                <ProtectedRoute allowedRoles={["patient", "doctor", "admin", "dpo"]}>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/identity" element={<IdentityCenter />} />
              <Route path="/assets" element={<DigitalAssetCenter />} />
            </Route>

            {/* Protected (patient) */}
            <Route
              element={
                <ProtectedRoute allowedRoles={["patient"]}>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<PatientDashboard />} />
              <Route path="/my-data" element={<PersonalDataCenter />} />
              <Route path="/consents" element={<ConsentCenter />} />
              <Route path="/timeline" element={<AuditTimeline />} />
              <Route path="/verify" element={<IntegrityVerification />} />
              <Route path="/chameleon-hash" element={<ChameleonHashCenter />} />
            </Route>

            {/* Protected (doctor) */}
            <Route
              element={
                <ProtectedRoute allowedRoles={["doctor"]}>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/doctor" element={<DoctorDashboard />} />
            </Route>

            {/* Protected (admin/dpo) */}
            {/* Protected (registration staff) — RESTRICTED to patient registration only */}
            <Route
              element={
                <ProtectedRoute allowedRoles={["registration_staff"]}>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/staff/register-patient" element={<RegisterPatient />} />
            </Route>

            <Route
              element={
                <ProtectedRoute allowedRoles={["admin", "dpo"]}>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/dpo" element={<DPODashboard />} />
              <Route path="/dpo/compliance" element={<ComplianceDashboard />} />
              <Route path="/compliance" element={<ComplianceDashboard />} />
              <Route path="/admin/register-patient" element={<RegisterPatient />} />
              <Route path="/admin/users" element={<IdentityGovernance />} />
              <Route path="/admin/operations" element={<DPDPOperationsCenter />} />
              <Route path="/admin/blockchain" element={<BlockchainExplorer />} />
              <Route path="/admin/physical-access" element={<PhysicalAccessLog />} />
              <Route path="/admin/access-control" element={<AccessControlCenter />} />
            </Route>

            {/* Defaults */}
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
          </Suspense>
        </BrowserRouter>
      </AuthProvider>
    </QueryProvider>
  );
}

export default App;
