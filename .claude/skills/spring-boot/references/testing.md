# Testing - Spring Boot Test

## Test Dependencies (Boot 4)

Each module has its own test starter (each brings `spring-boot-starter-test`, i.e. JUnit 6, AssertJ, Mockito):

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc-test</artifactId>   <!-- @WebMvcTest, MockMvc, RestTestClient -->
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa-test</artifactId> <!-- @DataJpaTest -->
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security-test</artifactId> <!-- @WithMockUser -->
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-testcontainers</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-postgresql</artifactId>          <!-- Testcontainers 2.x naming -->
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-junit-jupiter</artifactId>       <!-- @Testcontainers / @Container -->
    <scope>test</scope>
</dependency>
```

Test slice annotations moved to module packages, e.g.
`org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest`,
`org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest`,
`org.springframework.boot.jpa.test.autoconfigure.TestEntityManager`.

## Unit Testing with JUnit

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private PasswordEncoder passwordEncoder;

    @InjectMocks
    private UserService userService;

    @Test
    @DisplayName("Should create user successfully")
    void shouldCreateUser() {
        // Given
        UserCreateRequest request = new UserCreateRequest(
            "test@example.com",
            "Password123",
            "testuser",
            25
        );

        User user = new User();
        user.setId(1L);
        user.setEmail(request.email());
        user.setUsername(request.username());

        when(userRepository.existsByEmail(request.email())).thenReturn(false);
        when(passwordEncoder.encode(request.password())).thenReturn("encodedPassword");
        when(userRepository.save(any(User.class))).thenReturn(user);

        // When
        UserResponse response = userService.create(request);

        // Then
        assertThat(response).isNotNull();
        assertThat(response.email()).isEqualTo(request.email());

        verify(userRepository).existsByEmail(request.email());
        verify(passwordEncoder).encode(request.password());
        verify(userRepository).save(any(User.class));
    }

    @Test
    @DisplayName("Should throw exception when email already exists")
    void shouldThrowExceptionWhenEmailExists() {
        // Given
        UserCreateRequest request = new UserCreateRequest(
            "test@example.com",
            "Password123",
            "testuser",
            25
        );

        when(userRepository.existsByEmail(request.email())).thenReturn(true);

        // When & Then
        assertThatThrownBy(() -> userService.create(request))
            .isInstanceOf(DuplicateResourceException.class)
            .hasMessageContaining("Email already registered");

        verify(userRepository, never()).save(any(User.class));
    }
}
```

## Integration Testing with @SpringBootTest

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureRestTestClient   // required in Boot 4 - @SpringBootTest no longer configures HTTP test clients
@ActiveProfiles("test")
class UserIntegrationTest {

    @Autowired
    private RestTestClient restTestClient;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private RoleRepository roleRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Autowired
    private JwtService jwtService;

    @Autowired
    private UserDetailsService userDetailsService;

    private String adminToken;

