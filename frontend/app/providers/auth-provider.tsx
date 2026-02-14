"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { getUserId } from "@/lib/user/anonymous-id";

export interface User {
  id: string;
  type: "github" | "anonymous";
  isAuthenticated: boolean;
  name?: string;
  email?: string;
  image?: string;
}

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
});

export function useAuthContext() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const [anonymousId, setAnonymousId] = useState<string | null>(null);

  useEffect(() => {
    setAnonymousId(getUserId());
  }, []);

  const value = React.useMemo(() => {
    const isLoading = status === "loading" || (status === "unauthenticated" && !anonymousId);

    if (status === "authenticated" && session?.user) {
      return {
        user: {
          id: session.user.id ?? session.user.email ?? "unknown",
          type: "github" as const,
          isAuthenticated: true,
          name: session.user.name ?? undefined,
          email: session.user.email ?? undefined,
          image: session.user.image ?? undefined,
        },
        isLoading: false,
        isAuthenticated: true,
      };
    }

    if (status === "unauthenticated" && anonymousId) {
      return {
        user: {
          id: anonymousId,
          type: "anonymous" as const,
          isAuthenticated: false,
        },
        isLoading: false,
        isAuthenticated: false,
      };
    }

    return {
      user: null,
      isLoading: true,
      isAuthenticated: false,
    };
  }, [session, status, anonymousId]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
