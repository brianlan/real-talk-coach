"use client";

import { signIn } from "next-auth/react";
import { useState } from "react";

export default function SignInPage() {
  const [isLoading, setIsLoading] = useState(false);

  const handleSignIn = async () => {
    setIsLoading(true);
    try {
      await signIn("github", { callbackUrl: "/practice" });
    } catch (error) {
      console.error("Sign in failed:", error);
      setIsLoading(false);
    }
  };

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
          fontSize: "2.5rem",
          fontWeight: 700,
          marginBottom: "2rem",
          letterSpacing: "-0.02em",
          textAlign: "center",
        }}
      >
        Sign In
      </h1>
      
      <button
        onClick={handleSignIn}
        disabled={isLoading}
        style={{
          padding: "16px 32px",
          fontSize: "1.125rem",
          borderRadius: 999,
          border: "none",
          background: "#2f2a24",
          color: "#f7f0e6",
          cursor: isLoading ? "not-allowed" : "pointer",
          fontWeight: 600,
          opacity: isLoading ? 0.7 : 1,
          transition: "opacity 0.2s",
        }}
      >
        {isLoading ? "Signing in..." : "Sign in with GitHub"}
      </button>
    </main>
  );
}
