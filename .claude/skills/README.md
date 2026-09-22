# Skills

Skills are reusable prompts that teach Claude specific patterns for Java development.

## Structure Convention

Each skill folder contains:

| File | Purpose | Audience |
|------|---------|----------|
| `SKILL.md` | Instructions for Claude (frontmatter `name` + `description` decide when it loads) | AI |
| `references/*.md` | Optional detail loaded on demand from `SKILL.md` | AI |

## Available Skills

| Skill | Description |
|-------|-------------|
| [spring-boot](spring-boot/) | Spring Boot 4.x - REST APIs, JPA, Security, Testing, Cloud (with `references/`) |
| [jpa-patterns](jpa-patterns/) | JPA/Hibernate patterns and pitfalls (N+1, lazy loading, transactions, Lombok on entities) |
| [logging-patterns](logging-patterns/) | Structured logging (JSON), SLF4J fluent API, MDC, AI-friendly formats |
| [code-quality](code-quality/) | Java code review - clean code, API contracts, null safety, exceptions, performance |
| [design-patterns](design-patterns/) | Factory, Builder, Strategy, Observer, Decorator, etc. |

## Adding a New Skill

### Before You Start

- [ ] **No significant overlap** - Check the table above for similar skills
- [ ] **Clear type** - Audit (review existing code) or Template (show how to write)
- [ ] **Focused scope** - Can be applied in one session (<15 checklist items)
- [ ] **Current versions** - Examples target Spring Boot 4.x and compile

### Implementation Steps

1. Create folder: `.claude/skills/<skill-name>/`
2. Create `SKILL.md` with frontmatter (`name`, `description`) and instructions for Claude
3. Update this table
4. Update the main README.md tree and changelog

## Usage

Skills are loaded automatically by Claude Code based on their `description`. You can also invoke them directly:

```bash
# Automatic - Claude detects when to use skills
> "Why am I getting LazyInitializationException?"   # Loads jpa-patterns
> "Add JSON logging to this service"                # Loads logging-patterns

# Manual - invoke with slash command
> /spring-boot
> /code-quality
```

## Learn More

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills) - Official guide on creating and using skills
