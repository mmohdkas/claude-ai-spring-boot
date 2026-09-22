---
name: spring-boot
description: Spring Boot 4.x development - REST APIs, JPA, Security, Testing, and Cloud-native patterns. Use for building enterprise Java applications with Spring Boot.
metadata:
  version: "3.0.0"
  domain: backend
  triggers: Spring Boot, Spring Framework, Spring Security, Spring Data JPA, Spring WebFlux, Java REST API, Microservices Java
  role: specialist
  scope: implementation
  output-format: code
---

# Spring Boot Skill

Enterprise Spring Boot 4.x development with focus on clean architecture and production-ready code.

## Core Workflow

1. **Analyze** - Understand requirements, identify service boundaries, APIs, data models
2. **Design** - Plan architecture, confirm design before coding
3. **Implement** - Build with constructor injection and layered architecture
4. **Secure** - Add Spring Security, OAuth2, method security; verify tests pass
5. **Test** - Write unit, integration tests; run `./mvnw test` and confirm all pass
6. **Deploy** - Configure health checks via Actuator; validate `/actuator/health` returns UP

## Boot 4 Essentials

- **Modular starters** - `spring-boot-starter-webmvc` (was `-web`), `-aspectj` (was `-aop`), `-security-oauth2-resource-server`; each has a matching test starter (`spring-boot-starter-webmvc-test`, `-data-jpa-test`, `-security-test`)
- **Jackson 3** - packages `tools.jackson.*` (annotations stay in `com.fasterxml.jackson.annotation`); inject `JsonMapper`, customize with `JsonMapperBuilderCustomizer`, `@JacksonComponent` replaces `@JsonComponent`
- **Null safety** - JSpecify (`org.jspecify.annotations.Nullable`) replaces `org.springframework.lang` annotations
- **Testing** - `@MockitoBean`/`@MockitoSpyBean` (`@MockBean` is removed); `RestTestClient` + `@AutoConfigureRestTestClient` for HTTP integration tests
- **HTTP clients** - `RestClient` and HTTP interface clients (`@HttpExchange` + `@ImportHttpServices`); `RestTemplate` only for legacy code
- **API versioning** - `@GetMapping(path = "/{id}", version = "1.1")` + `spring.mvc.apiversion.*`
- **Resilience** - `@Retryable` / `@ConcurrencyLimit` from `org.springframework.resilience.annotation` (enable with `@EnableResilientMethods`); Spring Retry is no longer managed
- **Upgrading** - add `spring-boot-properties-migrator` (runtime scope) temporarily to report renamed properties

## Quick Start Templates

### Dependencies
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc</artifactId>
</dependency>
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc-test</artifactId>
    <scope>test</scope>
</dependency>
<!-- Register Lombok in maven-compiler-plugin <annotationProcessorPaths> -->
```

### Entity
```java
@Entity
@Table(name = "products")
@Getter @Setter
@NoArgsConstructor
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    private String name;

    @DecimalMin("0.0")
    private BigDecimal price;
}
```

### Repository
```java
public interface ProductRepository extends JpaRepository<Product, Long> {
    List<Product> findByNameContainingIgnoreCase(String name);
}
```

### Service
```java
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class ProductService {
    private final ProductRepository repo;

    public List<Product> search(String name) {
        return repo.findByNameContainingIgnoreCase(name);
    }

    @Transactional
    public Product create(ProductRequest request) {
        var product = new Product();
        product.setName(request.name());
        product.setPrice(request.price());
        return repo.save(product);
    }
}
```

### REST Controller
```java
@RestController
@RequestMapping("/api/v1/products")
@RequiredArgsConstructor
public class ProductController {
    private final ProductService service;

    @GetMapping
    public List<Product> search(@RequestParam(defaultValue = "") String name) {
        return service.search(name);
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Product create(@Valid @RequestBody ProductRequest request) {
        return service.create(request);
    }
}
```

### DTO (Record)
```java
public record ProductRequest(
    @NotBlank String name,
    @DecimalMin("0.0") BigDecimal price
) {}
```

### Global Exception Handler (RFC 9457 Problem Details)
```java
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        ProblemDetail problem = ex.getBody();
        problem.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
            .collect(Collectors.toMap(FieldError::getField,
                    error -> Objects.requireNonNullElse(error.getDefaultMessage(), "Invalid"),
                    (first, second) -> first)));
        return handleExceptionInternal(ex, problem, headers, status, request);
    }

    @ExceptionHandler(EntityNotFoundException.class)
    public ProblemDetail handleNotFound(EntityNotFoundException ex) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
    }
}
```

### Test Slice
```java
@WebMvcTest(ProductController.class)
class ProductControllerTest {
    @Autowired MockMvc mockMvc;
    @MockitoBean ProductService service;

