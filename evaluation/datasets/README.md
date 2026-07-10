# Zayd-IslamicQA-TH Starter Dataset

This directory contains the starter dataset `Zayd-IslamicQA-TH` version `1.0.0` for testing and evaluating the Thai Islamic Knowledge Assistant (Zayd).

## Contents

- `starter_set_manifest.json` — Dataset metadata and licensing terms.
- `public_cases.json` — Approved public benchmark cases with redistributable source licenses.
- `private_cases.json` — Approved private restricted cases (e.g. safety-critical, out-of-domain, or restricted-context).

## Seeding Dataset

The starter set can be loaded into the database programmatically via the `seed_starter_set` module:

```python
from pathlib import Path
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_evaluation import seed_starter_set

uow = SQLAlchemyUnitOfWork(session_factory)
result = seed_starter_set(
    uow=uow,
    dataset_dir=Path("evaluation/datasets"),
    actor_user_id=actor_uuid,
    reviewed_by=reviewer_uuid,
    permissions=frozenset({"evaluations.manage"}),
)
print(f"Seeded {result.created_cases} cases successfully.")
```

## Governance and Licensing

All cases here are manually reviewed and approved by human scholars. Under no circumstances should raw AI-generated answers be committed without scholar verification. Public domain and CC-BY-SA cases reside in `public_cases.json` while restricted/proprietary sources are separated in `private_cases.json`.
