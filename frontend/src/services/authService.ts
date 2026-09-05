/**
 * Authentication API Service.
 */

import api from "./api";
import type { LoginResponse, User } from "@/types";

export const authService = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const { data } = await api.post<LoginResponse>("/auth/login", { email, password });
    return data;
  },

  async googleLogin(idToken: string): Promise<LoginResponse> {
    const { data } = await api.post<LoginResponse>("/auth/google", { id_token: idToken });
    return data;
  },

  async register(
    email: string,
    password: string,
    role: string,
    full_name: string
  ): Promise<{ message: string; user: User }> {
    const { data } = await api.post("/auth/register", { email, password, role, full_name });
    return data;
  },

  async getCurrentUser(): Promise<User> {
    const { data } = await api.get<{ user: User }>("/auth/me");
    return data.user;
  },

  // Phase 5: check whether the user recently tapped their RFID card
  async getPhysicalPresence(): Promise<PhysicalPresenceStatus> {
    const { data } = await api.get<PhysicalPresenceStatus>("/auth/physical-presence/status");
    return data;
  },
};

export interface PhysicalPresenceStatus {
  present: boolean;
  reason?: string;
  verified_at?: string;
  expires_at?: string;
  seconds_left?: number;
  card_id?: string;
}
