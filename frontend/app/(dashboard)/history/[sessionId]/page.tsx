"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import HistoryDetail from "./history-detail";
import { fetchHistoryDetail } from "@/services/api/history";

export default function HistoryDetailPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params?.sessionId;
  const [detail, setDetail] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let canceled = false;
    const loadDetail = async () => {
      if (!sessionId) {
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const data = await fetchHistoryDetail(sessionId, 2);
        if (!canceled) {
          setDetail(data);
        }
      } catch (err) {
        if (!canceled) {
          setDetail(null);
          setError((err as Error).message);
        }
      } finally {
        if (!canceled) {
          setLoading(false);
        }
      }
    };
    loadDetail();
    return () => {
      canceled = true;
    };
  }, [sessionId]);

  if (loading) {
    return (
      <main style={{ padding: "48px 24px" }}>
        <p>Loading session...</p>
      </main>
    );
  }

  if (!detail || !sessionId) {
    return (
      <main style={{ padding: "48px 24px" }}>
        <p>{error ?? "Session not found."}</p>
      </main>
    );
  }

  return <HistoryDetail sessionId={sessionId} initialDetail={detail} />;
}
