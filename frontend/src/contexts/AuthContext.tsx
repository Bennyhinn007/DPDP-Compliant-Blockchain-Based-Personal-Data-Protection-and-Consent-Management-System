/**
 * Authentication Context.
 *
 * Manages user session, JWT tokens, and login/logout flows.
 */

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { authService } from "@/services/authService";
import { identityService } from "@/services/identityService";
import { loadWallet, personalSign, deriveDid } from "@/lib/wallet";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  loginWithGoogle: (idToken: string) => Promise<User>;
  loginWithDid: () => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const token = localStorage.getItem("access_token");
    if (storedUser && token) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem("user");
      }
    }
    setIsLoading(false);
  }, []);

  // Shared: persist a successful auth result and set the active user.
  const persistSession = (result: {
    access_token: string;
    refresh_token: string;
    user: User;
  }): User => {
    localStorage.setItem("access_token", result.access_token);
    localStorage.setItem("refresh_token", result.refresh_token);
    localStorage.setItem("user", JSON.stringify(result.user));
    setUser(result.user);
    return result.user;
  };

  const login = async (email: string, password: string): Promise<User> => {
    const result = await authService.login(email, password);
    return persistSession(result);
  };

  const loginWithGoogle = async (idToken: string): Promise<User> => {
    const result = await authService.googleLogin(idToken);
    return persistSession(result);
  };

  /**
   * Passwordless login using the browser DID wallet (SIH 26125, additive).
   * Loads the client-side keypair, asks the backend for a single-use challenge,
   * signs it (EIP-191), and verifies it — the backend returns the SAME JWT pair
   * as password login, so we persist the session identically.
   */
  const loginWithDid = async (): Promise<User> => {
    const wallet = loadWallet();
    if (!wallet) {
      throw new Error(
        "No DID wallet found on this device. Create a DID first in the Identity Center."
      );
    }
    // Derive the DID locally from the wallet's public key (same deterministic
    // algorithm as the backend), so we can request a challenge before login.
    const did = deriveDid(wallet.publicKey);
    const challenge = await identityService.challenge(did);
    const signature = await personalSign(challenge.message, wallet.privateKey);
    const result = await identityService.verify(did, challenge.nonce, signature);
    return persistSession(result);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        loginWithGoogle,
        loginWithDid,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
