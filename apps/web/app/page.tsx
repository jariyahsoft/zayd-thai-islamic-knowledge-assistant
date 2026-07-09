import type { ReactElement } from "react";
import { ArabicText } from "@zayd/ui";
import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "./user-app-client.js";

export default function Page(): ReactElement {
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;

  return (
    <UserAppClient activeNav="home" apiBaseUrl={apiBaseUrl}>
      <section className="zayd-panel">
        <h2>ยินดีต้อนรับ</h2>
        <p>
          แอปนี้ออกแบบสำหรับมือถือเป็นหลัก พร้อมธีมสว่าง/มืด และการแสดงข้อความภาษาไทยและอาหรับอย่างปลอดภัย
        </p>
        <p>
          <a className="zayd-home__link" href="/saved">
            ดูคำตอบที่บันทึก
          </a>
        </p>
      </section>

      <section className="zayd-panel zayd-typography-demo" aria-label="ตัวอย่างการแสดงผลภาษา">
        <h2>ตัวอย่างการแสดงผลภาษา</h2>
        <p className="zayd-typography-demo__thai">
          คำถามตัวอย่าง: การละหมาดตามมัซฮับชาฟิอีมีเงื่อนไขอย่างไร
        </p>
        <p className="zayd-typography-demo__arabic">
          <ArabicText>بسم الله الرحمن الرحيم</ArabicText>
        </p>
      </section>
    </UserAppClient>
  );
}