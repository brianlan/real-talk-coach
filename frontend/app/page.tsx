"use client";

import Link from "next/link";

export default function RootPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <h1
        style={{
          fontSize: "3.5rem",
          fontWeight: 700,
          marginBottom: "1rem",
          letterSpacing: "-0.02em",
          textAlign: "center",
        }}
      >
        Real Talk Coach
      </h1>
      <p
        style={{
          fontSize: "1.25rem",
          color: "#4a4a4a",
          marginBottom: "3rem",
          maxWidth: "600px",
          textAlign: "center",
          lineHeight: 1.6,
        }}
      >
        Master your communication skills with AI-guided practice scenarios.
      </p>

      <div style={{ display: "flex", gap: "24px", flexWrap: "wrap", justifyContent: "center" }}>
        <Link href="/practice">
          <button
            style={{
              padding: "16px 32px",
              fontSize: "1.125rem",
              borderRadius: 999,
              border: "none",
              background: "#2f2a24",
              color: "#f7f0e6",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Start Practice
          </button>
        </Link>
        <Link href="/signin">
          <button
            style={{
              padding: "16px 32px",
              fontSize: "1.125rem",
              borderRadius: 999,
              border: "2px solid #2f2a24",
              background: "transparent",
              color: "#2f2a24",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Sign In
          </button>
        </Link>
      </div>
    </main>
  );
}
