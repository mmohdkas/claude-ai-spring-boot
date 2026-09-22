---
name: logging-patterns
description: Java logging best practices with SLF4J, structured logging (JSON), and MDC for request tracing. Includes AI-friendly log formats for Claude Code debugging. Use when user asks about logging, debugging application flow, or analyzing logs.
---

# Logging Patterns Skill

Effective logging for Java applications with focus on structured, AI-parsable formats.

## When to Use
- User says "add logging" / "improve logs" / "debug this"
- Analyzing application flow from logs
- Setting up structured logging (JSON)
- Request tracing with correlation IDs
- AI/Claude Code needs to analyze application behavior

---

## AI-Friendly Logging

> **Key insight:** JSON logs are better for AI analysis - faster parsing, fewer tokens, direct field access.

### Why JSON for AI/Claude Code?

```
# Text format - AI must "interpret" the string
2026-01-29 10:15:30 INFO OrderService - Order 12345 created for user-789, total: 99.99

# JSON format - AI extracts fields directly
{"timestamp":"2026-01-29T10:15:30Z","level":"INFO","orderId":12345,"userId":"user-789","total":99.99}
```

| Aspect | Text | JSON |
|--------|------|------|
| Parsing | Regex/interpretation | Direct field access |
| Token usage | Higher (repeated patterns) | Lower (structured) |
| Error extraction | Parse stack trace text | `exception` field |
| Filtering | grep patterns | `jq` queries |

### Recommended Setup for AI-Assisted Development

```yaml
# application.yml - JSON by default
logging:
  structured:
    format:
      console: logstash  # built into Spring Boot (3.4+)

# When YOU need to read logs manually:
# Option 1: Use jq
# tail -f app.log | jq .

# Option 2: Switch profile temporarily
# java -jar app.jar --spring.profiles.active=human-logs
```

### Log Format Optimized for AI Analysis

```json
{
  "timestamp": "2026-01-29T10:15:30.123Z",
  "level": "INFO",
  "logger": "edu.iu.es.ep.OrderService",
  "message": "Order created",
  "requestId": "req-abc123",
  "traceId": "trace-xyz",
  "orderId": 12345,
  "userId": "user-789",
  "duration_ms": 45,
  "step": "payment_completed"
}
```

**Key fields for AI debugging:**
- `requestId` - group all logs from same request
- `step` - track progress through flow
- `duration_ms` - identify slow operations
- `level` - quick filter for errors

### Reading Logs with AI/Claude Code

When asking AI to analyze logs:

```bash
# Get recent errors
cat app.log | jq 'select(.level == "ERROR")' | tail -20

# Follow specific request
cat app.log | jq 'select(.requestId == "req-abc123")'

# Find slow operations
cat app.log | jq 'select(.duration_ms > 1000)'
```

AI can then:
1. Parse JSON directly (no guessing)
2. Follow request flow via requestId
3. Identify exactly where errors occurred
4. Measure timing between steps

---

## Quick Setup (Spring Boot 4)

### Native Structured Logging

Spring Boot has built-in structured logging (since 3.4) - no extra dependencies, no `logback-spring.xml`.

```yaml
# application.yml
logging:
  structured:
    format:
      console: logstash    # or "ecs" for Elastic Common Schema

# Supported formats: logstash, ecs, gelf
```

### Profile-Based Switching

```yaml
# application.yml (default - JSON for AI/prod)
spring:
  profiles:
    default: json-logs

---
spring:
  config:
    activate:
      on-profile: json-logs
logging:
  structured:
    format:
      console: logstash

---
spring:
  config:
    activate:
      on-profile: human-logs
# No structured format = human-readable default
logging:
  pattern:
    console: "%d{HH:mm:ss.SSS} %-5level [%thread] %logger{36} - %msg%n"
```

**Usage:**
```bash
# Default: JSON (for AI, CI/CD, production)
./mvnw spring-boot:run

# Human-readable when needed
./mvnw spring-boot:run -Dspring.profiles.active=human-logs
```

---

## Adding Structured Fields

Use the SLF4J 2 fluent API - Boot's `logstash`/`ecs`/`gelf` formats emit each key-value pair as its own JSON field:

```java
log.atInfo()
    .addKeyValue("orderId", order.getId())
    .addKeyValue("userId", user.getId())
    .addKeyValue("total", order.getTotal())
    .addKeyValue("step", "order_created")
    .log("Order created");

// Output:
// {"message":"Order created","orderId":123,"userId":"u-456","total":99.99,"step":"order_created", ...}
```

> Legacy projects on `logstash-logback-encoder` use `StructuredArguments.kv(...)` instead.
> Don't add that library to new Spring Boot 4 projects.

---

## SLF4J Basics

### Logger Declaration

```java
// ✅ Preferred: Lombok
@Slf4j
@Service
public class OrderService {
    // `log` field is generated
}

// Without Lombok
@Service
public class OrderService {
    private static final Logger log = LoggerFactory.getLogger(OrderService.class);
}
```

### Parameterized Logging

