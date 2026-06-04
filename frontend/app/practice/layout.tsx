"use client";

import PracticeSidebar from "@/components/PracticeSidebar";

export default function PracticeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <PracticeSidebar />
      <div style={{ marginLeft: 260, flex: 1, position: "relative" }}>
        {children}
      </div>
    </div>
  );
}
