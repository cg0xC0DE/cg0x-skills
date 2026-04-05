# CLAUDE.md

## Project Overview

Claude Code marketplace plugin providing development workflow and project automation skills by cg0x.

## Architecture

Skills are organized into plugin categories in `marketplace.json`:

```
skills/
└── [dev-tools]                    # Development & automation
    ├── cg0x-init-maker/               # Windows init.bat generator
    ├── cg0x-dev-standards/            # Python web project conventions
    ├── cg0x-subagent-team/            # Multi-agent team management
    ├── cg0x-service-guardian/         # Local service healthcheck generator
    └── cg0x-mq-event/                   # cmd-patrol MQ event publishing guide
```

Each skill contains:
- `SKILL.md` — YAML front matter (name, description) + documentation

## Skill Loading Rules

| Rule | Description |
|------|-------------|
| **Load project skills first** | MUST load all skills from `skills/` directory in current project. Project skills take priority over system/user-level skills with same name. |

**Loading Priority** (highest → lowest):
1. Current project `skills/` directory
2. User-level skills (`$HOME/.cg0x-skills/`)
3. System-level skills

## Adding New Skills

**All skills MUST use `cg0x-` prefix** to avoid conflicts when users import this plugin.

### Key Requirements

| Requirement | Details |
|-------------|---------|
| **name field** | Max 64 chars, lowercase letters/numbers/hyphens only, must start with `cg0x-` |
| **description field** | Max 1024 chars, third person, include what + when to use + trigger keywords |
| **SKILL.md body** | Keep under 500 lines; use `references/` for additional content |

### Steps

1. Create `skills/cg0x-<name>/SKILL.md` with YAML front matter
2. Add optional `scripts/`, `prompts/`, `references/` subdirectories as needed
3. Register in `.claude-plugin/marketplace.json` under the appropriate plugin category
4. Update `README.md` skill listing

### Writing Effective Descriptions

**MUST write in third person**:

```yaml
# Good
description: >
  Generates Windows init.bat scripts for open-source projects.
  Use when user asks for "初始化脚本" or "one-click setup".

# Bad
description: I can help you create init scripts
description: You can use this to generate setup scripts
```

Include both **what** the skill does and **when** to use it (triggers/keywords).
