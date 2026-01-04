import type { ReactNode } from "react";

import { AdminNav } from "@/components/admin/AdminNav";

export const metadata = {
  title: "Admin | Real Talk Coach",
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <main
      style={{
        padding: "32px 24px",
        maxWidth: 1200,
        margin: "0 auto",
      }}
    >
      <header style={{ marginBottom: 16 }}>
        <p style={{ textTransform: "uppercase", letterSpacing: 2, fontSize: 12 }}>
          Admin
        </p>
        <h1 style={{ fontSize: 32, margin: "4px 0 12px" }}>Data management</h1>
        <p style={{ color: "#4a433b" }}>
          Manage skills, scenarios, sessions, and audit history for the coaching app.
        </p>
        <AdminNav />
      </header>
      <section>{children}</section>
    </main>
  );
}
