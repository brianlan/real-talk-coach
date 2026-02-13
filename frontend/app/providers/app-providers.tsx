"use client";

import React, { createContext, useMemo, useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { getWsBase } from "@/services/api/base";

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
  const baseUrl = getWsBase();

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
