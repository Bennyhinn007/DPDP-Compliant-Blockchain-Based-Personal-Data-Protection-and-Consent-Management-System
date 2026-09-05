/**
 * Google Sign-In Button.
 *
 * Loads Google Identity Services (GIS) and renders the official
 * "Sign in with Google" button. On success it exchanges the Google ID
 * token for our own JWT session via AuthContext.loginWithGoogle, then
 * routes the user by role — identical to the password login flow.
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/services/api";

const GIS_SRC = "https://accounts.google.com/gsi/client";

interface GoogleSignInButtonProps {
  /** Where to send non-admin users after login. */
  redirectTo?: string;
  /** Bubble errors up to the parent page for display. */
  onError?: (message: string) => void;
  text?: "signin_with" | "signup_with" | "continue_with";
}

/** Load the GIS script once and resolve when window.google is ready. */
function loadGisScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }
    const existing = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load Google script")));
      return;
    }
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google script"));
    document.head.appendChild(script);
  });
}

export function GoogleSignInButton({
  redirectTo = "/dashboard",
  onError,
  text = "continue_with",
}: GoogleSignInButtonProps) {
  const { loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const buttonRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId) {
      onError?.("Google login is not configured (missing VITE_GOOGLE_CLIENT_ID).");
      return;
    }

    let cancelled = false;

    loadGisScript()
      .then(() => {
        if (cancelled || !window.google || !buttonRef.current) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response: { credential: string }) => {
            try {
              const user = await loginWithGoogle(response.credential);
              if (user.role === "admin" || user.role === "dpo") {
                navigate("/dpo", { replace: true });
              } else if (user.role === "doctor") {
                navigate("/doctor", { replace: true });
              } else {
                navigate(redirectTo, { replace: true });
              }
            } catch (err) {
              onError?.(getErrorMessage(err));
            }
          },
          cancel_on_tap_outside: true,
        });

        window.google.accounts.id.renderButton(buttonRef.current, {
          type: "standard",
          theme: "outline",
          size: "large",
          text,
          shape: "pill",
          logo_alignment: "left",
          width: 320,
        });

        setReady(true);
      })
      .catch(() => onError?.("Could not load Google Sign-In. Check your connection."));

    return () => {
      cancelled = true;
    };
  }, [clientId, loginWithGoogle, navigate, redirectTo, onError, text]);

  if (!clientId) return null;

  return (
    <div className="flex flex-col items-center">
      {/* GIS renders its official button inside this element */}
      <div ref={buttonRef} className="flex justify-center" />
      {!ready && (
        <div className="h-10 w-full animate-pulse rounded-full bg-neutral-100" aria-hidden />
      )}
    </div>
  );
}
