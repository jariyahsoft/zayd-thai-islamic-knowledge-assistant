import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { createApiClient } from "@zayd/api-client";
import { AppShell } from "@zayd/ui";

export default function Page(): ReactElement {
  const client = createApiClient({
    baseUrl: getPublicEnv().NEXT_PUBLIC_API_BASE_URL,
  });

  return (
    <AppShell title="Zayd Web" subtitle={client.baseUrl}>
      User application workspace placeholder.
    </AppShell>
  );
}
