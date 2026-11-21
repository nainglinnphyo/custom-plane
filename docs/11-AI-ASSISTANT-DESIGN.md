# 11 — AI Project Assistant Design (PROPOSED, deferred module 15)

## 1. Existing

Plane already ships **LLM provider plumbing** (verified):

- `apps/api/plane/app/views/external/base.py` — `LLMProvider` base class with `OpenAIProvider`, `AnthropicProvider`, `GeminiProvider`, a provider registry and `get_llm_config()`; uses the `openai` SDK (`openai==1.63.2` in `pyproject.toml`).
- Instance-level config keys `LLM_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL` in `plane/utils/instance_config_variables/core.py` (managed via the admin app; the API key is a secret — never log it).
- Exposed as an "external" endpoint (`plane/app/urls/external.py`) for in-editor AI help (details unverified).
  This is a text-completion helper, **not** a project-aware assistant (no tools, no data access, no conversation storage found). The custom module should reuse the provider registry/config rather than add a second one.

## 2. Principles

- **Runs as the requesting user**: every data fetch goes through custom service functions that apply core membership + policy-layer checks. No service account with broad read access.
- Reuse the existing provider registry and instance-level `LLM_*` configuration (no new `AIProviderConfig` table unless per-workspace keys are required); keys never in logs, conversations or docs; a self-hosted/offline provider must remain possible (company data stays on-prem by default).
- Async: requests enqueue a Celery task; UI polls or streams (no general WebSocket push exists in core — see 02 §3.7).
- Read-only tools in v1 (summaries, risk hints, status reports). **No write actions** until an approval/confirmation step exists.
- Persist `AIConversation`/`AIMessage` with workspace scoping; retention and deletion follow the workspace.

## 3. Risks

Prompt injection from work-item text/comments (treat all content as data), data leakage to third-party providers (AGPL/privacy review), cost control (per-workspace quotas).

## 4. Testing

Mocked-provider unit tests, permission-boundary tests (assistant cannot return data the user cannot access), prompt-injection regression fixtures.

Detailed design is postponed until after PR 6 (D5).
