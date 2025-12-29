import PracticeRoom from "./practice-room";

export default async function PracticePage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const resolvedParams = await params;
  return <PracticeRoom sessionId={resolvedParams.sessionId} />;
}
