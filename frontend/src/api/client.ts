import axios from "axios";
import type { Platform } from "../types";

/** Axios instance pre-configured for the backend API. */
const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export default api;

// ---------------------------------------------------------------------------
// Platform API
// ---------------------------------------------------------------------------

export interface PlatformCreatePayload {
  name: string;
  base_url: string;
  login_url: string;
  credentials: { username: string; password: string };
  login_selectors: Record<string, string>;
  extra_config?: Record<string, unknown> | null;
}

export type PlatformUpdatePayload = Partial<PlatformCreatePayload>;

export async function fetchPlatforms(): Promise<Platform[]> {
  const { data } = await api.get<Platform[]>("/platforms");
  return data;
}

export async function fetchPlatform(id: string): Promise<Platform> {
  const { data } = await api.get<Platform>(`/platforms/${id}`);
  return data;
}

export async function createPlatform(
  payload: PlatformCreatePayload,
): Promise<Platform> {
  const { data } = await api.post<Platform>("/platforms", payload);
  return data;
}

export async function updatePlatform(
  id: string,
  payload: PlatformUpdatePayload,
): Promise<Platform> {
  const { data } = await api.put<Platform>(`/platforms/${id}`, payload);
  return data;
}

export async function deletePlatform(id: string): Promise<void> {
  await api.delete(`/platforms/${id}`);
}
