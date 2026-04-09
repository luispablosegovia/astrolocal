# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue.**
2. Email the maintainers directly or use GitHub's private vulnerability reporting.
3. Include steps to reproduce and potential impact.
4. We will respond within 72 hours.

## Security Design Principles

AstroLocal is designed with privacy and security as core principles:

### Data Privacy
- **100% local execution** — no data leaves your machine
- **No telemetry, no analytics, no tracking**
- **PII redaction in logs** — birth dates and coordinates are redacted by default
- **Anonymized IDs** — logs use SHA-256 hashed identifiers, never names

### Input Validation
- **Pydantic models** validate all user input at the boundary
- **Name/city sanitization** removes control characters
- **Date validation** rejects impossible dates (Feb 30, etc.)
- **Coordinate bounds** enforce valid geographic ranges
- **Nation codes** must be exactly 2 uppercase letters (ISO 3166-1)

### Database Security
- **Parameterized queries only** — no string interpolation in SQL
- **WAL mode** for safe concurrent access
- **Foreign keys enforced** for referential integrity
- **Path traversal prevention** — database path validated against home directory

### LLM Communication
- **Localhost-only by default** — LLM base URL must be localhost or private network
- **Request timeouts** prevent indefinite hangs
- **Rate limiting** prevents resource exhaustion
- **Prompt size limits** (256KB max) prevent memory issues
- **Retry with backoff** for transient failures

### Supply Chain
- **Pinned dependency ranges** in pyproject.toml
- **Bandit** static security analysis in CI
- **Safety** dependency vulnerability scanning in CI
- **Ruff** linting with security rules enabled (S prefix)

### What We Don't Do
- No authentication (it's a local app)
- No network exposure by default
- No file uploads from untrusted sources
- No eval(), exec(), or dynamic code execution
- No pickle deserialization
- No secrets or API keys required
