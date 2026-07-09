import type { ReactElement } from "react";

import { UserAppClient } from "../user-app-client.js";

export default function SettingsPage(): ReactElement {
  return (
    <UserAppClient activeNav="settings">
      <section className="zayd-panel">
        <h2>ตั้งค่า</h2>
        <p>การตั้งค่ามัซฮับและความยาวคำตอบจะมาใน TASK-09-04</p>
      </section>
      <div className="zayd-screen-placeholder">การตั้งค่าผู้ใช้จะอยู่ที่นี่</div>
    </UserAppClient>
  );
}