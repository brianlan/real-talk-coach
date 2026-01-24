"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { getSession, deleteSession } from "@/services/api/admin/sessions";

const formatDateTime = (value?: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
};

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params?.sessionId as string;
  const [session, setSession] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getSession(sessionId);
        setSession(data);
      } catch (err: any) {
        setError(err?.message ?? "Failed to load session");
      } finally {
        setLoading(false);
      }
    };
    if (sessionId) load();
  }, [sessionId]);

  const handleDelete = async () => {
    setConfirming(false);
    try {
      await deleteSession(sessionId);
      setNotice("Deleted");
      setTimeout(() => router.push("/admin/sessions"), 800);
    } catch (err: any) {
      setError(err?.message ?? "Failed to delete session");
    }
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2>Session Detail</h2>
      {loading ? <p>Loading…</p> : null}
      {error ? <p style={{ color: "#b24332" }}>{error}</p> : null}
      {notice ? <p style={{ color: "#1f7a3d" }}>{notice}</p> : null}
      {session && !loading && !error ? (
        <div style={{ display: "grid", gap: 8 }}>
          {(() => {
            const scenarioLabel = session.scenarioTitle
              ? `${session.scenarioTitle} (${session.scenarioId})`
              : session.scenarioId;
            return (
              <>
          <p><strong>ID:</strong> {session.id}</p>
          <p><strong>Scenario:</strong> {scenarioLabel}</p>
          <p><strong>Status:</strong> {session.status}</p>
          <p><strong>Started:</strong> {formatDateTime(session.startedAt)}</p>
          <p><strong>Ended:</strong> {formatDateTime(session.endedAt)}</p>
          <p><strong>Termination Reason:</strong> {session.terminationReason ?? ""}</p>
          <p><strong>Evaluation Status:</strong> {session.evaluationStatus ?? ""}</p>
              </>
            );
          })()}
          <button
            type="button"
            onClick={() => setConfirming(true)}
            style={{ padding: "10px 14px", borderRadius: 10, border: "1px solid #d9d3cb" }}
          >
            Delete Session
          </button>
          {confirming ? (
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span>Confirm delete?</span>
              <button
                type="button"
                onClick={handleDelete}
                style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #b24332", background: "#fbe9e7" }}
              >
                Yes, delete
              </button>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #d9d3cb" }}
              >
                Cancel
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