```java
// ✅ GOOD: Evaluated only if level enabled
log.debug("Processing order {} for user {}", orderId, userId);

// ❌ BAD: Always concatenates
log.debug("Processing order " + orderId + " for user " + userId);

// ✅ For expensive operations - supplier is only called if DEBUG is enabled
log.atDebug().setMessage("Full order details: {}").addArgument(order::toJson).log();
```

---

## Log Levels

| Level | When | Example |
|-------|------|---------|
| **ERROR** | Failures needing attention | Unhandled exception, service down |
| **WARN** | Unexpected but handled | Retry succeeded, deprecated API used |
| **INFO** | Business events | Order created, payment processed |
| **DEBUG** | Technical details | Method params, SQL queries |
| **TRACE** | Very detailed | Loop iterations (rarely used) |

---

## MDC (Mapped Diagnostic Context)

MDC adds context to every log entry in a request - essential for tracing.

With Micrometer Tracing (`spring-boot-starter-opentelemetry`), `traceId` and `spanId` are put in the
MDC automatically and appear in structured logs - prefer them over a hand-made request ID.
Use a filter only for extra context or when tracing is not on the classpath:

### Request ID Filter

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestContextFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        try {
            String requestId = Optional.ofNullable(request.getHeader("X-Request-ID"))
                .filter(s -> !s.isBlank())
                .orElseGet(() -> UUID.randomUUID().toString());

            MDC.put("requestId", requestId);
            response.setHeader("X-Request-ID", requestId);

            chain.doFilter(request, response);
        } finally {
            MDC.remove("requestId");
        }
    }
}
```

### MDC in Async Operations

MDC does not propagate to other threads by itself. For `@Async` and Boot-managed executors,
register a context-propagating decorator (Boot applies a `TaskDecorator` bean automatically):

```java
@Bean
public TaskDecorator contextPropagatingTaskDecorator() {
    return new ContextPropagatingTaskDecorator();   // copies MDC + tracing context (Micrometer context-propagation)
}
```

For hand-made threads, copy the map yourself:

```java
Map<String, String> context = MDC.getCopyOfContextMap();
CompletableFuture.runAsync(() -> {
    try {
        if (context != null) MDC.setContextMap(context);
        log.info("Async task running");  // Has requestId, traceId
    } finally {
        MDC.clear();
    }
});
```

---

## What to Log

### Business Events (INFO) and Flow Steps

```java
public Order processOrder(CreateOrderRequest request) {
    Order order = createOrder(request);
    log.atInfo().addKeyValue("step", "order_created").addKeyValue("orderId", order.getId())
        .log("Order created");

    processPayment(order);
    log.atInfo().addKeyValue("step", "payment_done").addKeyValue("orderId", order.getId())
        .addKeyValue("amount", order.getTotal()).log("Payment processed");
    return order;
}
```

### External Calls (with timing)

```java
long start = System.nanoTime();
try {
    Result result = externalService.call(params);
    log.atInfo().addKeyValue("service", "PaymentGateway")
        .addKeyValue("duration_ms", (System.nanoTime() - start) / 1_000_000)
        .log("External call succeeded");
    return result;
} catch (Exception e) {
    log.atError().setCause(e).addKeyValue("service", "PaymentGateway")
        .addKeyValue("duration_ms", (System.nanoTime() - start) / 1_000_000)
        .log("External call failed");
    throw e;
}
```

---

## What NOT to Log

- ❌ Passwords, tokens (JWT, API keys), full card numbers, SSNs and other PII
- ✅ Log identifiers instead: `userId`, `cardLast4`, token `subject`/`exp`

---

## Exception Logging

### Log Once at the Boundary

```java
// ❌ BAD: catch-log-rethrow at every layer - the same stack trace appears N times
catch (Exception e) { log.error("Error", e); throw e; }

// ✅ GOOD: let it propagate; log once in the global handler (see spring-boot references/web.md)
@ExceptionHandler(Exception.class)
public ProblemDetail handle(Exception e, HttpServletRequest request) {
    log.atError().setCause(e)
        .addKeyValue("path", request.getRequestURI())
        .addKeyValue("method", request.getMethod())
        .log("Request failed");
    return ProblemDetail.forStatus(HttpStatus.INTERNAL_SERVER_ERROR);
}
```

### Include Context

```java
// ❌ Useless
log.error("Error occurred", e);

// ✅ Useful for debugging
log.atError().setCause(e)
    .addKeyValue("orderId", orderId)
    .addKeyValue("step", "payment")
    .addKeyValue("attempt", attempt)
    .log("Order processing failed");
```

---

## Quick Reference

```java
@Slf4j                                                // logger
log.info("Order {} created", id);                     // parameterized
log.atInfo().addKeyValue("orderId", id).log("Order created");   // structured field
log.atError().setCause(e).log("Failed");              // exception
MDC.put("requestId", requestId); ... MDC.remove("requestId");  // request context
```

```yaml
logging.structured.format.console: logstash   # or ecs, gelf
```

---

## Related Skills

- `spring-boot` - configuration, tracing (`references/cloud.md`)
- `jpa-patterns` - SQL logging
