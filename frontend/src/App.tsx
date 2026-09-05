/**
 * Application Root.
 *
 * Sets up providers, routing, and route protection.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryProvider } from "@/contexts/QueryProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { AppShell } from "@/layouts/AppShell";
import { Toaster } from "sonner";
import { LoginPage } from "@/pages/auth/LoginPage";
import { RegisterPage } from "@/pages/auth/RegisterPage";
import { PatientDashboard } from "@/pages/patient/PatientDashboard";
import { PersonalDataCenter } from "@/pages/patient/PersonalDataCenter";
import { ConsentCenter } from "@/pages/patient/ConsentCenter";
import { AuditTimeline } from "@/pages/patient/AuditTimeline";
import { IntegrityVerification } from "@/pages/patient/IntegrityVerification";
import { ChameleonHashCenter } from "@/pages/patient/ChameleonHashCenter";
import { DPODashboard } from "@/pages/dpo/DPODashboard";
import { DoctorDashboard } from "@/pages/doctor/DoctorDashboard";
import { ComplianceDashboard } from "@/pages/dpo/ComplianceDashboard";
import { IdentityGovernance } from "@/pages/admin/IdentityGovernance";
import { DPDPOperationsCenter } from "@/pages/admin/DPDPOperationsCenter";
import { BlockchainExplorer } from "@/pages/admin/BlockchainExplorer";
import { PhysicalAccessLog } from "@/pages/admin/PhysicalAccessLog";
import { ProfilePage } from "@/pages/shared/ProfilePage";
import { UnauthorizedPage } from "@/pages/UnauthorizedPage";

function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <BrowserRouter>
          <Toaster position="top-right" richColors closeButton />
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
              <Route path="/admin/users" element={<IdentityGovernance />} />
              <Route path="/admin/operations" element={<DPDPOperationsCenter />} />
              <Route path="/admin/blockchain" element={<BlockchainExplorer />} />
              <Route path="/admin/physical-access" element={<PhysicalAccessLog />} />
            </Route>

            {/* Defaults */}
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryProvider>
  );
}

export default App;
