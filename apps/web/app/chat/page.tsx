import type { ReactElement } from "react";

import { UserAppClient } from "../user-app-client.js";

export default function ChatPage(): ReactElement {
  return (
    <UserAppClient activeNav="chat">
      <section className="zayd-panel">
        <h2>ถามคำถาม</h2>
        <p>หน้าสนทนาจะเชื่อมต่อกับ SSE streaming chat ใน TASK-09-02</p>
      </section>
      <div className="zayd-screen-placeholder">พื้นที่แชทจะอยู่ที่นี่</div>
    </UserAppClient>
  );
}