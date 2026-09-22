# Lessons

## Forked CLAUDE.md rules may not be the user's rules (2026-09-22)
- **Mistake:** Flagged Lombok usage in skill examples as a "violation" because this repo's CLAUDE.md said "Do not use the Lombok library". That rule came from the upstream author (piomin); the user uses Lombok in most projects.
- **Rule:** In a forked template, treat style/tooling rules in CLAUDE.md as possibly inherited. Before reporting something as a violation of such a rule, check `git log` for who wrote it and confirm it reflects the user's preference.

## Verify "latest" claims against the artifacts, not memory (2026-09-22)
- **Mistake risk:** Boot 4 moved classes/properties (e.g. `RestClient` needs `spring-boot-starter-restclient`; OTLP is `management.opentelemetry.tracing.export.otlp.endpoint`).
- **Rule:** Resolve the real dependencies (scratch Maven project) and check class locations with `unzip -l`/`javap` and property names in `META-INF/spring-configuration-metadata.json` before documenting them.

## Follow the team's Git conventions from the first branch (2026-09-22)
- **Mistake:** Created branch `boot4-update`; the team uses Git Flow (`feature/<name>`), Conventional Commits and SemVer.
- **Rule:** Name branches `feature/<kebab-name>` (base: `develop` when it exists), write commits as `type(scope): subject`, and pick the version bump by SemVer impact (breaking → MAJOR), not by habit.

## Check inherited tooling rules too (2026-09-22)
- **Mistake:** Recommended a CircleCI pipeline because the forked CLAUDE.md said so; the team uses GitHub Actions.
- **Rule:** Same as the Lombok lesson — CI/CD, build and tooling rules in a forked CLAUDE.md may be upstream's. Default to GitHub Actions (`.github/workflows/`) here.

## Files must end with a newline (2026-09-22)
- **Mistake:** Edited upstream files (`pom.xml`, `plugin.json`, agents) without noticing they lacked a final newline; the PR diff flagged it.
- **Rule:** Every file ends with `\n`. `.editorconfig` sets `insert_final_newline`, and CI checks all tracked files.

## Renaming a PR's head branch closes the PR (2026-09-22)
- **Mistake:** Told the user GitHub keeps a PR attached when its head branch is renamed. Renaming `feature/spring-boot-4-upgrade` recorded `head_ref_deleted` and auto-closed PR #1; a new PR (#2) had to be opened.
- **Rule:** Pick the final branch name before opening the PR. If a rename is needed later, warn that the PR will close and must be recreated (or keep the old name).
