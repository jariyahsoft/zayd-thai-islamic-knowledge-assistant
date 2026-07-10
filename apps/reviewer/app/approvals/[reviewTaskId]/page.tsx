import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { ScholarApprovalWorkspace } from "./workspace.js";

export default function Page(props: {
  params: {
    reviewTaskId: string;
  };
}): ReactElement {
  return (
    <ScholarApprovalWorkspace
      apiBaseUrl={getPublicEnv().NEXT_PUBLIC_API_BASE_URL}
      reviewTaskId={props.params.reviewTaskId}
    />
  );
}
