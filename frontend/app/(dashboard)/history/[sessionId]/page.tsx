import HistoryDetail from "./history-detail";

const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function fetchHistoryDetail(sessionId: string) {
  const response = await fetch(
    `${apiBase}/api/sessions/${sessionId}?historyStepCount=2`,
    {
      cache: "no-store",
    }
  );
  if (!response.ok) {
    return null;
  }
  return response.json();
}

export default async function HistoryDetailPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const resolvedParams = await params;
  const detail = await fetchHistoryDetail(resolvedParams.sessionId);
  if (!detail) {
    return (
      <main style={{ padding: "48px 24px" }}>
        <p>Session not found.</p>
      </main>
    );
  }

  return (
    <HistoryDetail sessionId={resolvedParams.sessionId} initialDetail={detail} />
  );
}
