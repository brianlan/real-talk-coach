"use client";

import React, { createContext, useMemo, useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

export type WebSocketContextValue = {
  baseUrl: string;
  connect: (path: string) => WebSocket;
};

export const WebSocketContext = createContext<WebSocketContextValue | null>(null);

type AppProvidersProps = {
  children: React.ReactNode;
};

export function AppProviders({ children }: AppProvidersProps) {
  const [queryClient] = useState(() => new QueryClient());
  const baseUrl =
    process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000/ws";

  const wsContext = useMemo<WebSocketContextValue>(
    () => ({
      baseUrl,
      connect: (path: string) => new WebSocket(`${baseUrl}${path}`),
    }),
    [baseUrl]
  );

  return (
    <QueryClientProvider client={queryClient}>
      <WebSocketContext.Provider value={wsContext}>
        {children}
      </WebSocketContext.Provider>
    </QueryClientProvider>
  );
}
