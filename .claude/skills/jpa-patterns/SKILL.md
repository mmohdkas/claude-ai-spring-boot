---
name: jpa-patterns
description: JPA/Hibernate patterns and common pitfalls (N+1, lazy loading, transactions, queries). Use when user has JPA performance issues, LazyInitializationException, or asks about entity relationships and fetching strategies.
---

# JPA Patterns Skill

Best practices and common pitfalls for JPA/Hibernate in Spring applications.

## When to Use
- User mentions "N+1 problem" / "too many queries"
- LazyInitializationException errors
- Questions about fetch strategies (EAGER vs LAZY)
- Transaction management issues
- Entity relationship design
- Query optimization

---

## Quick Reference: Common Problems

| Problem | Symptom | Solution |
|---------|---------|----------|
| N+1 queries | Many SELECT statements | JOIN FETCH, @EntityGraph |
| LazyInitializationException | Error outside transaction | JOIN FETCH, @EntityGraph, DTO projection (not Open Session in View) |
| Slow queries | Performance issues | Pagination, projections, indexes |
| Dirty checking overhead | Slow updates | Read-only transactions, DTOs |
| Lost updates | Concurrent modifications | Optimistic locking (@Version) |

---

## N+1 Problem

> The #1 JPA performance killer

### The Problem

```java
// ❌ BAD: N+1 queries
@Entity
public class Author {
    @Id private Long id;
    private String name;

    @OneToMany(mappedBy = "author", fetch = FetchType.LAZY)
    private List<Book> books;
}

// This innocent code...
List<Author> authors = authorRepository.findAll();  // 1 query
for (Author author : authors) {
    System.out.println(author.getBooks().size());   // N queries!
}
// Result: 1 + N queries (if 100 authors = 101 queries)
```

### Solution 1: JOIN FETCH (JPQL)

```java
// ✅ GOOD: Single query with JOIN FETCH
public interface AuthorRepository extends JpaRepository<Author, Long> {

    @Query("SELECT a FROM Author a JOIN FETCH a.books")
    List<Author> findAllWithBooks();
}

// Usage - single query
List<Author> authors = authorRepository.findAllWithBooks();
```

### Solution 2: @EntityGraph

```java
// ✅ GOOD: EntityGraph for declarative fetching
public interface AuthorRepository extends JpaRepository<Author, Long> {

    @EntityGraph(attributePaths = {"books"})
    List<Author> findAll();

    // Or with named graph
    @EntityGraph(value = "Author.withBooks")
    List<Author> findAllWithBooks();
}

// Define named graph on entity
@Entity
@NamedEntityGraph(
    name = "Author.withBooks",
    attributeNodes = @NamedAttributeNode("books")
)
public class Author {
    // ...
}
```

### Solution 3: Batch Fetching

```java
// ✅ GOOD: Batch fetching (Hibernate-specific)
@Entity
public class Author {

    @OneToMany(mappedBy = "author")
    @BatchSize(size = 25)  // Fetch 25 at a time
    private List<Book> books;
}

// Or globally in application.properties
spring.jpa.properties.hibernate.default_batch_fetch_size=25
```

### Detecting N+1

```yaml
# Enable SQL logging to detect N+1
spring:
  jpa:
    show-sql: true
    properties:
      hibernate:
        format_sql: true

logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE   # bound parameter values (Hibernate 6+)
```

---

## Lazy Loading

### FetchType Basics

```java
@Entity
public class Order {

    // LAZY: Load only when accessed (default for collections)
    @OneToMany(mappedBy = "order", fetch = FetchType.LAZY)
    private List<OrderItem> items;

    // EAGER: Always load immediately (default for @ManyToOne, @OneToOne)
    @ManyToOne(fetch = FetchType.EAGER)  // ⚠️ Usually bad
    private Customer customer;
}
```

### Best Practice: Default to LAZY

```java
// ✅ GOOD: Always use LAZY, fetch when needed
@Entity
public class Order {

    @ManyToOne(fetch = FetchType.LAZY)  // Override EAGER default
    private Customer customer;

    @OneToMany(mappedBy = "order", fetch = FetchType.LAZY)
    private List<OrderItem> items;
}
```

### LazyInitializationException

```java
// ❌ BAD: Accessing lazy field outside transaction
@Service
public class OrderService {

    public Order getOrder(Long id) {
        return orderRepository.findById(id).orElseThrow();
    }
}

// In controller (no transaction)
Order order = orderService.getOrder(1L);
order.getItems().size();  // 💥 LazyInitializationException!
```

### Solutions for LazyInitializationException

**Solution 1: JOIN FETCH in query**
```java
// ✅ Fetch needed associations in query
@Query("SELECT o FROM Order o JOIN FETCH o.items WHERE o.id = :id")
Optional<Order> findByIdWithItems(@Param("id") Long id);
```