    // Real HTTP call through the real security filter chain: authenticate with a real JWT
    // (@WithMockUser does not apply to RANDOM_PORT tests - the server runs on another thread)
    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
        Role admin = roleRepository.findByName("ADMIN")
            .orElseGet(() -> roleRepository.save(Role.builder().name("ADMIN").build()));
        userRepository.save(User.builder()
            .email("admin@example.com")
            .password(passwordEncoder.encode("Admin123"))
            .username("admin")
            .roles(new HashSet<>(Set.of(admin)))
            .build());
        adminToken = jwtService.generateToken(userDetailsService.loadUserByUsername("admin@example.com"));
    }

    @Test
    @DisplayName("Should create user via API")
    void shouldCreateUserViaApi() {
        // Given
        UserCreateRequest request = new UserCreateRequest(
            "test@example.com",
            "Password123",
            "testuser",
            25
        );

        // When & Then
        restTestClient.post()
            .uri("/api/v1/users")
            .headers(h -> h.setBearerAuth(adminToken))
            .contentType(MediaType.APPLICATION_JSON)
            .body(request)
            .exchange()
            .expectStatus().isCreated()
            .expectHeader().exists(HttpHeaders.LOCATION)
            .expectBody(UserResponse.class)
            .value(user -> assertThat(user.email()).isEqualTo(request.email()));
    }

    @Test
    @DisplayName("Should reject request without token")
    void shouldRejectAnonymousRequest() {
        restTestClient.get()
            .uri("/api/v1/users")
            .exchange()
            .expectStatus().isUnauthorized();
    }

    @Test
    @DisplayName("Should return validation error for invalid request")
    void shouldReturnValidationError() {
        // Given
        UserCreateRequest request = new UserCreateRequest(
            "invalid-email",
            "short",
            "u",
            15
        );

        // When & Then - errors come back as RFC 9457 ProblemDetail
        restTestClient.post()
            .uri("/api/v1/users")
            .headers(h -> h.setBearerAuth(adminToken))
            .contentType(MediaType.APPLICATION_JSON)
            .body(request)
            .exchange()
            .expectStatus().isBadRequest()
            .expectBody(ProblemDetail.class)
            .value(problem -> assertThat(problem.getProperties()).containsKey("errors"));
    }
}
```

## Web Layer Testing with MockMvc

```java
@WebMvcTest(UserController.class)
@Import(SecurityConfig.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private UserService userService;

    // @WebMvcTest also picks up Filter beans - mock what JwtAuthenticationFilter needs
    @MockitoBean
    private JwtService jwtService;

    @MockitoBean
    private UserDetailsService userDetailsService;

    @Autowired
    private JsonMapper jsonMapper;   // Jackson 3: tools.jackson.databind.json.JsonMapper

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Should get all users")
    void shouldGetAllUsers() throws Exception {
        // Given
        Page<UserResponse> users = new PageImpl<>(List.of(
            new UserResponse(1L, "user1@example.com", "user1", 25, true, null, null),
            new UserResponse(2L, "user2@example.com", "user2", 30, true, null, null)
        ));

        when(userService.findAll(any(Pageable.class))).thenReturn(users);

        // When & Then
        mockMvc.perform(get("/api/v1/users")
                .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.content").isArray())
            .andExpect(jsonPath("$.content.length()").value(2))
            .andExpect(jsonPath("$.content[0].email").value("user1@example.com"))
            .andDo(print());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Should create user")
    void shouldCreateUser() throws Exception {
        // Given
        UserCreateRequest request = new UserCreateRequest(
            "test@example.com",
            "Password123",
            "testuser",
            25
        );

        UserResponse response = new UserResponse(
            1L,
            request.email(),
            request.username(),
            request.age(),
            true,
            LocalDateTime.now(),
            LocalDateTime.now()
        );

        when(userService.create(any(UserCreateRequest.class))).thenReturn(response);

        // When & Then
        mockMvc.perform(post("/api/v1/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(jsonMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(header().exists("Location"))
            .andExpect(jsonPath("$.email").value(request.email()))
            .andExpect(jsonPath("$.username").value(request.username()))
            .andDo(print());
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("Should return 403 for non-admin user")
    void shouldReturn403ForNonAdmin() throws Exception {
        mockMvc.perform(get("/api/v1/users")
                .contentType(MediaType.APPLICATION_JSON))
            .andExpect(status().isForbidden());
    }
}
```

### AssertJ-style alternative: MockMvcTester

```java
@WebMvcTest(UserController.class)
@Import(SecurityConfig.class)
class UserControllerTesterTest {

    @Autowired
    private MockMvcTester mvc;

    @MockitoBean
    private UserService userService;

    @MockitoBean
    private JwtService jwtService;

    @MockitoBean
    private UserDetailsService userDetailsService;

    @Test
    @WithMockUser(roles = "ADMIN")
    void shouldReturnNotFoundForMissingUser() {
        when(userService.findById(99L)).thenThrow(new ResourceNotFoundException("User not found"));

        assertThat(mvc.get().uri("/api/v1/users/{id}", 99L))
            .hasStatus(HttpStatus.NOT_FOUND)
            .bodyJson().extractingPath("$.detail").isEqualTo("User not found");
    }
}
```

## Data JPA Testing

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@ActiveProfiles("test")
class UserRepositoryTest {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private TestEntityManager entityManager;

    @Test
    @DisplayName("Should find user by email")
    void shouldFindUserByEmail() {
        // Given
        User user = User.builder()
            .email("test@example.com")
            .password("password")
            .username("testuser")
            .active(true)
            .build();

        entityManager.persistAndFlush(user);

        // When
        Optional<User> found = userRepository.findByEmail("test@example.com");

        // Then
        assertThat(found).isPresent();
        assertThat(found.get().getEmail()).isEqualTo("test@example.com");
    }

    @Test
    @DisplayName("Should check if email exists")
    void shouldCheckIfEmailExists() {
        // Given
        User user = User.builder()
            .email("test@example.com")
            .password("password")
            .username("testuser")
            .active(true)
            .build();

        entityManager.persistAndFlush(user);

        // When
        boolean exists = userRepository.existsByEmail("test@example.com");

        // Then
        assertThat(exists).isTrue();
    }

    @Test
    @DisplayName("Should fetch user with roles")
    void shouldFetchUserWithRoles() {
        // Given
        Role adminRole = Role.builder().name("ADMIN").build();
        entityManager.persist(adminRole);

        User user = User.builder()
            .email("admin@example.com")
            .password("password")
            .username("admin")
            .active(true)
            .roles(Set.of(adminRole))
            .build();

        entityManager.persistAndFlush(user);
        entityManager.clear();

        // When
        Optional<User> found = userRepository.findByEmailWithRoles("admin@example.com");

        // Then
        assertThat(found).isPresent();
        assertThat(found.get().getRoles()).hasSize(1);
        assertThat(found.get().getRoles()).extracting(Role::getName).contains("ADMIN");
    }
}
```

## Testcontainers for Database

```java
// Testcontainers 2.x: org.testcontainers.postgresql.PostgreSQLContainer (no generic type)
@SpringBootTest
@Testcontainers
class UserServiceIntegrationTest {

    @Container
    @ServiceConnection   // configures spring.datasource.* automatically - no @DynamicPropertySource
    static PostgreSQLContainer postgres = new PostgreSQLContainer("postgres:17-alpine");

    @Autowired
    private UserService userService;

    @Autowired
    private UserRepository userRepository;

    @BeforeEach
    void setUp() {
        userRepository.deleteAll();
    }

    @Test
    @DisplayName("Should create and find user in real database")
    void shouldCreateAndFindUser() {
        // Given
        UserCreateRequest request = new UserCreateRequest(
            "test@example.com",
            "Password123",
            "testuser",
            25
        );

        // When
        UserResponse created = userService.create(request);
        UserResponse found = userService.findById(created.id());

        // Then
        assertThat(found).isNotNull();
        assertThat(found.email()).isEqualTo(request.email());
    }
}
```

## Testing Reactive Endpoints with WebTestClient

```java
@WebFluxTest(UserReactiveController.class)
class UserReactiveControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockitoBean
    private UserReactiveService userService;

    @Test
    @DisplayName("Should get user reactively")
    void shouldGetUserReactively() {
        // Given
        UserResponse user = new UserResponse(
            1L,
            "test@example.com",
            "testuser",
            25,
            true,
            LocalDateTime.now(),
            LocalDateTime.now()
        );

        when(userService.findById(1L)).thenReturn(Mono.just(user));

        // When & Then
        webTestClient.get()
            .uri("/api/v1/users/{id}", 1L)
            .accept(MediaType.APPLICATION_JSON)
            .exchange()
            .expectStatus().isOk()
            .expectBody(UserResponse.class)
            .value(response -> {
                assertThat(response.id()).isEqualTo(1L);
                assertThat(response.email()).isEqualTo("test@example.com");
            });
    }

    @Test
    @DisplayName("Should create user reactively")
    void shouldCreateUserReactively() {
        // Given
        UserCreateRequest request = new UserCreateRequest(
            "test@example.com",
            "Password123",
            "testuser",
            25
        );

        UserResponse response = new UserResponse(
            1L,
            request.email(),
            request.username(),
            request.age(),
            true,
            LocalDateTime.now(),
            LocalDateTime.now()
        );

        when(userService.create(any(UserCreateRequest.class))).thenReturn(Mono.just(response));

        // When & Then
        webTestClient.post()
            .uri("/api/v1/users")
            .contentType(MediaType.APPLICATION_JSON)
            .body(Mono.just(request), UserCreateRequest.class)
            .exchange()
            .expectStatus().isCreated()
            .expectHeader().exists("Location")
            .expectBody(UserResponse.class)
            .value(user -> {
                assertThat(user.email()).isEqualTo(request.email());
            });
    }
}
```

## Testing Configuration

```java
// application-test.yml
spring:
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: true
    properties:
      hibernate:
        format_sql: true
  security:
    user:
      name: test
      password: test

logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE   # bound parameter values (Hibernate 6+)

// Test Configuration Class
@TestConfiguration
public class TestConfig {

    @Bean
    @Primary
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(4); // Faster for tests
    }

    @Bean
    public Clock fixedClock() {
        return Clock.fixed(
            Instant.parse("2026-01-01T00:00:00Z"),
            ZoneId.of("UTC")
        );
    }
}
```

## Test Fixtures

Uses the Lombok `@Builder` declared on the entities (see `data.md`).

```java
public final class TestDataFactory {

    private TestDataFactory() {}

    public static User createUser(String email, String username) {
        return User.builder()
            .email(email)
            .password("encodedPassword")
            .username(username)
            .active(true)
            .createdAt(LocalDateTime.now())
            .updatedAt(LocalDateTime.now())
            .build();
    }

    public static UserCreateRequest createUserRequest() {
        return new UserCreateRequest(
            "test@example.com",
            "Password123",
            "testuser",
            25
        );
    }
}
```

## Quick Reference

| Annotation | Purpose |
|------------|---------|
| `@SpringBootTest` | Full application context integration test |
| `@WebMvcTest` | Test MVC controllers with mocked services |
| `@WebFluxTest` | Test reactive controllers |
| `@DataJpaTest` | Test JPA repositories (embedded DB, or real DB with `@AutoConfigureTestDatabase(replace = NONE)`) |
| `@MockitoBean` / `@MockitoSpyBean` | Replace / spy a bean in the Spring context (`@MockBean` was removed in Boot 4) |
| `@AutoConfigureRestTestClient` | Inject `RestTestClient` into `@SpringBootTest` |
| `@ServiceConnection` | Wire a Testcontainers container into Spring Boot properties |
| `@WithMockUser` | Mock authenticated user for security tests |
| `@Testcontainers` | Enable Testcontainers support |
| `@ActiveProfiles` | Activate specific Spring profiles for test |

## Testing Best Practices

- Write tests following AAA pattern (Arrange, Act, Assert)
- Use descriptive test names with @DisplayName
- Mock external dependencies, use real DB with Testcontainers
- Achieve 85%+ code coverage
- Test happy path and edge cases
- Use @Transactional for test data cleanup (not with RANDOM_PORT tests - the server runs in another thread)
- Separate unit tests from integration tests
- Use parameterized tests for multiple scenarios
- Test security rules and validation
- Keep tests fast and independent
