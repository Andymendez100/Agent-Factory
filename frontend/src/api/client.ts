import axios from "axios";
import type { AgentRun, AgentTask, Platform } from "../types";

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

// ---------------------------------------------------------------------------
// Task API
// ---------------------------------------------------------------------------

export interface TaskCreatePayload {
  name: string;
  goal: string;
  platform_ids: string[];
  constraints: Record<string, unknown> | null;
}

export type TaskUpdatePayload = Partial<TaskCreatePayload>;

export async function fetchTasks(): Promise<AgentTask[]> {
  const { data } = await api.get<AgentTask[]>("/tasks");
  return data;
}

export async function fetchTask(id: string): Promise<AgentTask> {
  const { data } = await api.get<AgentTask>(`/tasks/${id}`);
  return data;
}

export async function createTask(
  payload: TaskCreatePayload,
): Promise<AgentTask> {
  const { data } = await api.post<AgentTask>("/tasks", payload);
  return data;
}

export async function updateTask(
  id: string,
  payload: TaskUpdatePayload,
): Promise<AgentTask> {
  const { data } = await api.put<AgentTask>(`/tasks/${id}`, payload);
  return data;
}

export async function deleteTask(id: string): Promise<void> {
  await api.delete(`/tasks/${id}`);
}

// ---------------------------------------------------------------------------
// Run API
// ---------------------------------------------------------------------------

export async function triggerRun(taskId: string): Promise<AgentRun> {
  const { data } = await api.post<AgentRun>(`/tasks/${taskId}/run`);
  return data;
}
