# Security Policy

## Supported Versions

This is a research artifact. Security fixes are applied to the current main branch only.

## Reporting a Vulnerability

**Do not report security vulnerabilities as public GitHub issues.**

To report a security vulnerability (e.g., a dependency with a known CVE,
an unsafe code pattern, or a credentials handling problem):

1. Open a **private** GitHub Security Advisory (use the "Security" tab →
   "Report a vulnerability" button)
2. Or email the maintainers directly if the Security Advisory feature is unavailable

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

We will acknowledge receipt within 72 hours and aim to resolve confirmed
vulnerabilities within 14 days.

## Secrets Handling

This project requires an API key for LLM baseline reproduction (`GROQ_API_KEY`).

**Never commit API keys or secrets to this repository.**

- Copy `.env.example` to `.env` and fill in values locally
- `.env` is listed in `.gitignore` and will not be tracked
- The `.env.example` file contains only empty placeholders — no real values

If you discover a real secret accidentally committed to the repository history,
report it immediately via the process above so it can be rotated and purged.
