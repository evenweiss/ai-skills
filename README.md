# ai-agent-skills

Public source repository for AI agent commands and skills used by `luminae-helper`.

## Layout

```text
commands/<id>/SKILL.md  # command-style entries
skills/<id>/SKILL.md    # directory-style skills
```

Public entries currently live under `commands/`. Internal company skills are intentionally not stored here; they live in a private wrapper repository.

## Use

This repo is consumed at build time by:

- `evenweiss/luminae-helper`
- `私有包装器`

The published npm packages bundle a snapshot of these files, so end users do not need network access at runtime.
