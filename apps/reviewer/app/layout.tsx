import type { Metadata } from "next";
import type { ReactElement, ReactNode } from "react";

export const metadata: Metadata = {
  title: "Zayd Reviewer",
  description: "Zayd reviewer application workspace placeholder",
};

export default function RootLayout(props: {
  children: ReactNode;
}): ReactElement {
  return (
    <html lang="en">
      <body>{props.children}</body>
    </html>
  );
}
