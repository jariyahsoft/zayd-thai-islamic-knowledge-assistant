import type { ReactElement } from "react";

import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "../user-app-client.js";
import { SettingsForm } from "./settings-form.js";

export default function SettingsPage(): ReactElement {
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;

  return (
    <UserAppClient activeNav="settings" apiBaseUrl={apiBaseUrl}>
      <section className="zayd-panel">
        <h2 id="settings-heading">ตั้งค่า</h2>
        <p>ปรับมัซฮับ ความยาวคำตอบ การแสดงอักษรอาหรับ ประวัติการสนทนา และธีม</p>
      </section>
      <SettingsForm />
    </UserAppClient>
  );
}