# Evaluation Plan — Zayd 1.0

## 1. Purpose

วัดความสามารถของระบบทั้ง retrieval, answer grounding, citation, madhhab, safety, ภาษาไทย ประสิทธิภาพ และต้นทุน ก่อน release และทุกการเปลี่ยนแปลงสำคัญ

## 2. Evaluation Layers

### Layer A — Data and ingestion

- parser accuracy
- page/reference preservation
- normalization invariants
- metadata completeness

### Layer B — Retrieval

- Recall@5, Recall@10
- MRR
- precision
- exact reference success
- metadata filter correctness
- multilingual query success

### Layer C — Answer and citation

- answer correctness
- citation correctness
- citation completeness
- fabricated citation rate
- claim support rate
- quote accuracy

### Layer D — Islamic governance

- madhhab consistency
- differences-of-opinion presentation
- scholar approval rate
- source hierarchy compliance

### Layer E — Safety

- high-risk routing accuracy
- abstention accuracy
- unsafe answer rate
- prompt injection resistance
- personal-data handling

### Layer F — Product and operations

- latency
- availability
- cost per answer
- local hit/fallback rate
- user feedback rate
- reviewer turnaround indicators

## 3. Benchmark Dataset

ชื่อ: `Zayd-IslamicQA-TH`

หมวดเริ่มต้น:

- Taharah
- Salah
- Fasting
- Basic Aqidah
- Quran/Hadith lookup
- Madhhab differences
- Unanswerable
- High-risk
- Adversarial and spelling variants

ทุก case ต้องมี:

- ID/category/risk
- Thai question and variants
- expected behavior
- accepted evidence/citations
- madhhab metadata
- reviewer and review date
- license status

## 4. Public and Private Sets

- Public development set สำหรับ contributors
- Private holdout set ลดการ optimize ตรงข้อสอบ
- Incident-derived regression set ต้อง redact PII

## 5. Metrics and Initial Gates

| Metric | Release target |
|---|---:|
| Citation correctness | ≥ 98% |
| Fabricated citation | 0 in release set |
| Retrieval Recall@5, MVP categories | ≥ 90% |
| High-risk routing | ≥ 95% |
| Scholar approval, MVP answer set | ≥ 90% |
| Critical unsafe answer | 0 |

Thresholds เป็น baseline และเปลี่ยนได้ผ่าน approved evaluation policy

## 6. Comparison Protocol

ทุก run ต้องบันทึก:

- git commit
- dataset version
- model/provider
- prompt/policy/retriever versions
- embedding/reranker
- date, hardware/config
- latency/token/cost

ห้ามเปรียบเทียบ run ที่ใช้ dataset หรือ grading rubric ต่างกันโดยไม่แจ้ง

## 7. Human Review

Scholar rubric:

- ถูกต้องตามแหล่ง
- อธิบายเงื่อนไขครบ
- ระบุมัซฮับ/ความเห็นต่าง
- citation สนับสนุน claim
- ภาษาชัดและไม่ชี้นำเกินหลักฐาน
- ควร abstain หรือไม่

ต้องวัด reviewer disagreement และ escalate cases ที่ไม่ลงรอย

## 8. Automated Evaluation Cautions

LLM-as-judge ใช้เป็นสัญญาณเสริม ไม่ใช่ผู้อนุมัติทางศาสนา ต้อง pin judge version และตรวจตัวอย่างด้วยมนุษย์

## 9. Regression Process

- ทุก confirmed incident สร้าง candidate case
- redact personal data
- scholar/QA approve expected behavior
- add to regression set
- CI/nightly run appropriate subset

## 10. Release Report

Release report ต้องมี:

- metrics vs previous release
- regressions/improvements
- known limitations
- failing categories
- model/provider costs
- scholar sign-off summary
- security and restore gate results
