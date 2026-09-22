# Data Access - Spring Data JPA

## JPA Entity Pattern

```java
@Entity
@Table(name = "users", indexes = {
    @Index(name = "idx_email", columnList = "email", unique = true),
    @Index(name = "idx_username", columnList = "username")
})
@EntityListeners(AuditingEntityListener.class)
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 100)
    private String email;

    @Column(nullable = false, length = 100)
    private String password;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    private Integer age;

    @Column(nullable = false)
    @Builder.Default
    private Boolean active = true;

    private LocalDateTime lastLoginAt;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<Address> addresses = new ArrayList<>();

    @ManyToMany
    @JoinTable(
        name = "user_roles",
        joinColumns = @JoinColumn(name = "user_id"),
        inverseJoinColumns = @JoinColumn(name = "role_id")
    )
    @Builder.Default
    private Set<Role> roles = new HashSet<>();

    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(nullable = false)
    private LocalDateTime updatedAt;

    @Version
    private Long version;

    // Helper methods for bidirectional relationships
    public void addAddress(Address address) {
        addresses.add(address);
        address.setUser(this);
    }

    public void removeAddress(Address address) {
        addresses.remove(address);
        address.setUser(null);
    }

    // ID-based equality: stable across persist/merge, never touches lazy associations
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof User other)) return false;
        return id != null && id.equals(other.getId());
    }

    @Override
    public int hashCode() {
        return getClass().hashCode();
    }
}
```

Lombok rules for entities (same pattern for `Role`, `Address`, `Order`):
- `@Getter @Setter @NoArgsConstructor` always; add `@AllArgsConstructor @Builder` when a builder is needed (tests, factories)
- `@Builder.Default` on initialized fields, otherwise the builder leaves them `null`
- Never `@Data`, `@ToString` or `@EqualsAndHashCode` - they touch lazy associations and recurse on bidirectional links

## Spring Data JPA Repository

```java
@Repository
public interface UserRepository extends JpaRepository<User, Long>,
                                       JpaSpecificationExecutor<User> {

    Optional<User> findByEmail(String email);

    Optional<User> findByUsername(String username);

    boolean existsByEmail(String email);

    boolean existsByUsername(String username);

    @Query("SELECT u FROM User u LEFT JOIN FETCH u.roles WHERE u.email = :email")
    Optional<User> findByEmailWithRoles(@Param("email") String email);

    @Query("SELECT u FROM User u WHERE u.active = true AND u.createdAt >= :since")
    List<User> findActiveUsersSince(@Param("since") LocalDateTime since);

    @Modifying
    @Query("UPDATE User u SET u.active = false WHERE u.lastLoginAt < :threshold")
    int deactivateInactiveUsers(@Param("threshold") LocalDateTime threshold);

    // Projection for read-only DTOs
    @Query("SELECT new edu.iu.es.ep.dto.UserSummaryDto(u.id, u.username, u.email) " +
           "FROM User u WHERE u.active = true")
    List<UserSummaryDto> findAllActiveSummaries();
}
```

## Repository with Specifications

```java
public class UserSpecifications {

    public static Specification<User> hasEmail(String email) {
        return (root, query, cb) ->
            email == null ? null : cb.equal(root.get("email"), email);
    }

    public static Specification<User> isActive() {
        return (root, query, cb) -> cb.isTrue(root.get("active"));
    }

    public static Specification<User> createdAfter(LocalDateTime date) {
        return (root, query, cb) ->
            date == null ? null : cb.greaterThanOrEqualTo(root.get("createdAt"), date);
    }

    public static Specification<User> hasRole(String roleName) {
        return (root, query, cb) -> {
            Join<User, Role> roles = root.join("roles", JoinType.INNER);
            return cb.equal(roles.get("name"), roleName);
        };
    }
}

// Usage in service
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;

    public Page<User> searchUsers(UserSearchCriteria criteria, Pageable pageable) {
        Specification<User> spec = Specification
            .where(UserSpecifications.hasEmail(criteria.email()))
            .and(UserSpecifications.isActive())
            .and(UserSpecifications.createdAfter(criteria.createdAfter()));

        return userRepository.findAll(spec, pageable);
    }
}
```

## Transaction Management

```java
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {
    private final OrderRepository orderRepository;
    private final OrderEventRepository orderEventRepository;
    private final PaymentService paymentService;
    private final InventoryService inventoryService;
    private final NotificationService notificationService;

    @Transactional
    public Order createOrder(OrderCreateRequest request) {
        // All operations in single transaction
        Order order = Order.builder()
            .customerId(request.customerId())
            .status(OrderStatus.PENDING)
            .build();

        request.items().forEach(item -> {
            inventoryService.reserveStock(item.productId(), item.quantity());
            order.addItem(item);
        });

        Order saved = orderRepository.save(order); // `order` stays effectively final for the lambda

        try {
            paymentService.processPayment(saved);
            saved.setStatus(OrderStatus.PAID);   // managed entity - flushed on commit, no second save()
        } catch (PaymentException e) {
            saved.setStatus(OrderStatus.PAYMENT_FAILED);
            throw e; // Transaction will rollback
        }

        return saved;
    }

    // NOTE: propagation only applies when called through the Spring proxy.
    // Calling this from another method of OrderService (self-invocation) runs it
    // in the caller's transaction - move it to a separate bean in real code.
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logOrderEvent(Long orderId, String event) {
        // Separate transaction - will commit even if parent rolls back
        OrderEvent orderEvent = new OrderEvent(orderId, event);
        orderEventRepository.save(orderEvent);
    }

    @Transactional(noRollbackFor = NotificationException.class)
    public void completeOrder(Long orderId) {
        Order order = orderRepository.findById(orderId)
            .orElseThrow(() -> new ResourceNotFoundException("Order not found"));

        order.setStatus(OrderStatus.COMPLETED); // dirty checking persists the change

        // Won't rollback transaction if notification fails
        try {
            notificationService.sendCompletionEmail(order);
        } catch (NotificationException e) {
            log.error("Failed to send notification for order {}", orderId, e);
        }
    }
}
```

