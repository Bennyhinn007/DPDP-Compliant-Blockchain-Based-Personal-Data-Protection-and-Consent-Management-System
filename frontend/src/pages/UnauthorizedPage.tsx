/**
 * Unauthorized (403) Page.
 *
 * Role-aware "Back to Dashboard" navigation.
 */

import { useNavigate } from "react-router-dom";
import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { portalPath } from "@/lib/navigation";

export function UnauthorizedPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleBack = () => {
    if (!user) {
      navigate("/login", { replace: true });
      return;
    }
    navigate(portalPath(user.role), { replace: true });
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-danger/10">
        <ShieldX className="h-8 w-8 text-danger" />
      </div>
      <h1 className="text-2xl font-bold text-neutral-800">Access Denied</h1>
      <p className="mt-2 max-w-md text-neutral-500">
        You do not have permission to view this page.
      </p>
      <Button className="mt-6" onClick={handleBack}>
        Back to Dashboard
      </Button>
    </div>
  );
}
