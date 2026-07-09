import type { ReactElement } from "react";

import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "../user-app-client.js";
import { ChatInterface } from "./chat-interface.js";

export default function ChatPage(): ReactElement {
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;

  return (
    <UserAppClient activeNav="chat">
      <ChatInterface apiBaseUrl={apiBaseUrl} />
    </UserAppClient>
  );
}