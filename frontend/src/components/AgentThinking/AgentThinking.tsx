import { useEffect, useRef, useState } from "react";

interface Props {
  /** Full reasoning text from the latest agent_thinking step. */
  text: string | null;
  /** Whether the run is still active (enables streaming effect). */
  isLive: boolean;
}

/**
 * Terminal-style agent reasoning display with a character-by-character
 * typing effect when new text arrives during a live run. Falls back to
 * static display for completed runs.
 */
export default function AgentThinking({ text, isLive }: Props) {
  const [displayed, setDisplayed] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const prevTextRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // If same text or null, nothing to animate
    if (text === prevTextRef.current) return;
    prevTextRef.current = text;

    if (!text) {
      setDisplayed("");
      setIsTyping(false);
      return;
    }

    // For historical (non-live) runs, show full text immediately
    if (!isLive) {
      setDisplayed(text);
      setIsTyping(false);
      return;
    }

    // Live mode: type character by character
    setIsTyping(true);
    setDisplayed("");
    let idx = 0;
    const interval = setInterval(() => {
      idx++;
      setDisplayed(text.slice(0, idx));
      if (idx >= text.length) {
        clearInterval(interval);
        setIsTyping(false);
      }
    }, 12);

    return () => clearInterval(interval);
  }, [text, isLive]);

  // Auto-scroll to bottom as text streams in
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayed]);

  const isEmpty = !text && !displayed;

  return (
    <div className="rounded-xl border border-surface-700 bg-surface-800 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-surface-700 px-4 py-2.5">
        {/* Terminal dots */}
        <div className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-danger/60" />
          <span className="h-2 w-2 rounded-full bg-warning/60" />
          <span className="h-2 w-2 rounded-full bg-success/60" />
        </div>
        <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
          Agent Reasoning
        </span>
        {isTyping && (
          <span className="ml-auto flex items-center gap-1.5 text-[10px] text-accent-400">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-400 opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent-400" />
            </span>
            streaming
          </span>
        )}
      </div>

      {/* Body */}
      <div
        ref={scrollRef}
        className="max-h-[200px] min-h-[80px] overflow-y-auto bg-surface-900 px-4 py-3"
      >
        {isEmpty ? (
          <p className="text-xs text-text-muted italic">
            {isLive
              ? "Waiting for agent to reason..."
              : "No reasoning captured."}
          </p>
        ) : (
          <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-accent-300">
            {displayed}
            {isTyping && (
              <span className="inline-block w-[6px] h-[13px] ml-px bg-accent-400 animate-pulse" />
            )}
          </pre>
        )}
      </div>
    </div>
  );
}
