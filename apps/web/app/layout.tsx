import type { Metadata, Viewport } from "next";
import type { ReactElement, ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Zayd",
  description:
    "Mobile-first Thai Islamic knowledge assistant with verified citations.",
  applicationName: "Zayd",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Zayd",
  },
  formatDetection: {
    telephone: false,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#1f4d3a" },
    { media: "(prefers-color-scheme: dark)", color: "#101816" },
  ],
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout(props: {
  children: ReactNode;
}): ReactElement {
  return (
    <html lang="th" suppressHydrationWarning>
      <body>{props.children}</body>
    </html>
  );
}