**Solution 2: Map to a DTO inside the transaction**
```java
// ✅ Access lazy data within the transaction, return a DTO (never the entity)
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;

    @Transactional(readOnly = true)
    public OrderDto getOrderWithItems(Long id) {
        Order order = orderRepository.findById(id).orElseThrow();
        return OrderDto.from(order, order.getItems().size());
    }
}
```

**Solution 3: DTO Projection (recommended for reads)**
```java
// ✅ BEST: Select only what you need - no entities, no lazy loading
public record OrderSummary(Long id, OrderStatus status, int itemCount) {}

@Query("""
    SELECT new edu.iu.es.ep.dto.OrderSummary(o.id, o.status, SIZE(o.items))
    FROM Order o WHERE o.id = :id
    """)
Optional<OrderSummary> findOrderSummary(@Param("id") Long id);
```

**Anti-pattern: Open Session in View**
```yaml
# ❌ Spring Boot enables OSIV by default (and logs a warning). It hides N+1 problems
# and holds a DB connection for the whole HTTP request. Turn it off:
spring:
  jpa:
    open-in-view: false
```

---

## Transactions

### Propagation

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final OrderRepository orderRepository;
    private final PaymentService paymentService;

    @Transactional
    public void placeOrder(Order order) {
        orderRepository.save(order);
        // REQUIRED (default): joins this transaction - if payment throws, the order rolls back
        paymentService.processPayment(order);
    }
}

@Service
public class PaymentService {

    // REQUIRES_NEW: independent transaction, commits/rolls back on its own
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void processPayment(Order order) { ... }

    // MANDATORY: throws if no transaction is active
    @Transactional(propagation = Propagation.MANDATORY)
    public void updatePaymentStatus(Order order) { ... }
}
```

### Common Transaction Mistakes

```java
// ❌ BAD: self-invocation bypasses the proxy - @Transactional is IGNORED
@Service
public class OrderService {
    public void processOrder(Long id) {
        updateOrder(id);
    }

    @Transactional
    public void updateOrder(Long id) { ... }
}

// ✅ GOOD: move the transactional method to a separate bean
@Service
@RequiredArgsConstructor
public class OrderProcessor {
    private final OrderUpdater orderUpdater;

    public void processOrder(Long id) {
        orderUpdater.updateOrder(id);   // goes through the proxy
    }
}
```

Other mistakes:
- Checked exceptions do **not** roll back by default - use `@Transactional(rollbackFor = Exception.class)` when needed
- `@Transactional` on `private` methods has no effect
- Catching an exception inside the method and swallowing it commits the transaction

---

## Entity Relationships

### OneToMany / ManyToOne

```java
// ✅ GOOD: Bidirectional, parent owns the lifecycle, child side is LAZY
@Entity
@Getter @Setter
@NoArgsConstructor
public class Author {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @OneToMany(mappedBy = "author", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Book> books = new ArrayList<>();

    public void addBook(Book book) {
        books.add(book);
        book.setAuthor(this);
    }

    public void removeBook(Book book) {
        books.remove(book);
        book.setAuthor(null);
    }
}

@Entity
@Getter @Setter
@NoArgsConstructor
public class Book {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "author_id")
    private Author author;
}
```

### ManyToMany

- Use `Set`, not `List` (Hibernate deletes and re-inserts all rows when a `List` bag changes)
- Cascade at most `PERSIST`/`MERGE`, never `REMOVE`/`ALL`
- Keep both sides in sync with `add*/remove*` helpers, like above

### equals() and hashCode() for Entities

```java
// ✅ Business key (@NaturalId) when one exists
@Entity
@Getter @Setter
@NoArgsConstructor
public class Book {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NaturalId
    @Column(unique = true, nullable = false)
    private String isbn;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Book book)) return false;
        return isbn != null && isbn.equals(book.isbn);
    }

    @Override
    public int hashCode() {
        return Objects.hash(isbn);
    }
}

// ✅ Otherwise ID-based: equal only when both are persisted with the same id,
// constant hashCode so the entity stays in the same HashSet bucket before/after persist
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof Author other)) return false;
    return id != null && id.equals(other.getId());
}

