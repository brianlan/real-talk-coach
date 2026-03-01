"use client";

import { useEffect, useState } from "react";
import PhoneCallRoom from "./phone-call-room";

export default function PracticePage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const [sessionId, setSessionId] = useState<string | null>(null);

  useEffect(() => {
    params.then((resolvedParams) => {
      setSessionId(resolvedParams.sessionId);
    });
  }, [params]);

  if (!sessionId) {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <p>Loading...</p>
      </main>
    );
  }

  return <PhoneCallRoom sessionId={sessionId} />;
}
