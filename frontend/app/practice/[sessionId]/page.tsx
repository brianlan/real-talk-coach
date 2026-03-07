"use client";

import { useEffect, useState } from "react";
import PhoneCallRoom from "./phone-call-room";
import PracticeRoom from "./practice-room";

function isPhoneCallRoomEnabled(): boolean {
  const disabled = process.env.NEXT_PUBLIC_PHONE_CALL_ROOM_DISABLED;
  return disabled !== "1";
}

export default function PracticePage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [phoneCallEnabled, setPhoneCallEnabled] = useState<boolean>(true);

  useEffect(() => {
    params.then((resolvedParams) => {
      setSessionId(resolvedParams.sessionId);
    });
    setPhoneCallEnabled(isPhoneCallRoomEnabled());
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

  if (!phoneCallEnabled) {
    return <PracticeRoom sessionId={sessionId} />;
  }

  return <PhoneCallRoom sessionId={sessionId} />;
}
