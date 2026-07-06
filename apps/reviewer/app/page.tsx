import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { AppShell } from "@zayd/ui";

export default function Page(): ReactElement {
  return (
    <AppShell title="Zayd Reviewer" subtitle={getPublicEnv().NEXT_PUBLIC_API_BASE_URL}>
      Reviewer workspace placeholder.
    </AppShell>
  );
}
