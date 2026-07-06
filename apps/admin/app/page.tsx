import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { AppShell } from "@zayd/ui";

export default function Page(): ReactElement {
  return (
    <AppShell title="Zayd Admin" subtitle={getPublicEnv().NEXT_PUBLIC_API_BASE_URL}>
      Admin workspace placeholder.
    </AppShell>
  );
}
