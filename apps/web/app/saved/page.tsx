import type { ReactElement } from "react";

import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "../user-app-client.js";
import { SavedList } from "./saved-list.js";

export default function SavedPage(): ReactElement {
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;

  return (
    <UserAppClient activeNav="home" apiBaseUrl={apiBaseUrl}>
      <section className="zayd-panel">
        <h2 id="saved-heading">คำตอบที่บันทึก</h2>
        <p>คำตอบที่บันทึกอ้างอิงจากคำตอบในระบบ ไม่ได้คัดลอกข้อความแหล่งอ้างอิงแยกต่างหาก</p>
      </section>
      <SavedList apiBaseUrl={apiBaseUrl} />
    </UserAppClient>
  );
}