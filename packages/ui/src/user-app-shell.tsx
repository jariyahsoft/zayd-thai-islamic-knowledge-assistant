import type { ReactElement, ReactNode } from "react";

import { USER_APP_NAV_ITEMS, type UserAppNavId } from "./pwa.js";

export function UserAppShell(props: {
  readonly activeNav: UserAppNavId | "home";
  readonly children: ReactNode;
  readonly themeLabel: string;
  readonly onThemeToggle?: () => void;
}): ReactElement {
  return (
    <div className="zayd-user-shell">
      <header className="zayd-user-shell__header">
        <div className="zayd-user-shell__brand">
          <p className="zayd-user-shell__eyebrow">Zayd</p>
          <h1 className="zayd-user-shell__title">ผู้ช่วยความรู้อิสลามภาษาไทย</h1>
        </div>
        {props.onThemeToggle ? (
          <button
            type="button"
            className="zayd-user-shell__theme-toggle"
            aria-label={`สลับธีม (${props.themeLabel})`}
            onClick={props.onThemeToggle}
          >
            {props.themeLabel}
          </button>
        ) : null}
      </header>

      <main className="zayd-user-shell__main" id="main-content">
        {props.children}
      </main>

      <nav className="zayd-user-shell__nav" aria-label="เมนูหลัก">
        <a
          className={
            props.activeNav === "home"
              ? "zayd-user-shell__nav-link is-active"
              : "zayd-user-shell__nav-link"
          }
          href="/"
          aria-current={props.activeNav === "home" ? "page" : undefined}
        >
          หน้าแรก
        </a>
        {USER_APP_NAV_ITEMS.map((item) => (
          <a
            key={item.id}
            className={
              props.activeNav === item.id
                ? "zayd-user-shell__nav-link is-active"
                : "zayd-user-shell__nav-link"
            }
            href={item.href}
            aria-current={props.activeNav === item.id ? "page" : undefined}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </div>
  );
}