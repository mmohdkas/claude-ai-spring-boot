# Claude Code Template for Spring Boot Application

This template provides a structured starting point for Spring Boot applications, optimized for Claude AI's code completion capabilities. It includes essential configurations and best practices to streamline development and enhance productivity.

The idea behind this template is that you can just clone this repository and use it to generate the app you want with Claude Code.

> **Fork note:** this is a fork of [piomin/claude-ai-spring-boot](https://github.com/piomin/claude-ai-spring-boot),
> updated for **Spring Boot 4.1** (release 2.0.0) and adapted to use **Lombok** and the `edu.iu.es.ep` group ID / base package.

```shell
.
├── .claude
│   ├── agents
│   │   ├── code-reviewer.md
│   │   ├── devops-engineer.md
│   │   ├── docker-expert.md
│   │   ├── kubernetes-specialist.md
│   │   ├── security-engineer.md
│   │   └── spring-boot-engineer.md
│   ├── settings.local.json
│   └── skills
│       ├── README.md
│       ├── code-quality
│       │   └── SKILL.md
│       ├── design-patterns
│       │   └── SKILL.md
│       ├── jpa-patterns
│       │   └── SKILL.md
│       ├── logging-patterns
│       │   └── SKILL.md
│       └── spring-boot
│           ├── SKILL.md
│           └── references
│               ├── cloud.md
│               ├── data.md
│               ├── security.md
│               ├── testing.md
│               └── web.md
├── .claude-plugin
│   └── plugin.json
├── .github
│   ├── doc-snippets        # CI-only: compiles/tests the skills' java blocks
│   └── workflows
│       └── ci.yml
├── tasks
│   └── lessons.md
├── CLAUDE.md
├── LICENSE
├── README.md
└── pom.xml
```

## CI

The `CI` workflow extracts every java block from `.claude/skills` (see `.github/doc-snippets/extract.py`),
compiles it against Spring Boot 4.1 and runs the test snippets. Run it locally with:

```bash
mvn -B -f .github/doc-snippets/pom.xml verify
```

## Upgrading to a New Spring Boot Minor (e.g. 4.2)

Each Spring Boot minor gets its own release of this template:

1. Branch `feature/spring-boot-4.2-upgrade` from `develop`.
2. Bump the parent in `.github/doc-snippets/pom.xml` to the new version. It is the version CI verifies the docs against.
   Fix whatever `mvn -B -f .github/doc-snippets/pom.xml verify` breaks.
3. Read the Spring Boot release notes / migration guide and update the skills (new APIs, deprecations, property renames).
   Also check the matching Spring Cloud release train in `references/cloud.md`.
4. Update the target-version mentions: `git grep -n "4\.1"`.
5. Pick the version by SemVer: MINOR if the guidance only adds or updates, MAJOR if it removes or replaces patterns.
   Add a changelog entry, then release through `release/x.y.z` → `main` and tag `vx.y.z`.

## Target Stack

Spring Boot 4.1.x (Spring Framework 7, Spring Security 7, Hibernate 7, Jackson 3, JUnit 6), Spring Cloud 2025.1.x, Testcontainers 2.x, Java 25 (17+ minimum), Maven, Lombok.

## Changelog

### 2.0.0
**Breaking changes**
- Group ID / base package changed from `pl.piomin.services` to `edu.iu.es.ep`
- Lombok is now required by the conventions (the upstream "no Lombok" rule is reversed)
- Spring Boot 3.x guidance removed; examples target Spring Boot 4.1 only

**Changes**
- Skills and agents upgraded from Spring Boot 3.x to 4.1:
  - modular starters (`-webmvc`, `-restclient`, per-module test starters)
  - `@MockitoBean` instead of the removed `@MockBean`
  - `RestTestClient`, Testcontainers 2 + `@ServiceConnection`
  - Jackson 3, JSpecify null-safety, Spring Security 7, JJWT 0.12+ API
  - `RestClient` and HTTP interface clients, API versioning, `ProblemDetail` errors
  - Framework 7 `@Retryable`/`@ConcurrencyLimit`, OpenTelemetry tracing, Gateway 5 properties
- Lombok patterns documented with entity-safe rules (`@Getter`/`@Setter`, no `@Data`/`@ToString`/`@EqualsAndHashCode` on entities); records preferred for DTOs, secrets kept out of `toString()`
- Git Flow, Conventional Commits and Semantic Versioning documented in CLAUDE.md
- CI/CD convention switched from CircleCI to GitHub Actions
- GitHub Actions `CI` workflow: checks Markdown structure and compiles/tests the skills' java blocks
  against Spring Boot 4.1 (`.github/doc-snippets`); required on `main` and `develop`
- Restored `jpa-patterns` and `logging-patterns` skills that had been truncated mid-file
- Fixed non-compiling examples (text block, filter signature, effectively-final lambda capture, mixed repository/service code)
- Removed non-functional "context manager" protocol from agents; agent cross-references now point only to agents in this repo

### 1.0.0
- Initial version from upstream.

You can find the detailed explanation and description of the original template in the upstream author's post [Claude Code Template for Spring Boot](https://piotrminkowski.com/2026/03/24/claude-code-template-for-spring-boot/).
