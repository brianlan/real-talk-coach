"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { fetchHistoryList } from "@/services/api/history";
import { usePathname } from "next/navigation";
import { useUser } from "@/hooks/useUser";

export default function PracticeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user } = useUser();
  const { data: historyData } = useQuery({
    queryKey: ["history", user?.id],
    queryFn: () =>
      fetchHistoryList({ historyStepCount: 0, pageSize: 20, userId: user?.id }),
  });

  const sessions = historyData?.items ?? [];

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 260,
          background: "#e5dccf",
          borderRight: "1px solid #d4c8b8",
          display: "flex",
          flexDirection: "column",
          position: "fixed",
          top: 0,
          bottom: 0,
          left: 0,
          zIndex: 10,
          overflowY: "auto",
        }}
      >
        <div style={{ padding: "24px 16px" }}>
          <Link
            href="/practice"
            style={{
              display: "block",
              width: "100%",
              padding: "12px",
              background: "#2f2a24",
              color: "#f7f0e6",
              textAlign: "center",
              borderRadius: 8,
              textDecoration: "none",
              fontWeight: 600,
              marginBottom: 24,
            }}
          >
            + New Practice
          </Link>

          <h3
            style={{
              fontSize: 12,
              textTransform: "uppercase",
              letterSpacing: 1.5,
              color: "#6b6054",
              marginBottom: 12,
            }}
          >
            History
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sessions.map((session) => {
              const isActive = pathname === `/practice/${session.id}`;
              const date = session.startedAt 
                ? new Date(session.startedAt).toLocaleDateString() 
                : "Unknown date";
                
              return (
                <Link
                  key={session.id}
                  href={`/practice/${session.id}`}
                  style={{
                    display: "block",
                    padding: "10px 12px",
                    borderRadius: 6,
                    background: isActive ? "#fff" : "transparent",
                    color: isActive ? "#2f2a24" : "#4a4a4a",
                    textDecoration: "none",
                    border: isActive ? "1px solid #d4c8b8" : "1px solid transparent",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ fontWeight: 500, fontSize: 14, marginBottom: 4 }}>
                    Practice Session
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.7 }}>{date}</div>
                </Link>
              );
            })}
          </div>
        </div>
      </aside>

      <div style={{ marginLeft: 260, flex: 1, position: "relative" }}>
        {children}
      </div>

    </div>
  );
}
