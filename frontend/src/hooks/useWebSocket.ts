import { useCallback, useEffect, useRef, useState } from "react";
import type { StepEvent, RunCompleteEvent } from "../types";

export type WSStatus = "connecting" | "connected" | "disconnected" | "error";

interface UseWebSocketReturn {
  /** Steps received so far. */
  steps: StepEvent[];
  /** Terminal event when the run finishes. */
  completion: RunCompleteEvent | null;
  /** Connection status. */
  status: WSStatus;
}

/**
 * Connects to the backend WebSocket for a given run and streams step events.
 * Automatically disconnects when the run completes or the component unmounts.
 */
export function useWebSocket(runId: string | undefined): UseWebSocketReturn {
  const [steps, setSteps] = useState<StepEvent[]>([]);
  const [completion, setCompletion] = useState<RunCompleteEvent | null>(null);
  const [status, setStatus] = useState<WSStatus>("disconnected");
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!runId) return;

    // Build WS URL relative to current host (works with Vite proxy in dev)
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${window.location.host}/ws/runs/${runId}`;

    setStatus("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "run_complete") {
          setCompletion(data as RunCompleteEvent);
          setStatus("disconnected");
          ws.close();
          return;
        }

        // Regular step event
        setSteps((prev) => [...prev, data as StepEvent]);
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onerror = () => {
      setStatus("error");
    };

    ws.onclose = () => {
      setStatus((prev) => (prev === "error" ? "error" : "disconnected"));
    };
  }, [runId]);

  useEffect(() => {
    // Reset state on runId change
    setSteps([]);
    setCompletion(null);

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  return { steps, completion, status };
}
