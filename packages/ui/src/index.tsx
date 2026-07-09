import type { ReactElement, ReactNode } from "react";

export { ArabicText } from "./arabic-text.js";
export {
  USER_APP_NAV_ITEMS,
  createUserAppManifest,
  validateManifestForInstallability,
  type UserAppNavId,
  type WebManifest,
} from "./pwa.js";
export { resolveTheme, toggleTheme, type ThemeMode } from "./theme.js";
export { UserAppShell } from "./user-app-shell.js";

export function AppShell(props: {
  readonly title: string;
  readonly subtitle?: string;
  readonly children: ReactNode;
}): ReactElement {
  return (
    <main>
      <h1>{props.title}</h1>
      {props.subtitle ? <p>{props.subtitle}</p> : null}
      <section>{props.children}</section>
    </main>
  );
}