# Skills

A collection of [Agent Skills](https://agentskills.io/specification) for Claude Code.

## Available Skills

| Skill | Description |
|---|---|
| [ai-engineer](skills/ai-engineer/) | Senior-level AI engineering standards for retrieval, agents, evals, context engineering, and production AI systems |

## Installation

### Claude Code Plugin

```bash
/plugin marketplace add <your-repo-url>
/plugin install ai-engineer@conway-agent-skills
```

### Manual

Copy the skill directory into your project or Claude Code skills path.

## Creating a New Skill

1. Copy the `template/` directory into `skills/` and rename it
2. Edit `SKILL.md` — update the frontmatter (`name`, `description`) and body
3. Add `references/` for detailed docs that should load on-demand
4. Add `scripts/` for executable code if needed
5. Add `LICENSE.txt`
6. Register the skill in `.claude-plugin/marketplace.json`

### Skill Structure

```
my-skill/
├── SKILL.md          # Required: YAML frontmatter + markdown instructions
├── LICENSE.txt       # Recommended
├── references/       # Optional: detailed docs loaded on-demand
├── scripts/          # Optional: executable code
└── assets/           # Optional: templates, images, data
```

### SKILL.md Format

```yaml
---
name: my-skill            # lowercase, hyphens, max 64 chars
description: >            # max 1024 chars
  What it does and when to trigger.
  Include negative triggers.
license: Apache-2.0
---
```

Keep SKILL.md under 500 lines. Split longer content into `references/`.

## Building .skill Archives

```bash
chmod +x scripts/build.sh
./scripts/build.sh              # build all skills
./scripts/build.sh ai-engineer  # build one skill
```

Archives are written to `dist/`.

## License

Apache 2.0 — see individual skill directories for per-skill licensing.
