import type { ReactElement } from "react";

import { getPublicEnv } from "@zayd/config/env/public";

import { UserAppClient } from "../user-app-client.js";
import { HistoryList } from "./history-list.js";

export default function HistoryPage(): ReactElement {
  const apiBaseUrl = getPublicEnv().NEXT_PUBLIC_API_BASE_URL;

  return (
    <UserAppClient activeNav="history" apiBaseUrl={apiBaseUrl}>
      <section className="zayd-panel">
        <h2 id="history-heading">ประวัติการสนทนา</h2>
        <p>ค้นหา เปิด ลบ และลบประวัติทั้งหมดได้จากหน้านี้</p>
      </section>
      <HistoryList apiBaseUrl={apiBaseUrl} />
    </UserAppClient>
  );
}