    @Test
    void createProduct_validRequest_returns201() throws Exception {
        var product = new Product();
        product.setName("Widget");
        when(service.create(any())).thenReturn(product);

        mockMvc.perform(post("/api/v1/products")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"name":"Widget","price":10.0}
                    """))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value("Widget"));
    }

    @Test
    void createProduct_blankName_returns400() throws Exception {
        mockMvc.perform(post("/api/v1/products")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {"name":"","price":10.0}
                    """))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.errors.name").exists());
    }
}
```

## Reference Guide

Load detailed patterns based on context:

| Topic | Reference | When to Load |
|-------|-----------|-------------|
| Web/REST | `references/web.md` | Controllers, validation, Problem Details, HTTP clients, API versioning |
| Data Access | `references/data.md` | JPA, repositories, transactions, queries |
| Security | `references/security.md` | Spring Security 7, OAuth2, JWT, auth |
| Cloud/Config | `references/cloud.md` | Config server, discovery, gateway, resilience, tracing |
| Testing | `references/testing.md` | Unit, integration, slice tests, Testcontainers |

## Constraints

### MUST DO
- Constructor injection (`@RequiredArgsConstructor` + `private final` fields)
- `@Valid` on all request bodies
- `@Transactional` for multi-step writes
- `@Transactional(readOnly = true)` for reads
- Type-safe config with `@ConfigurationProperties`
- Global exception handling with `@RestControllerAdvice` extending `ResponseEntityExceptionHandler` (returns `ProblemDetail`)
- Externalize secrets (use env vars, not properties files)

### MUST NOT DO
- Field injection (`@Autowired` on fields)
- `@Data`, `@ToString`, `@EqualsAndHashCode` on JPA entities
- Skip input validation on endpoints
- Mix blocking and reactive code
- Store secrets in application.properties
- Use deprecated or removed Spring Boot 2.x/3.x patterns (`@MockBean`, `WebSecurityConfigurerAdapter`, `spring-boot-starter-web`, `com.fasterxml.jackson.databind`)
- Hardcode URLs, credentials, environment values

## Architecture Patterns

**Project Structure:**
```
src/main/java/edu/iu/es/ep/
├── controller/     # REST endpoints
├── service/        # Business logic
├── repository/     # Data access
├── model/          # Entities
├── dto/            # Request/Response DTOs
├── config/         # Configuration
└── exception/      # Custom exceptions + handler
```

**Layering:**
- Controller → Service → Repository
- Controller handles HTTP, validation
- Service handles business logic, transactions
- Repository handles data persistence

**Clean Architecture Principles:**
- Domain models independent of frameworks
- Use case driven design
- Dependency inversion (interfaces)
- Clear boundaries between layers

## Common Annotations

| Annotation | Purpose |
|------------|---------|
| `@RestController` | REST controller (combines @Controller + @ResponseBody) |
| `@Service` | Business logic component |
| `@Repository` | Data access component |
| `@Transactional` | Transaction management |
| `@Valid` | Trigger validation |
| `@ConfigurationProperties` | Bind properties to class |
| `@EnableMethodSecurity` | Enable method security |
| `@RequiredArgsConstructor` | Lombok constructor for `final` fields (constructor injection) |

## Reactive WebFlux Endpoint

```java
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {
    private final OrderService orderService;

    @GetMapping("/{id}")
    public Mono<ResponseEntity<OrderDto>> getOrder(@PathVariable UUID id) {
        return orderService.findById(id)
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.notFound().build());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Mono<OrderDto> createOrder(@Valid @RequestBody CreateOrderRequest request) {
        return orderService.create(request);
    }
}
```

## Spring Security JWT

```java
@Configuration
@EnableMethodSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health").permitAll()
                        .anyRequest().authenticated())
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
                .build();
    }
}
```

## Knowledge Base

Spring Boot 4.x, Spring Framework 7, Java 25 (17+ minimum), Spring WebMVC, Spring WebFlux, Project Reactor, Spring Data JPA, Hibernate 7, Spring Security 7, OAuth2/JWT, Jackson 3, R2DBC, Spring Cloud 2025.1, Resilience4j, Micrometer, OpenTelemetry, JUnit 6, Testcontainers 2, Mockito, Lombok, Maven/Gradle
