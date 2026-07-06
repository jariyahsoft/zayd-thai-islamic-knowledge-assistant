import threading
import time

import pytest
from zayd_common.exceptions import ConcurrencyConflictError


class MutableRecord:
    """Mock database record to simulate optimistic locking with row_version."""

    def __init__(self, record_id: str, status: str, row_version: int):
        self.record_id = record_id
        self.status = status
        self.row_version = row_version
        self._lock = threading.Lock()

    def update_status(self, to_status: str, expected_version: int) -> None:
        with self._lock:
            # Check row_version for concurrency conflicts
            if self.row_version != expected_version:
                raise ConcurrencyConflictError(
                    f"Conflict updating record {self.record_id}: "
                    f"expected version {expected_version}, but found {self.row_version}"
                )

            # Introduce minor timing delay to highlight race conditions
            time.sleep(0.01)
            self.status = to_status
            self.row_version += 1


def test_concurrency_conflict_raises_error() -> None:
    record = MutableRecord("doc-1", "draft", 1)

    # Process A and B both read the record at the same version
    version_a = record.row_version
    version_b = record.row_version

    # Process A succeeds first
    record.update_status("uploaded", version_a)
    assert record.status == "uploaded"
    assert record.row_version == 2

    # Process B tries to update using the stale version
    with pytest.raises(ConcurrencyConflictError) as exc_info:
        record.update_status("parsing", version_b)

    assert exc_info.value.error_code == "CONCURRENCY_CONFLICT"
    assert "Conflict updating record" in str(exc_info.value)


def test_concurrent_threading_race() -> None:
    # 10 threads competing to perform the initial update starting at version 1
    record = MutableRecord("doc-1", "draft", 1)
    initial_version = record.row_version

    results: list[bool] = []
    errors: list[ConcurrencyConflictError] = []

    def worker() -> None:
        try:
            record.update_status("uploaded", initial_version)
            results.append(True)
        except ConcurrencyConflictError as e:
            errors.append(e)
            results.append(False)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify exactly one worker succeeded, and the rest raised ConcurrencyConflictError
    assert results.count(True) == 1
    assert results.count(False) == 9
    assert len(errors) == 9
    for err in errors:
        assert err.error_code == "CONCURRENCY_CONFLICT"
