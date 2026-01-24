"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { practiceAgain } from "@/services/api/history";

type PracticeAgainButtonProps = {
  sessionId: string;
};

export default function PracticeAgainButton({ sessionId }: PracticeAgainButtonProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    if (loading) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const session = await practiceAgain(sessionId);
      if (session?.id) {
        router.push(`/practice/${session.id}`);
      } else {
        setError("Unable to start a new session.");
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        style={{
          padding: "10px 18px",
          borderRadius: 999,
          border: "none",
          background: "#2f2a24",
          color: "#f7f0e6",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Starting..." : "Practice again"}
      </button>
      {error ? <p style={{ margin: 0, color: "#b24332" }}>{error}</p> : null}
    </div>
  );
}
