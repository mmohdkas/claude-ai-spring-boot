### 1. Plan Mode Default
- Enter plan mode for ANY not-trivial task (3+ steps or architectural decisions)
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until the mistake rate drops
- Review lessons at session start for a project

### 3. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 4. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes. Don't overengineer
- Challenge your own work before presenting it

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards

## Project General Instructions

- Always use the latest versions of dependencies.
- Always write Java code as the Spring Boot application.
- Always use Maven for dependency management.
- Always create test cases for the generated code both positive and negative.
- Always generate the CircleCI pipeline in the .circleci directory to verify the code.
- Minimize the amount of code generated.
- The Maven artifact name must be the same as the parent directory name.
- Use Semantic Versioning for the Maven project: bump MAJOR for breaking changes, MINOR for new backward-compatible features, PATCH for backward-compatible fixes.
- Use Git Flow branches (`feature/*`, `release/*`, `hotfix/*` from `develop`/`main`) and Conventional Commits (`type(scope): subject`) for commit messages and PR titles.
- Use `edu.iu.es.ep` as the group ID for the Maven project and base Java package.
- Use Lombok to reduce boilerplate. On JPA entities use `@Getter`/`@Setter` (+ `@NoArgsConstructor`, and `@Builder` with `@AllArgsConstructor` when needed). Never use `@Data`, `@ToString` or `@EqualsAndHashCode` on entities.
- For DTOs prefer Java records; use Lombok `@Value`/`@Data` only for classes that can't be records. Never include secrets (passwords, tokens) in `toString()`: override it on records, or use `@ToString.Exclude`.
- Generate the Docker Compose file to run all components used by the application.
- Update README.md each time you generate a new version.
