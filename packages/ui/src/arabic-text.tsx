import type { CSSProperties, ReactElement, ReactNode } from "react";

export function ArabicText(props: {
  readonly children: ReactNode;
  readonly className?: string;
  readonly style?: CSSProperties;
}): ReactElement {
  return (
    <span
      dir="rtl"
      lang="ar"
      className={props.className}
      style={{
        unicodeBidi: "isolate",
        overflowWrap: "anywhere",
        ...props.style,
      }}
    >
      {props.children}
    </span>
  );
}