@Override
public int hashCode() {
    return getClass().hashCode();
}
```

---

## Lombok on Entities

| Annotation | Entity? | Why |
|---|---|---|
| `@Getter`, `@Setter` | ✅ | Plain accessors |
| `@NoArgsConstructor` | ✅ | Required by JPA |
| `@Builder` + `@AllArgsConstructor` | ✅ when needed | `@Builder` alone removes the no-args constructor |
| `@Builder.Default` | ✅ on initialized fields | Without it the builder sets `addresses = null` |
| `@RequiredArgsConstructor` | ✅ on services | Constructor injection for `final` fields |
| `@Data` | ❌ | Generates `equals`/`hashCode`/`toString` over all fields |
| `@ToString` | ❌ (or `@ToString.Exclude` on every association) | Triggers lazy loading / `LazyInitializationException`, infinite recursion on bidirectional links |
| `@EqualsAndHashCode` | ❌ | Changes when the ID is generated, touches lazy collections - write ID/business-key equality by hand |

```java
@Entity
@Getter @Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Order {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    @ManyToOne(fetch = FetchType.LAZY)
    private Customer customer;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<OrderItem> items = new ArrayList<>();

    @Version
    private Long version;
}
```

---

## Query Optimization

### Pagination

```java
public interface OrderRepository extends JpaRepository<Order, Long> {
    Page<Order> findByStatus(OrderStatus status, Pageable pageable);
}

Pageable pageable = PageRequest.of(0, 20, Sort.by("createdAt").descending());
Page<Order> orders = orderRepository.findByStatus(OrderStatus.PENDING, pageable);
```

⚠️ Never combine `JOIN FETCH` of a collection with `Pageable` - Hibernate paginates in memory
(`HHH90003004` warning). Page the IDs first, then fetch associations for that page.

### Bulk Operations

```java
public interface OrderRepository extends JpaRepository<Order, Long> {

    // clearAutomatically: stale entities in the persistence context are evicted
    @Modifying(clearAutomatically = true)
    @Query("UPDATE Order o SET o.status = :status WHERE o.createdAt < :date")
    int updateOldOrdersStatus(@Param("status") OrderStatus status,
                              @Param("date") LocalDateTime date);
}

@Transactional
public void archiveOldOrders() {
    int updated = orderRepository.updateOldOrdersStatus(
        OrderStatus.ARCHIVED, LocalDateTime.now().minusYears(1));
    log.info("Archived {} orders", updated);
}
```

---

## Optimistic Locking

```java
// @Version on the entity (see Order above). Concurrent update:
// User 1 loads version=1 and saves → version=2
// User 2 loads version=1 and saves → ObjectOptimisticLockingFailureException
```

The exception is thrown at flush/commit - **after** the `@Transactional` method returns - so a
`try/catch` inside that method never sees it. Handle it one level up:

```java
// Map to HTTP 409 globally
@ExceptionHandler(ObjectOptimisticLockingFailureException.class)
public ProblemDetail handleConflict(ObjectOptimisticLockingFailureException ex) {
    return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
        "The resource was modified by another user. Refresh and try again.");
}

// Or retry from a separate bean, so each attempt runs in a new transaction
// (Spring Framework 7 @Retryable, enabled with @EnableResilientMethods)
@Service
@RequiredArgsConstructor
public class OrderUpdateFacade {
    private final OrderService orderService;   // has the @Transactional updateOrder()

    @Retryable(includes = ObjectOptimisticLockingFailureException.class, maxRetries = 3)
    public Order updateOrder(Long id, UpdateOrderRequest request) {
        return orderService.updateOrder(id, request);
    }
}
```

---

## Common Mistakes

1. **`CascadeType.ALL` on `@ManyToOne`** - deleting a `Book` deletes its `Author`. Cascade only parent → child.
2. **Missing indexes** on columns used in `WHERE`/`JOIN` - declare them in the migration (Flyway/Liquibase), `@Table(indexes = ...)` only documents them.
3. **Lazy fields in `toString()`** - including Lombok `@ToString`/`@Data`; triggers extra queries or `LazyInitializationException`.
4. **Returning entities from controllers** - leaks internals and triggers lazy loading during serialization; return DTOs.
5. **`FetchType.EAGER`** anywhere - cannot be overridden per query; use LAZY + fetch plans.

---

## Performance Checklist

When reviewing JPA code, check:

- [ ] No N+1 queries (JOIN FETCH, @EntityGraph or batch fetching)
- [ ] LAZY fetch everywhere (especially @ManyToOne / @OneToOne)
- [ ] `spring.jpa.open-in-view=false`
- [ ] Pagination for large result sets (no collection JOIN FETCH with Pageable)
- [ ] DTO projections for read-only queries
- [ ] Bulk operations for batch updates/deletes
- [ ] @Version on entities with concurrent access
- [ ] Indexes on frequently queried columns
- [ ] No `@Data` / `@ToString` / `@EqualsAndHashCode` on entities
- [ ] `@Transactional(readOnly = true)` for reads

---

## Related Skills

- `spring-boot` - Spring Boot 4 controller/service/data patterns (`references/data.md`)
- `code-quality` - General Java code review checklist
- `logging-patterns` - SQL and application logging
