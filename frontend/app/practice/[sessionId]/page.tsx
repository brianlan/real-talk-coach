import PracticeRoom from "./practice-room";

export default function PracticePage({
  params,
}: {
  params: { sessionId: string };
}) {
  return <PracticeRoom sessionId={params.sessionId} />;
}
