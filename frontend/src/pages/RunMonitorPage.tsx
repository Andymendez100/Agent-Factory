import { useParams } from "react-router-dom";

export default function RunMonitorPage() {
  const { runId } = useParams<{ runId: string }>();

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Run Monitor</h1>
      <p className="mt-1 text-text-secondary">
        Live execution trace for run{" "}
        <code className="font-mono text-accent-400">{runId}</code>
      </p>
    </div>
  );
}
