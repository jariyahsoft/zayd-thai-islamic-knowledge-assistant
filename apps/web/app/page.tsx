import type { ReactElement } from "react";
import { ArabicText } from "@zayd/ui";

import { UserAppClient } from "./user-app-client.js";

export default function Page(): ReactElement {
  return (
    <UserAppClient activeNav="home">
      <section className="zayd-panel">
        <h2>ยินดีต้อนรับ</h2>
        <p>
          แอปนี้ออกแบบสำหรับมือถือเป็นหลัก พร้อมธีมสว่าง/มืด และการแสดงข้อความภาษาไทยและอาหรับอย่างปลอดภัย
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