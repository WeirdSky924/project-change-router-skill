# PCR 0.5 migration notes

PCR 0.5 keeps the 0.4 bundle, typed-finding, gate, authorization, and reuse APIs readable. The installed skill advances to `0.5.0`; existing repository bundles remain schema-v1 inputs and are never rewritten during installation.

Freshness is now split into path-set, content, and routing-knowledge layers. Index snapshots may include schema-v2 per-file records; legacy snapshots without them are incomplete. Task observations and working-index events stay in the external PCR runtime, are observation-only, and never grant write authority or baseline eligibility. Directed relation evidence tracks dependencies and reverse callers separately; missing, dynamic, unsupported, or symlink evidence remains incomplete. Trusted ancestry history is comparison-only, never current pass evidence.

P0/P1 findings, unknown evidence, owner conflicts, incomplete reuse, malformed reports, changed routing knowledge, and generated-output failures remain blocking. Duplicate findings are merged by stable identity; conflicting evidence becomes an invalid `evidence_conflict` finding. No migration step changes Godview, starts live services, promotes a dirty baseline, revives a consumed grant, or publishes to GitHub.

Upgrade validation is: staged install and verification, read-only bundle checks, cold/warm flow equivalence, malformed/path-escape and legacy-snapshot fixtures, isolated rollback, and the full test suite. Rebuild an existing bundle only under a separately authorized repository-boundary change.
