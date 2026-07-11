# Performance and Load Testing

Performance and load testing verify that Zayd handles concurrent chats, retrieval latency, worker throughput, and database capacity within specified targets, and degrades safely under peak loads.

## Performance Targets (NFR)

The system is tested against the following non-functional requirements (NFRs) documented in the System Requirements Specification (SRS §32):

| Target ID | Requirement | Target Metric |
|-----------|-------------|---------------|
| `NFR-PERF-001` | Front page first load time | Under 3 seconds on standard mobile network |
| `NFR-PERF-002` | Stream initialization latency | Under 5 seconds |
| `NFR-PERF-003` | Local Retrieval execution | Under 2 seconds under normal conditions |
| `NFR-PERF-004` | General answer generation completion | Under 20 seconds |

---

## Core System Bottlenecks

### 1. Upstream Model Latency
The primary latency contributor is the upstream LLM provider response generation. In local Swarm/Compose deployments (e.g. using Ollama/vLLM), generation times depend on hardware limits. The orchestrator's timeout parameters dictate cancellation behaviors to prevent hung sockets.

### 2. Document Parsing and Ingestion
Extracted text normalization and semantic chunking are computationally heavy. Large PDF uploads may experience ingestion latency before indexing occurs.

### 3. Vector Search
knowledge retrieval uses `pgvector` HNSW indexes. When database capacity grows, index lookup latencies are guarded by query structure filters limits.

---

## Safe Degradation and Failure Gates

When systems scale past standard thresholds, Zayd degrades safely as follows:

| Component | Saturated State | Safe Degradation Action |
|-----------|-----------------|------------------------|
| **LLM Provider** | Rate Limit (429) or Timeout | Returns `PROVIDER_RATE_LIMIT` or `ANSWER_TIMEOUT` and fails closed cleanly. |
| **Worker Queue** | Heavy Ingestion load | Retains tasks in worker queue without blocking chat. |
| **CORS / Rate Limit** | Client request flood | custom global middleware limits requests (10/min strict, 100/min normal) and exits with HTTP 429. |

---

## Running Performance Tests

Simulate concurrent workloads, database soak tests, provider failure injections, and SQLite query plan checks locally:

```bash
# Run all performance test scenarios
uv run pytest services/evaluation/tests/test_performance.py -v
```

### Explaining Query Plans
To audit database index health and query costs, execute:

```sql
EXPLAIN QUERY PLAN SELECT * FROM evaluation_cases WHERE id = 'uuid-here';
```

Verify that the result plan mentions `SEARCH TABLE` (Index lookup) rather than `SCAN TABLE` (Full-table scan).
