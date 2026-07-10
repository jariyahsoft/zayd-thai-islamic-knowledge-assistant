import type { Metadata } from "next";
import type { ReactElement, ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Zayd Reviewer",
  description: "Reviewer dashboard for queue status, due work, and feedback triage",
};

export default function RootLayout(props: {
  children: ReactNode;
}): ReactElement {
  return (
    <html lang="th">
      <body>{props.children}</body>
    </html>
  );
}
