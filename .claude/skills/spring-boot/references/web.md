# Web Layer - Controllers & REST APIs

## REST Controller Pattern

```java
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @GetMapping
    public ResponseEntity<Page<UserResponse>> getUsers(
            @PageableDefault(size = 20, sort = "createdAt") Pageable pageable) {
        Page<UserResponse> users = userService.findAll(pageable);
        return ResponseEntity.ok(users);
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
        UserResponse user = userService.findById(id);
        return ResponseEntity.ok(user);
    }

    @PostMapping
    public ResponseEntity<UserResponse> createUser(
            @Valid @RequestBody UserCreateRequest request) {
        UserResponse user = userService.create(request);
        URI location = ServletUriComponentsBuilder
                .fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(user.id())
                .toUri();
        return ResponseEntity.created(location).body(user);
    }

    @PutMapping("/{id}")
    public ResponseEntity<UserResponse> updateUser(
            @PathVariable Long id,
            @Valid @RequestBody UserUpdateRequest request) {
        UserResponse user = userService.update(id, request);
        return ResponseEntity.ok(user);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
    }
}
```

> Serializing `Page` directly produces an unstable JSON shape. Enable
> `@EnableSpringDataWebSupport(pageSerializationMode = VIA_DTO)` or return `PagedModel`.

## API Versioning (Spring Framework 7)

```java
@RestController
@RequestMapping("/api/users")
public class UserVersionedController {

    @GetMapping(path = "/{id}", version = "1.0")
    public UserResponse getUserV1(@PathVariable Long id) { ... }

    @GetMapping(path = "/{id}", version = "1.1+")   // 1.1 and later
    public UserResponseV2 getUserV2(@PathVariable Long id) { ... }
}
```

```yaml
# application.yml - pick one strategy
spring:
  mvc:
    apiversion:
      use:
        header: X-API-Version        # or path-segment / query-parameter / media-type-parameter
      default: "1.0"
      supported: "1.0,1.1"
```

## Request DTOs with Validation

```java
public record UserCreateRequest(
    @NotBlank(message = "Email is required")
    @Email(message = "Email must be valid")
    String email,

    @NotBlank(message = "Password is required")
    @Size(min = 8, max = 100, message = "Password must be 8-100 characters")
    @Pattern(regexp = "^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d).*$",
             message = "Password must contain uppercase, lowercase, and digit")
    String password,

    @NotBlank(message = "Username is required")
    @Size(min = 3, max = 50)
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "Username must be alphanumeric")
    String username,

    @Min(value = 18, message = "Must be at least 18")
    @Max(value = 120, message = "Must be at most 120")
    Integer age
) {
    // Records print every component - keep the password out of logs
    @Override
    public String toString() {
        return "UserCreateRequest[email=%s, username=%s, age=%s]".formatted(email, username, age);
    }
}

public record UserUpdateRequest(
    @Email(message = "Email must be valid")
    String email,

    @Size(min = 3, max = 50)
    String username
) {}
```

## Response DTOs

```java
public record UserResponse(
    Long id,
    String email,
    String username,
    Integer age,
    Boolean active,
    LocalDateTime createdAt,
    LocalDateTime updatedAt
) {
    public static UserResponse from(User user) {
        return new UserResponse(
            user.getId(),
            user.getEmail(),
            user.getUsername(),
            user.getAge(),
            user.getActive(),
            user.getCreatedAt(),
            user.getUpdatedAt()
        );
    }
}
```

## Global Exception Handling (RFC 9457 Problem Details)

Extend `ResponseEntityExceptionHandler`: every built-in Spring MVC exception (validation, 404, 405, 415, ...)
is then rendered as `ProblemDetail`, and you override only what needs extra data.

```java
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = ex.getBindingResult()
            .getFieldErrors()
            .stream()
            .collect(Collectors.toMap(
                FieldError::getField,
                error -> Objects.requireNonNullElse(error.getDefaultMessage(), "Invalid value"),
                (first, second) -> first
            ));

        ProblemDetail problem = ex.getBody();          // 400, pre-filled by Spring
        problem.setDetail("Validation failed");
        problem.setProperty("errors", errors);
        return handleExceptionInternal(ex, problem, headers, status, request);
    }

    @ExceptionHandler(ResourceNotFoundException.class)
    public ProblemDetail handleNotFound(ResourceNotFoundException ex) {
        log.warn("Resource not found: {}", ex.getMessage());
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("Resource not found");
        return problem;
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ProblemDetail handleDataIntegrity(DataIntegrityViolationException ex) {
        log.error("Data integrity violation", ex);
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
            "Data integrity violation - resource may already exist");
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleGlobalException(Exception ex) {
        log.error("Unexpected error", ex);
        return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR,
            "An unexpected error occurred");
    }
}
```

