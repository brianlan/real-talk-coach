import type { Metadata } from "next";

import { AppProviders } from "./providers/app-providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Real Talk Coach",
  description: "Practice conversations with an AI coach.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
