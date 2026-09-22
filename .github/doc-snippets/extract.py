#!/usr/bin/env python3
"""Extract the ```java blocks of the skill docs into compilable sources.

Every java block in the skills must be listed in MANIFEST (extracted) or SKIPPED
(with a reason); an unlisted block fails the build, so new snippets get checked.

Usage: extract.py <output-dir>   (writes <output-dir>/main and <output-dir>/test)
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS = ROOT / ".claude" / "skills"
SB = "spring-boot/SKILL.md"
WEB, DATA, SEC, TEST, CLOUD = (f"spring-boot/references/{n}.md" for n in ("web", "data", "security", "testing", "cloud"))
JPA, LOG = "jpa-patterns/SKILL.md", "logging-patterns/SKILL.md"

COMMON = """
import java.io.IOException;
import java.lang.annotation.*;
import java.math.BigDecimal;
import java.net.URI;
import java.time.*;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;
import lombok.*;
import lombok.extern.slf4j.Slf4j;
"""

MAIN = COMMON + """
import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import jakarta.persistence.*;
import jakarta.persistence.criteria.*;
import jakarta.persistence.Id;
import jakarta.persistence.Version;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import jakarta.validation.Constraint;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import jakarta.validation.Payload;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import javax.crypto.SecretKey;
import org.hibernate.annotations.BatchSize;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.data.repository.query.Param;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.*;
import org.springframework.security.access.annotation.Secured;
import org.springframework.security.access.prepost.PostAuthorize;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.authentication.*;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtDecoders;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.AccessDeniedHandlerImpl;
import org.springframework.security.web.authentication.HttpStatusEntryPoint;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.*;
import org.springframework.transaction.annotation.*;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.cors.*;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.service.annotation.*;
import org.springframework.web.service.registry.ImportHttpServices;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;
import static org.springframework.security.config.http.SessionCreationPolicy.STATELESS;
"""

TESTS = COMMON + """
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;
import org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase;
import org.springframework.boot.jpa.test.autoconfigure.TestEntityManager;
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.data.domain.*;
import org.springframework.http.*;
import org.springframework.http.MediaType;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.client.RestTestClient;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.postgresql.PostgreSQLContainer;
import tools.jackson.databind.json.JsonMapper;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultHandlers.print;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
"""

CLOUD_IMPORTS = COMMON + """
import org.springframework.boot.health.contributor.Health;
import org.springframework.boot.health.contributor.HealthIndicator;
import org.springframework.context.annotation.Configuration;
import org.springframework.resilience.annotation.ConcurrencyLimit;
import org.springframework.resilience.annotation.EnableResilientMethods;
import org.springframework.resilience.annotation.Retryable;
import org.springframework.stereotype.*;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
"""

LOG_IMPORTS = COMMON + """
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
"""

JPA_IMPORTS = COMMON + """
import jakarta.persistence.*;
import jakarta.persistence.Id;
import jakarta.persistence.Version;
import org.hibernate.annotations.NaturalId;
"""

# (doc, heading, block index) -> (source set, package, file name, imports, transforms)
# A transform is (old, new) for a text replacement, or (marker, None) to drop everything from marker on.
# App packages ("skill", "app") are Spring Boot apps and are exercised by the tests;
# "compileonly.*" packages are only compiled (not component-scanned by any test).
MANIFEST = {
    (SB, "### Entity", 0): ("main", "skill", "Product", MAIN, []),
    (SB, "### Repository", 0): ("main", "skill", "ProductRepository", MAIN, []),
    (SB, "### Service", 0): ("main", "skill", "ProductService", MAIN, []),
    (SB, "### REST Controller", 0): ("main", "skill", "ProductController", MAIN, []),
    (SB, "### DTO (Record)", 0): ("main", "skill", "ProductRequest", MAIN, []),
    (SB, "### Global Exception Handler (RFC 9457 Problem Details)", 0): ("main", "skill", "GlobalExceptionHandler", MAIN, []),
    # The skill app has Spring Security on the classpath; the snippet assumes none -> authenticate in the harness
    (SB, "### Test Slice", 0): ("test", "skill", "ProductControllerTest", TESTS, [
        ("@WebMvcTest(ProductController.class)\n", "@WebMvcTest(ProductController.class)\n@WithMockUser // harness\n"),
        ('post("/api/v1/products")', 'post("/api/v1/products").with(org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf())'),
    ]),
    (SB, "## Spring Security JWT", 0): ("main", "compileonly.security", "SkillSecurityConfig", MAIN, []),

    (WEB, "## REST Controller Pattern", 0): ("main", "app", "UserController", MAIN, []),
    (WEB, "## Request DTOs with Validation", 0): ("main", "app", "UserRequests", MAIN, []),
    (WEB, "## Response DTOs", 0): ("main", "app", "UserResponse", MAIN, []),
    (WEB, "## Global Exception Handling (RFC 9457 Problem Details)", 0): ("main", "app", "GlobalExceptionHandler", MAIN, []),
    (WEB, "## Custom Validation", 0): ("main", "app", "UniqueEmailValidation", MAIN, []),
    (WEB, "## RestClient for External APIs", 0): ("main", "app", "ExternalApi", MAIN, []),
    (WEB, "## HTTP Interface Clients (declarative)", 0): ("main", "app", "ExternalDataClient", MAIN, []),
    (WEB, "## CORS Configuration", 0): ("main", "app", "WebConfig", MAIN, []),

    (DATA, "## JPA Entity Pattern", 0): ("main", "app", "User", MAIN, []),
    (DATA, "## Spring Data JPA Repository", 0): ("main", "app", "UserRepository", MAIN, [
        ("edu.iu.es.ep.dto.", "edu.iu.es.ep.app.")]),   # harness keeps all types in one package
    (DATA, "## Repository with Specifications", 0): ("main", "app", "UserSpecifications", MAIN, [
        ("class UserService", "class UserSearchService")]),
    (DATA, "## Transaction Management", 0): ("main", "app", "OrderService", MAIN, []),
    (DATA, "## Auditing Configuration", 0): ("main", "app", "JpaAuditing", MAIN, []),
    (DATA, "## Query Optimization", 0): ("main", "app", "UserQueries", MAIN, [
        ("interface UserRepository", "interface UserQueryRepository")]),

    (SEC, "## Security Configuration", 0): ("main", "app", "SecurityConfig", MAIN, []),
    (SEC, "## JWT Authentication Filter", 0): ("main", "app", "JwtAuthenticationFilter", MAIN, []),
    (SEC, "## JWT Service (JJWT 0.12+)", 0): ("main", "app", "JwtService", MAIN, []),
    (SEC, "## UserDetailsService Implementation", 0): ("main", "app", "CustomUserDetailsService", MAIN, []),
    (SEC, "## Authentication Controller", 0): ("main", "app", "AuthenticationController", MAIN, []),
    (SEC, "## Authentication Service", 0): ("main", "app", "AuthenticationService", MAIN, []),
    (SEC, "## Method Security", 0): ("main", "app", "SecuredUserService", MAIN, [
        ("class UserService", "class SecuredUserService")]),
    (SEC, "## OAuth2 Resource Server (JWT)", 0): ("main", "compileonly.security", "OAuth2ResourceServerConfig", MAIN, []),

    (TEST, "## Unit Testing with JUnit", 0): ("test", "app", "UserServiceTest", TESTS, []),
    (TEST, "## Integration Testing with @SpringBootTest", 0): ("test", "app", "UserIntegrationTest", TESTS, []),
    (TEST, "## Web Layer Testing with MockMvc", 0): ("test", "app", "UserControllerTest", TESTS, []),
    (TEST, "### AssertJ-style alternative: MockMvcTester", 0): ("test", "app", "UserControllerTesterTest", TESTS, []),
    (TEST, "## Data JPA Testing", 0): ("test", "app", "UserRepositoryTest", TESTS, []),
    (TEST, "## Testcontainers for Database", 0): ("test", "app", "UserServiceIntegrationTest", TESTS, [
        ("@Testcontainers\n", "@Testcontainers(disabledWithoutDocker = true) // harness: skipped locally without Docker\n")]),
    (TEST, "## Test Fixtures", 0): ("test", "app", "TestDataFactory", TESTS, []),

    (CLOUD, "## Simple Retry & Concurrency Limits - Spring Framework 7", 0): ("main", "compileonly.cloud", "Resilience", CLOUD_IMPORTS, []),
    (CLOUD, "## Health Checks & Actuator", 0): ("main", "compileonly.cloud", "CustomHealthIndicator", CLOUD_IMPORTS, [
        ("// application.yml", None)]),

    (JPA, "### OneToMany / ManyToOne", 0): ("main", "compileonly.jpa", "AuthorBook", JPA_IMPORTS, []),
    (JPA, "## Lombok on Entities", 0): ("main", "compileonly.jpa", "Order", JPA_IMPORTS, []),

    (LOG, "### Request ID Filter", 0): ("main", "compileonly.logging", "RequestContextFilter", LOG_IMPORTS, []),
}

SKIPPED = {
    (SB, "## Reactive WebFlux Endpoint", 0): "WebFlux; depends on an unshown reactive OrderService",
    (CLOUD, "## Spring Cloud Config Server", 0): "Spring Cloud dependencies; mixes YAML",
    (CLOUD, "## Dynamic Configuration Refresh", 0): "Spring Cloud dependencies",
    (CLOUD, "## Service Discovery - Eureka", 0): "Spring Cloud dependencies; mixes YAML",
    (CLOUD, "## Spring Cloud Gateway", 0): "Spring Cloud dependencies; mixes YAML",
    (CLOUD, "## Circuit Breaker - Resilience4j", 0): "Resilience4j dependencies; mixes YAML",
    (CLOUD, "## Distributed Tracing - Micrometer Tracing + OpenTelemetry", 0): "mixes YAML; depends on unshown methods",
    (CLOUD, "## Load Balancing with Spring Cloud LoadBalancer", 0): "Spring Cloud dependencies",
    (DATA, "## Projections", 0): "fragment: repeats UserRepository and has loose statements",
    (TEST, "## Testing Reactive Endpoints with WebTestClient", 0): "WebFlux; depends on an unshown reactive controller",
    (TEST, "## Testing Configuration", 0): "mixes YAML (harness uses application-test.yml)",
    (WEB, "## API Versioning (Spring Framework 7)", 0): "method bodies elided ({ ... }); mirrored by UserVersionedController",
}
# Short illustrative fragments (method snippets, before/after pairs) are skipped as a group
FRAGMENT_DOCS = {JPA, LOG}

BLOCK = re.compile(r"^```java\n(.*?)^```", re.M | re.S)
HEADING = re.compile(r"^(#{2,4} .*)$", re.M)
TOP_LEVEL_PUBLIC = re.compile(r"^public (?=(?:final |abstract |sealed )*(?:class|interface|record|enum|@interface) )", re.M)


def blocks(doc):
    text = (SKILLS / doc).read_text()
    parts = HEADING.split(text)
    for i in range(1, len(parts), 2):
        for n, code in enumerate(BLOCK.findall(parts[i + 1])):
            yield (doc, parts[i], n), code


def main(out):
    out = pathlib.Path(out)
    docs = [SB, WEB, DATA, SEC, TEST, CLOUD, JPA, LOG]
    seen, errors, extracted, skipped = set(), [], 0, 0
    for doc in docs:
        for key, code in blocks(doc):
            seen.add(key)
            if key in MANIFEST:
                source_set, package, name, imports, transforms = MANIFEST[key]
                for old, new in transforms:
                    if old not in code:
                        errors.append(f"transform {old!r} not found in {key}")
                    code = code.split(old)[0] if new is None else code.replace(old, new)
                code = TOP_LEVEL_PUBLIC.sub("", code)  # several blocks share a file / package-private is enough
                target = out / source_set / "edu/iu/es/ep" / package.replace(".", "/") / f"{name}.java"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f"// GENERATED from {key[0]} {key[1]!r} - do not edit\n"
                                  f"package edu.iu.es.ep.{package};\n{imports}\n{code}")
                extracted += 1
            elif key in SKIPPED or doc in FRAGMENT_DOCS:
                skipped += 1
            else:
                errors.append(f"unclassified java block {key}: add it to MANIFEST or SKIPPED in extract.py")
    for key in list(MANIFEST) + list(SKIPPED):
        if key not in seen:
            errors.append(f"block {key} not found - heading renamed or block removed?")
    print(f"doc-snippets: extracted {extracted} java blocks, skipped {skipped}")
    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1])
