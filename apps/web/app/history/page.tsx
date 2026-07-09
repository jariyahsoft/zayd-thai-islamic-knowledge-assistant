import type { ReactElement } from "react";

import { UserAppClient } from "../user-app-client.js";

export default function HistoryPage(): ReactElement {
  return (
    <UserAppClient activeNav="history">
      <section className="zayd-panel">
        <h2>ประวัติการสนทนา</h2>
        <p>ประวัติจะพร้อมใช้งานหลัง TASK-09-05 Conversation History</p>
      </section>
      <div className="zayd-screen-placeholder">ยังไม่มีประวัติที่บันทึก</div>
    </UserAppClient>
  );
}