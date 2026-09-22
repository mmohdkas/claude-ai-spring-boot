# doc-snippets

CI-only Maven project that keeps the skill docs honest: `extract.py` copies the ```` ```java ```` blocks
from `.claude/skills/**` into `target/generated-docs`, then `mvn verify` compiles them against
Spring Boot 4.1 (the parent version in `pom.xml`) and runs the test snippets (plus `Boot4ClaimsTest`).

- Every java block must be listed in `MANIFEST` (extracted) or `SKIPPED` (with a reason) in `extract.py`;
  an unlisted or renamed block fails the build.
- `src/` holds only the stubs the snippets reference but do not show, and the two Boot apps.
- Not part of the template: generated applications never depend on it.

Run locally (Java 25, Maven, Python 3; Docker optional for the Testcontainers test):

```bash
mvn -B -f .github/doc-snippets/pom.xml verify
```