`ProblemDetail` responses use `application/problem+json` and include `type`, `title`, `status`, `detail`, `instance`
plus any custom properties (e.g. `errors`) at the top level.

> Don't combine a plain `@ExceptionHandler(MethodArgumentNotValidException.class)` with
> `spring.mvc.problemdetails.enabled=true`: Boot's built-in handler wins and your `errors` map is lost.
> Extending `ResponseEntityExceptionHandler` (above) makes Boot's handler back off, so the property is not needed.

## Custom Validation

```java
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = UniqueEmailValidator.class)
public @interface UniqueEmail {
    String message() default "Email already exists";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

@Component
@RequiredArgsConstructor
public class UniqueEmailValidator implements ConstraintValidator<UniqueEmail, String> {
    private final UserRepository userRepository;

    @Override
    public boolean isValid(String email, ConstraintValidatorContext context) {
        if (email == null) return true;
        return !userRepository.existsByEmail(email);
    }
}
```

## RestClient for External APIs

Use `RestClient` in servlet (blocking) applications; use `WebClient` only in WebFlux applications.
In Boot 4 the `RestClient.Builder` bean and HTTP interface clients need `spring-boot-starter-restclient`
(`spring-boot-starter-webmvc` alone does not include it).

```java
@Slf4j
@Configuration
public class RestClientConfig {
    @Bean
    public RestClient externalApiClient(RestClient.Builder builder) {
        return builder
            .baseUrl("https://api.example.com")
            .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
            .requestInterceptor((request, body, execution) -> {
                log.info("Request: {} {}", request.getMethod(), request.getURI());
                return execution.execute(request, body);
            })
            .build();
    }
}

@Service
@RequiredArgsConstructor
public class ExternalApiService {
    private final RestClient externalApiClient;

    public ExternalDataResponse fetchData(String id) {
        return externalApiClient.get()
            .uri("/data/{id}", id)
            .retrieve()
            .onStatus(HttpStatusCode::is4xxClientError, (request, response) -> {
                throw new ResourceNotFoundException("External resource not found");
            })
            .onStatus(HttpStatusCode::is5xxServerError, (request, response) -> {
                throw new ServiceUnavailableException("External service unavailable");
            })
            .body(ExternalDataResponse.class);
    }
}
```

## HTTP Interface Clients (declarative)

```java
@HttpExchange("/data")
public interface ExternalDataClient {
    @GetExchange("/{id}")
    ExternalDataResponse get(@PathVariable String id);

    @PostExchange
    ExternalDataResponse create(@RequestBody ExternalDataRequest request);
}

@Configuration
@ImportHttpServices(group = "external", types = ExternalDataClient.class)
public class HttpClientsConfig {
}
```

```yaml
# Base URL and timeouts per group
spring:
  http:
    serviceclient:
      external:
        base-url: https://api.example.com
        read-timeout: 5s
```

Inject `ExternalDataClient` like any other bean. Prefer HTTP interfaces over OpenFeign in new code.

## CORS Configuration

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
            .allowedOrigins("http://localhost:3000", "https://example.com")
            .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
            .allowedHeaders("*")
            .allowCredentials(true)
            .maxAge(3600);
    }
}
```

## Quick Reference

| Annotation | Purpose |
|------------|---------|
| `@RestController` | Marks class as REST controller (combines @Controller + @ResponseBody) |
| `@RequestMapping` | Maps HTTP requests to handler methods |
| `@GetMapping/@PostMapping` | HTTP method-specific mappings (`version` attribute for API versioning) |
| `@PathVariable` | Extracts values from URI path |
| `@RequestParam` | Extracts query parameters |
| `@RequestBody` | Binds request body to method parameter |
| `@Valid` | Triggers validation on request body |
| `@RestControllerAdvice` | Global exception handling for REST controllers |
| `@ResponseStatus` | Sets HTTP status code for method |
| `@HttpExchange` / `@ImportHttpServices` | Declarative HTTP clients |
