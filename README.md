# Zayd

**Zayd — Thai Islamic Knowledge Assistant** เป็นโครงการโอเพนซอร์สสำหรับสร้างผู้ช่วยค้นคว้าความรู้อิสลามภาษาไทย โดยเน้นหลักฐานที่ตรวจสอบย้อนกลับได้ การแยกทัศนะตามมัซฮับ และกระบวนการตรวจทานโดยผู้รู้

> Zayd ไม่ใช่มุฟตี AI และไม่ใช่ระบบออกฟัตวาอัตโนมัติ

## เอกสารก่อนเริ่ม Coding

เอกสารหลักอยู่ใน [`docs/`](docs/README.md):

- Master Development Plan: [`docs/00_project/01_master_development_plan.md`](docs/00_project/01_master_development_plan.md)
- Product Requirements Document: [`docs/01_product/PRD.md`](docs/01_product/PRD.md)
- Software Requirements Specification 1.1: [`docs/02_requirements/SRS.md`](docs/02_requirements/SRS.md)
- System Architecture: [`docs/03_architecture/system_architecture.md`](docs/03_architecture/system_architecture.md)
- Data License Policy: [`docs/05_data/license_policy.md`](docs/05_data/license_policy.md)
- Madhhab Policy: [`docs/06_islamic_governance/madhhab_policy.md`](docs/06_islamic_governance/madhhab_policy.md)
- Scholar Review Policy: [`docs/06_islamic_governance/scholar_review_policy.md`](docs/06_islamic_governance/scholar_review_policy.md)
- Answer Safety Policy: [`docs/06_islamic_governance/answer_safety_policy.md`](docs/06_islamic_governance/answer_safety_policy.md)
- Security Architecture: [`docs/07_security/security_architecture.md`](docs/07_security/security_architecture.md)
- Evaluation Plan: [`docs/08_evaluation/evaluation_plan.md`](docs/08_evaluation/evaluation_plan.md)
- AI Coding Agent Policy: [`docs/09_development/ai_coding_agent_policy.md`](docs/09_development/ai_coding_agent_policy.md)

## Baseline v1.4

Baseline v1.4 ปรับปรุง `docs/02_requirements/` โดยกำหนด `SRS.md` ฉบับเต็มเป็น canonical specification เก็บฉบับย่อเป็น `SRS_summary.md` และขยาย Requirements Traceability Matrix ให้เชื่อมกับ Tasks และ Quality Gates อย่างละเอียด

## งานพัฒนา

โฟลเดอร์ [`tasks/`](tasks/README.md) มี Task ทั้งหมด 95 งาน ครอบคลุม EPIC-00 ถึง EPIC-14

เริ่มจาก:

1. อ่านเอกสารใน `docs/`
2. ตรวจ [`tasks/00_task_index.md`](tasks/00_task_index.md)
3. เริ่มจาก `TASK-00-01`
4. ทำงานตาม dependency
5. อัปเดต Completion Report และสถานะ Task ทุกครั้ง

## Repository Foundation

- Repository hygiene is defined in [`.gitignore`](.gitignore), [`.editorconfig`](.editorconfig), and [`.gitattributes`](.gitattributes).
- Commit conventions and protected-branch recommendations are documented in [CONTRIBUTING.md](CONTRIBUTING.md).
- The default branch should be `main`.

## สถานะ

เอกสารชุดนี้เป็น **Baseline v1.4 ก่อนเริ่ม Coding** และต้องผ่านการทบทวนจากทีมผลิตภัณฑ์ ทีมเทคนิค และคณะผู้รู้ก่อนเปลี่ยนสถานะเป็น Approved