## Auditing Configuration

```java
@Configuration
@EnableJpaAuditing
public class JpaAuditingConfig {

    @Bean
    public AuditorAware<String> auditorProvider() {
        return () -> {
            Authentication authentication = SecurityContextHolder
                .getContext()
                .getAuthentication();

            if (authentication == null || !authentication.isAuthenticated()) {
                return Optional.of("system");
            }

            return Optional.of(authentication.getName());
        };
    }
}

@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
@Getter @Setter
public abstract class AuditableEntity {

    @CreatedDate
    @Column(nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @CreatedBy
    @Column(nullable = false, updatable = false, length = 100)
    private String createdBy;

    @LastModifiedDate
    @Column(nullable = false)
    private LocalDateTime updatedAt;

    @LastModifiedBy
    @Column(nullable = false, length = 100)
    private String updatedBy;
}
```

## Projections

```java
// Interface-based projection
public interface UserSummary {
    Long getId();
    String getUsername();
    String getEmail();

    @Value("#{target.username + ' <' + target.email + '>'}")
    String getDisplayName();   // open projection - selects the full entity
}

// Class-based projection (DTO)
public record UserSummaryDto(
    Long id,
    String username,
    String email
) {}

// Usage
public interface UserRepository extends JpaRepository<User, Long> {
    List<UserSummary> findAllBy();

    <T> List<T> findAllBy(Class<T> type);
}

// Service usage
List<UserSummary> summaries = userRepository.findAllBy();
List<UserSummaryDto> dtos = userRepository.findAllBy(UserSummaryDto.class);
```

## Query Optimization

```java
// Repository: fetch associations explicitly instead of relying on lazy loading
public interface UserRepository extends JpaRepository<User, Long> {

    // N+1 solved with JOIN FETCH (DISTINCT is implicit for entity results in Hibernate 6+)
    @Query("""
        SELECT u FROM User u
        LEFT JOIN FETCH u.addresses
        LEFT JOIN FETCH u.roles
        WHERE u.active = true
        """)
    List<User> findAllActiveWithAssociations();

    // EntityGraph for declarative fetching
    @EntityGraph(attributePaths = {"addresses", "roles"})
    List<User> findAllByActiveTrue();

    // Pagination to avoid loading all data (never JOIN FETCH collections with Pageable)
    Page<User> findAllByActiveTrue(Pageable pageable);

    // Native query for complex queries
    @Query(value = """
        SELECT u.* FROM users u
        INNER JOIN orders o ON u.id = o.user_id
        WHERE o.created_at >= :since
        GROUP BY u.id
        HAVING COUNT(o.id) >= :minOrders
        """, nativeQuery = true)
    List<User> findFrequentBuyers(@Param("since") LocalDateTime since,
                                  @Param("minOrders") int minOrders);
}

// Entity: batch fetching loads lazy collections for 25 parents in one query
@Entity
@Getter @Setter
@NoArgsConstructor
public class Customer {
    @Id @GeneratedValue
    private Long id;

    @BatchSize(size = 25)
    @OneToMany(mappedBy = "customer")
    private List<Order> orders = new ArrayList<>();
}
// Or globally: spring.jpa.properties.hibernate.default_batch_fetch_size=25
```

## Database Migrations (Flyway)

```sql
-- V1__create_users_table.sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version BIGINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(active);

-- V2__create_addresses_table.sql
CREATE TABLE addresses (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    street VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_addresses_user_id ON addresses(user_id);
```

## Quick Reference

| Annotation | Purpose |
|------------|---------|
| `@Entity` | Marks class as JPA entity |
| `@Table` | Specifies table details and indexes |
| `@Id` | Marks primary key field |
| `@GeneratedValue` | Auto-generated primary key strategy |
| `@Column` | Column constraints and mapping |
| `@OneToMany/@ManyToOne` | One-to-many/many-to-one relationships |
| `@ManyToMany` | Many-to-many relationships |
| `@JoinColumn/@JoinTable` | Join column/table configuration |
| `@Transactional` | Declares transaction boundaries |
| `@Query` | Custom JPQL/native queries |
| `@Modifying` | Marks query as UPDATE/DELETE |
| `@EntityGraph` | Defines fetch graph for associations |
| `@Version` | Optimistic locking version field |
