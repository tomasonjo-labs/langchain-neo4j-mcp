# 🔍⁉️ Neo4j MCP Server (with Throttling & Truncation)

## 🌟 Overview

This fork of the Neo4j MCP Server adds **query throttling, result sanitization, and token-based truncation** to improve LLM usability and prevent oversized responses. It is still a Model Context Protocol (MCP) server for running Cypher queries against Neo4j, but with safer defaults for large or noisy datasets.

## 🆕 Key Improvements

### ⏱️ Query Timeout

All queries now respect a configurable timeout:

* Controlled by the environment variable `QUERY_TIMEOUT` (default: `10` seconds).
* Ensures runaway queries are automatically terminated.
* Applied through `neo4j.Query(query, timeout=...)`.

```bash
# Example
export QUERY_TIMEOUT=15
```

### 🧹 Result Sanitization

A new sanitization function `_value_sanitize` removes oversized or embedding-like values from query results:

* Lists larger than **52 items** are dropped.
* Deeply nested dicts and lists are pruned recursively.
* Helps keep responses focused and prevents flooding the LLM context.

### ✂️ Token-Based Truncation

* After sanitization, results are tokenized with **`tiktoken`** (defaulting to GPT-4 tokenizer).
* Responses are truncated to **2048 tokens**.
* Guarantees compatibility with downstream LLMs and reduces prompt inflation.

### 📝 Logging

The logger name has changed for clarity:

```python
logger = logging.getLogger("mcp_neo4j_cypher_throttle")
```

---

## 🔧 Usage Notes

* **Large results** will be sanitized and truncated before being returned.
* **Token limit** defaults to 2048 (tuned for GPT-4), but can be adjusted in `_truncate_string_to_tokens`.
* **Schema queries** (`get_neo4j_schema`) are unchanged.
* **Read queries** (`read_neo4j_cypher`) enforce read-only mode and will auto-truncate results.
* **Write queries** (`write_neo4j_cypher`) still support full counters, but are subject to timeout.
