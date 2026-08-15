# Veridoc — Documentation Index

Single home for all Veridoc documentation. Veridoc is a local-first RAG
document Q&A platform with encrypted-at-rest storage and strict startup
validation.

**Start here:** [architecture.md](architecture.md) (system map) →
[folder_structure.md](folder_structure.md) (repo tree) →
[technical/TechSpec.md](technical/TechSpec.md) (build details).

## Structure

```
docs/
├── README.md                      ← this index
├── architecture.md                system architecture
├── folder_structure.md            repository + docs tree
├── module_dependency.md           dependency graph
├── package_overview.md            module inventory
├── startup_flow.md                boot + Q&A flow
├── community/
│   ├── CHANGELOG.md               changelog
│   ├── CONTRIBUTING.md            contribution guide
│   └── SECURITY.md                security policy
├── decisions/
│   └── DECISIONS.md               architectural decision records
├── design/
│   ├── AppFlow.md                 app screens / states / flows
│   └── Design.md                  design decisions
├── product/
│   └── PRD.md                     product requirements
├── project/
│   ├── analysis_report.md         repo inventory & classification
│   ├── ImplementationPlan.md      implementation plan
│   ├── RiskRegister.md            risks & mitigations
│   ├── Rules.md                   engineering rules
│   └── Tracker.md                 status tracker
├── reference/
│   ├── audit-before-after.md      pre/post-cleanup audit comparison
│   ├── data-sources.md            data source notes
│   ├── deployment-runbook.md      ops runbook
│   ├── Glossary.md                terminology
│   ├── LOOP_LOG.md                iterative verification log
│   └── NEXT_STEPS.md              next steps / manual checks
├── technical/
│   ├── API.md                     endpoint reference
│   ├── Deployment.md              deployment guide
│   ├── Schema.md                  data model
│   ├── SecurityAndCompliance.md   security baseline
│   ├── security-notes.md          security implementation notes
│   ├── TechSpec.md                technical spec
│   └── Testing.md                 test strategy
├── migration/
│   ├── migration_summary.md       modernization record
│   ├── old_tree_to_new_tree.md    restructure before/after
│   └── file_move_ledger.md        file-move ledger
└── audit/
    ├── cleanup-audit-2026-08-13.md  previous cleanup audit
    └── cleanup-audit-2026-08-15.md  docs de-LLM-ification audit
```

## Guidance

| You want... | Read |
|---|---|
| How the app works end-to-end | [architecture.md](architecture.md) |
| Architecture decisions | [decisions/DECISIONS.md](decisions/DECISIONS.md) |
| API surface | [technical/API.md](technical/API.md) |
| Ops runbook | [reference/deployment-runbook.md](reference/deployment-runbook.md) |
| Security notes | [technical/security-notes.md](technical/security-notes.md) |
| Next manual steps | [reference/NEXT_STEPS.md](reference/NEXT_STEPS.md) |
| What's shipped / next | [project/Tracker.md](project/Tracker.md) |
| Risks & follow-ups | [project/RiskRegister.md](project/RiskRegister.md) |
