import type { ReactElement } from "react";

import { formatWarning } from "./labels.js";

export function SourceStatusWarnings(props: {
  readonly warnings: readonly string[];
}): ReactElement | null {
  if (props.warnings.length === 0) {
    return null;
  }

  return (
    <div className="zayd-citation-warnings" role="alert">
      <p className="zayd-citation-warnings__title">คำเตือนเกี่ยวกับแหล่งอ้างอิง</p>
      <ul>
        {props.warnings.map((warning) => (
          <li key={warning}>{formatWarning(warning)}</li>
        ))}
      </ul>
    </div>
  );
}