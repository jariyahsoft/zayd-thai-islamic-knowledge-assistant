import type { ReactElement } from "react";

import { CitationDetailView } from "@zayd/citations";
import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "../../user-app-client.js";

export default async function CitationDetailPage(props: {
  readonly params: Promise<{ citationId: string }>;
}): Promise<ReactElement> {
  const { citationId } = await props.params;
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;

  return (
    <UserAppClient activeNav="chat" apiBaseUrl={apiBaseUrl}>
      <section className="zayd-panel zayd-citation-page">
        <h2>รายละเอียดอ้างอิง</h2>
        <CitationDetailView apiBaseUrl={apiBaseUrl} citationRef={decodeURIComponent(citationId)} />
      </section>
    </UserAppClient>
  );
}