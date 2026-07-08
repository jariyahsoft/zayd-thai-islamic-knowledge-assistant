# Query Expansion

Status: implemented for TASK-07-06.

Query expansion produces deterministic Thai, Arabic, English, and terminology
variant queries for retrieval. It is local-first and does not call an external
provider, so retrieval remains available when provider-backed expansion is
disabled or unavailable.

## Contract

`QueryExpansionService` accepts:

- query text
- declared query language: `th`, `ar`, `en`, or `mixed`
- optional madhhab metadata
- `QueryExpansionPolicy`

It returns:

- original query
- detected language
- expansion and policy versions
- normalized and terminology-variant expansions
- a structured trace suitable for `retrieval_runs.query_expansions`

## Policy Controls

`QueryExpansionPolicy` can:

- disable expansion completely
- disable cross-language variants
- disable terminology variants
- preserve named references by suppressing terminology substitutions
- limit maximum expansion count
- record a policy version

Invalid policy values fail closed with stable errors. Expansion never modifies
metadata filters such as madhhab, source type, license status, or reliability.

## Intent Preservation

Named references such as `book:v1:reference` and common `quran 2:255` /
`hadith 42` forms are treated as high-intent references. When named-reference
preservation is enabled, the service returns only the original normalized query
instead of adding terminology variants that could dilute exact-reference
retrieval.

## Reviewed Terminology Fixtures

The built-in fixtures are intentionally small and conservative:

- prayer: `ละหมาด`, `ซอลาต`, `الصلاة`, `صلاة`, `prayer`, `salat`, `salah`
- hadith: `ฮะดีษ`, `หะดีษ`, `حديث`, `الحديث`, `hadith`
- quran: `อัลกุรอาน`, `กุรอาน`, `القرآن`, `قرآن`, `quran`, `al-quran`
- zakat: `ซะกาต`, `ซะกาห์`, `زكاة`, `الزكاة`, `zakat`
- fasting: `ถือศีลอด`, `ศีลอด`, `صيام`, `الصيام`, `fasting`, `sawm`
- ablution: `วุฎูอ์`, `อาบน้ำละหมาด`, `وضوء`, `الوضوء`, `wudu`, `ablution`

These fixtures are regression-tested for semantic drift. The set should remain
small until reviewed terminology governance is available.

## Trace

The trace includes:

- expansion version
- policy version
- normalization framework version
- query and detected language
- madhhab metadata
- disabled/limited flags
- named-reference preservation flag
- expansion items with language, kind, source terms, and concept ID

The trace contains query text by design and should be handled with the same
sensitive-data controls as `retrieval_runs.query_original`.
