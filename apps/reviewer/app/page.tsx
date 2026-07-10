import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { ReviewerDashboard } from "./reviewer-dashboard.js";

export default function Page(): ReactElement {
  return <ReviewerDashboard apiBaseUrl={getPublicEnv().NEXT_PUBLIC_API_BASE_URL} />;
}
