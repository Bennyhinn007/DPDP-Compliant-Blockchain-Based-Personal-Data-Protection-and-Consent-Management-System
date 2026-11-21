/**
 * Prefetch the code the user needs right after signing in.
 *
 * /login no longer ships the signed-in layout or the dashboards, so the login
 * page calls this when it is idle (or when the form gets focus, if sooner).
 * The chunks then load while the user types. Vite reuses the same chunks for
 * the lazy routes in App.tsx.
 */
let started = false;

export function prefetchSignedInApp(): void {
  if (started) return;
  started = true;
  const ignore = () => undefined;
  import("@/layouts/AppShell").catch(ignore);
  import("@/pages/patient/PatientDashboard").catch(ignore);
  import("@/pages/doctor/DoctorDashboard").catch(ignore);
}
