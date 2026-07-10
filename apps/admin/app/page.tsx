import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { AdminWorkspace } from "./workspace.js";

export default function Page(): ReactElement {
  return <AdminWorkspace apiBaseUrl={getPublicEnv().NEXT_PUBLIC_API_BASE_URL} />;
}
