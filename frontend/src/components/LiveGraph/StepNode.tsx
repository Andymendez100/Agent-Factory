import { memo } from "react";
import { Handle, Position, type NodeProps, type Node } from "@xyflow/react";

export type StepNodeData = {
  stepIndex: number;
  stepType: "agent_thinking" | "tool_call";
  toolName: string | null;
  reasoning: string | null;
  durationMs: number;
  /** Whether this is the most recently added node (shows pulse). */
  isLatest: boolean;
};

export type StepNodeType = Node<StepNodeData, "step">;

const ICONS: Record<string, string> = {
  agent_thinking: "\u{1F9E0}",
  login: "\u{1F511}",
  navigate: "\u{1F310}",
  scrape: "\u{1F4CB}",
  click: "\u{1F5B1}",
  fill: "\u{270F}",
  screenshot: "\u{1F4F7}",
  analyze: "\u{1F4CA}",
  export: "\u{1F4BE}",
  alert: "\u{1F514}",
  default: "\u{2699}",
};

function getIcon(stepType: string, toolName: string | null): string {
  if (stepType === "agent_thinking") return ICONS.agent_thinking;
  if (!toolName) return ICONS.default;
  const lower = toolName.toLowerCase();
  for (const [key, icon] of Object.entries(ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return ICONS.default;
}

function StepNode({ data }: NodeProps<StepNodeType>) {
  const isThinking = data.stepType === "agent_thinking";
  const icon = getIcon(data.stepType, data.toolName);

  const label = isThinking
    ? "Agent Thinking"
    : data.toolName || "Tool Call";

  const preview = isThinking
    ? data.reasoning
      ? data.reasoning.slice(0, 80) + (data.reasoning.length > 80 ? "..." : "")
      : "Reasoning..."
    : data.toolName || "Executing...";

  // Color scheme per step type
  const borderColor = isThinking
    ? "border-accent-500/60"
    : "border-success/60";
  const glowColor = isThinking
    ? "shadow-accent-500/20"
    : "shadow-success/20";
  const badgeColor = isThinking
    ? "bg-accent-500/20 text-accent-400"
    : "bg-success/20 text-success";

  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !bg-surface-500 !border-surface-600"
      />

      <div
        className={`
          relative min-w-[200px] max-w-[260px] rounded-lg border bg-surface-800
          ${borderColor} shadow-lg ${glowColor}
          ${data.isLatest ? "ring-1 ring-accent-400/40" : ""}
          transition-all duration-300
        `}
      >
        {/* Pulse indicator for latest node */}
        {data.isLatest && (
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-accent-500" />
          </span>
        )}

        {/* Header */}
        <div className="flex items-center gap-2 border-b border-surface-700/50 px-3 py-2">
          <span className="text-sm">{icon}</span>
          <span className="text-xs font-semibold tracking-wide text-text-primary truncate">
            {label}
          </span>
          <span className={`ml-auto shrink-0 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${badgeColor}`}>
            #{data.stepIndex}
          </span>
        </div>

        {/* Body */}
        <div className="px-3 py-2">
          <p className="text-[11px] leading-relaxed text-text-secondary truncate">
            {preview}
          </p>
        </div>

        {/* Footer — duration */}
        <div className="border-t border-surface-700/50 px-3 py-1.5">
          <span className="font-mono text-[10px] text-text-muted">
            {data.durationMs > 0
              ? `${(data.durationMs / 1000).toFixed(1)}s`
              : "..."}
          </span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2 !h-2 !bg-surface-500 !border-surface-600"
      />
    </>
  );
}

export default memo(StepNode);
