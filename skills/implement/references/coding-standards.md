# Coding standards

Used by `implement` while writing code and by `review` when checking it.

Precedence, highest first: the repo's own rules (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`,
style guides, linter/formatter config), then `TECHNICAL-DESIGN.md`, then the defaults below.
Read the repo's rules before the first slice; when a default conflicts with them, theirs wins.

- **Design conformance**: API paths, request/response shapes, status codes, data model fields,
  and component boundaries match the technical design. A needed deviation is raised with the
  user and logged, not made silently.
- **Security**: validate and bound every external input at the boundary; parameterized queries,
  no string-built SQL/shell/HTML; enforce authN/authZ server-side on every new entry point per
  the design's security model; secrets from config/env only, never in code, tests, or logs;
  no PII or tokens in logs or error messages.
- **Error handling**: fail fast at boundaries with specific, actionable errors; never swallow
  exceptions or return silent defaults; map domain errors to the API's documented error shape;
  release resources deterministically (context managers, `finally`, `defer`, `using`).
- **Readability**: names from the domain glossary / PRD vocabulary; small functions with one
  job; no magic numbers — named constants; comments explain *why*, not *what*; match the
  surrounding code's comment density and idiom.
- **Structure**: dependencies point inward (domain ← application ← adapters); inject
  collaborators rather than constructing them inline, so tests don't need global patching;
  prefer composition and the simplest thing that passes — no speculative abstractions,
  config flags, or extension points no requirement asks for (YAGNI); no copy-paste — reuse
  or extract once there's a second real caller.
- **Performance**: meet the NFR numbers that apply to the slice (latency, limits, payload
  size); avoid N+1 queries and unbounded loads/collections; paginate list endpoints.
- **Observability**: log at boundaries and on failures with enough context to debug
  (request/entity IDs), at the repo's existing log levels; add the metrics/traces the design
  names.
- **Tests**: deterministic (no real clock, network, or randomness without control), isolated,
  fast; assert behavior, not implementation; mock only at architectural boundaries.
