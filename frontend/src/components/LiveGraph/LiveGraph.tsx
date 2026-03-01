import { useCallback, useEffect, useMemo, useRef } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
import StepNode, { type StepNodeData } from "./StepNode";
import type { StepEvent } from "../../types";

const NODE_TYPES = { step: StepNode };

/** Vertical spacing between nodes. */
const Y_GAP = 120;
/** X center for the vertical chain. */
const X_CENTER = 0;

interface LiveGraphInnerProps {
  steps: StepEvent[];
  isRunning: boolean;
}

function LiveGraphInner({ steps, isRunning }: LiveGraphInnerProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<StepNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const { fitView } = useReactFlow();
  const prevCountRef = useRef(0);

  // Build nodes and edges from steps
  const buildGraph = useCallback(() => {
    const newNodes: Node<StepNodeData>[] = steps.map((step, i) => ({
      id: `step-${step.step_index}`,
      type: "step" as const,
      position: { x: X_CENTER, y: i * Y_GAP },
      data: {
        stepIndex: step.step_index,
        stepType: step.step_type,
        toolName: step.tool_name,
        reasoning: step.agent_reasoning,
        durationMs: step.duration_ms,
        isLatest: i === steps.length - 1 && isRunning,
      },
    }));

    const newEdges: Edge[] = steps.slice(1).map((step, i) => ({
      id: `e-${steps[i].step_index}-${step.step_index}`,
      source: `step-${steps[i].step_index}`,
      target: `step-${step.step_index}`,
      animated: i === steps.length - 2 && isRunning,
      style: { stroke: "#374151", strokeWidth: 2 },
    }));

    setNodes(newNodes);
    setEdges(newEdges);
  }, [steps, isRunning, setNodes, setEdges]);

  useEffect(() => {
    buildGraph();

    // Auto-fit when new steps arrive
    if (steps.length !== prevCountRef.current) {
      prevCountRef.current = steps.length;
      // Small delay so the DOM updates before fitView
      setTimeout(() => fitView({ padding: 0.3, duration: 300 }), 50);
    }
  }, [buildGraph, steps.length, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.3 }}
      proOptions={{ hideAttribution: true }}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnDrag
      zoomOnScroll
      minZoom={0.3}
      maxZoom={1.5}
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={20}
        size={1}
        color="#1f2937"
      />
    </ReactFlow>
  );
}

interface LiveGraphProps {
  steps: StepEvent[];
  isRunning: boolean;
}

/**
 * Live execution graph — wraps ReactFlow in a provider.
 * Nodes appear vertically as the agent processes steps.
 */
export default function LiveGraph({ steps, isRunning }: LiveGraphProps) {
  const emptyMessage = useMemo(() => {
    if (steps.length > 0) return null;
    return (
      <div className="absolute inset-0 z-10 flex flex-col items-center justify-center pointer-events-none">
        <div className="flex items-center gap-2 text-text-muted">
          {isRunning ? (
            <>
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-accent-500" />
              <span className="text-sm">Waiting for agent to start...</span>
            </>
          ) : (
            <span className="text-sm">No steps recorded.</span>
          )}
        </div>
      </div>
    );
  }, [steps.length, isRunning]);

  return (
    <div className="relative h-full w-full">
      {emptyMessage}
      <ReactFlowProvider>
        <LiveGraphInner steps={steps} isRunning={isRunning} />
      </ReactFlowProvider>
    </div>
  );
}
