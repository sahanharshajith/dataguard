"use client";

import { useEffect, useState } from "react";

import { apiGet, isAbortError } from "@/lib/api";

type Props = {
  title: string;
  description: string;
  path: string;
};

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: Record<string, string> }
  | { kind: "error"; message: string };

const badgeStyles = {
  loading: "bg-slate-100 text-slate-600",
  ok: "bg-emerald-100 text-emerald-700",
  error: "bg-red-100 text-red-700",
} as const;

export default function ServiceStatusCard({ title, description, path }: Props) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    apiGet<Record<string, string>>(path, controller.signal)
      .then((data) => setState({ kind: "ok", data }))
      .catch((error: unknown) => {
        if (isAbortError(error)) return;
        setState({
          kind: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      });

    // Cancel the request if the component goes away or re-runs.
    return () => controller.abort();
  }, [path, reloadKey]);

  function recheck() {
    setState({ kind: "loading" });
    setReloadKey((key) => key + 1);
  }

  const label = state.kind === "loading" ? "Checking…" : state.kind === "ok" ? "Healthy" : "Down";

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-medium">{title}</h3>
          <p className="mt-0.5 text-sm text-slate-500">{description}</p>
        </div>
        <span
          role="status"
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeStyles[state.kind]}`}
        >
          {label}
        </span>
      </div>

      {state.kind === "ok" && (
        <dl className="mt-4 space-y-1 text-sm">
          {Object.entries(state.data).map(([key, value]) => (
            <div key={key} className="flex justify-between gap-4">
              <dt className="text-slate-500">{key}</dt>
              <dd className="font-mono text-slate-800">{value}</dd>
            </div>
          ))}
        </dl>
      )}

      {state.kind === "error" && <p className="mt-4 text-sm text-red-600">{state.message}</p>}

      <button
        type="button"
        onClick={recheck}
        className="mt-4 text-sm font-medium text-slate-600 underline-offset-2 hover:text-slate-900 hover:underline"
      >
        Re-check
      </button>
    </div>
  );
}