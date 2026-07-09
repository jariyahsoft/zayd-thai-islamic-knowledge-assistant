import type { ReactElement } from "react";

import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "../user-app-client.js";
import { ChatInterface } from "./chat-interface.js";

export default async function ChatPage(props: {
  readonly searchParams: Promise<{ conversation?: string }>;
}): Promise<ReactElement> {
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;
  const searchParams = await props.searchParams;

  return (
    <UserAppClient activeNav="chat" apiBaseUrl={apiBaseUrl}>
      <ChatInterface
        apiBaseUrl={apiBaseUrl}
        initialConversationId={searchParams.conversation ?? null}
      />
    </UserAppClient>
  );
}