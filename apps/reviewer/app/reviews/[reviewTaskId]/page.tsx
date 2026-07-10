import type { ReactElement } from "react";
import { getPublicEnv } from "@zayd/config/env/public";
import { DocumentReviewWorkspace } from "./workspace.js";

export default function Page(props: {
  params: {
    reviewTaskId: string;
  };
}): ReactElement {
  return (
    <DocumentReviewWorkspace
      apiBaseUrl={getPublicEnv().NEXT_PUBLIC_API_BASE_URL}
      reviewTaskId={props.params.reviewTaskId}
    />
  );
}
