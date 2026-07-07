import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { AdminConsole } from "./source-license-admin-console.js";

export default function Page(): ReactElement {
  return <AdminConsole apiBaseUrl={getPublicEnv().NEXT_PUBLIC_API_BASE_URL} />;
}
