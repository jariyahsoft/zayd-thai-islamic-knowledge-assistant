import type { ReactElement, ReactNode } from "react";

export function AppShell(props: {
  readonly title: string;
  readonly subtitle?: string;
  readonly children: ReactNode;
}): ReactElement {
  return (
    <main>
      <h1>{props.title}</h1>
      {props.subtitle ? <p>{props.subtitle}</p> : null}
      <section>{props.children}</section>
    </main>
  );
}
