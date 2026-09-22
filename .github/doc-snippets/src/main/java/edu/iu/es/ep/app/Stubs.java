package edu.iu.es.ep.app;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.*;
import lombok.*;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

// Types the doc snippets reference but do not show. Keep them minimal.

class ResourceNotFoundException extends RuntimeException { ResourceNotFoundException(String m) { super(m); } }
class DuplicateResourceException extends RuntimeException { DuplicateResourceException(String m) { super(m); } }
class InvalidTokenException extends RuntimeException { InvalidTokenException(String m) { super(m); } }
class ServiceUnavailableException extends RuntimeException { ServiceUnavailableException(String m) { super(m); } }
class PaymentException extends RuntimeException { PaymentException(String m) { super(m); } }
class NotificationException extends RuntimeException { NotificationException(String m) { super(m); } }

record ExternalDataResponse(String id, String value) {}
record ExternalDataRequest(String value) {}
record RegisterRequest(String email, String password, String username) {}
record LoginRequest(String email, String password) {}
record RefreshTokenRequest(String refreshToken) {}
record AuthenticationResponse(String accessToken, String refreshToken) {}
record UserSearchCriteria(String email, LocalDateTime createdAfter) {}
record UserSummaryDto(Long id, String username, String email) {}
record UserResponseV2(Long id, String email) {}
record OrderItemRequest(Long productId, int quantity) {}
record OrderCreateRequest(Long customerId, List<OrderItemRequest> items) {}
enum OrderStatus { PENDING, PAID, PAYMENT_FAILED, COMPLETED }

interface PaymentService { void processPayment(Order order); }
interface InventoryService { void reserveStock(Long productId, int quantity); }
interface NotificationService { void sendCompletionEmail(Order order); }
@Service class NoopPaymentService implements PaymentService { public void processPayment(Order order) {} }
@Service class NoopInventoryService implements InventoryService { public void reserveStock(Long productId, int quantity) {} }
@Service class NoopNotificationService implements NotificationService { public void sendCompletionEmail(Order order) {} }

@Entity @Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
class Role {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(unique = true) private String name;
}

@Entity @Getter @Setter @NoArgsConstructor
class Address {
    @Id @GeneratedValue private Long id;
    @ManyToOne(fetch = FetchType.LAZY) private User user;
}

@Entity @Table(name = "orders") @Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
class Order {
    @Id @GeneratedValue private Long id;
    private Long customerId;
    @Enumerated(EnumType.STRING) private OrderStatus status;
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "customer_ref_id") private Customer customer;   // for data.md Customer.orders
    @ElementCollection @Builder.Default private List<Long> productIds = new ArrayList<>();
    void addItem(OrderItemRequest item) { productIds.add(item.productId()); }
}

@Entity @Getter @Setter @NoArgsConstructor
class OrderEvent {
    @Id @GeneratedValue private Long id;
    private Long orderId;
    private String event;
    OrderEvent(Long orderId, String event) { this.orderId = orderId; this.event = event; }
}

interface OrderRepository extends JpaRepository<Order, Long> {}
interface OrderEventRepository extends JpaRepository<OrderEvent, Long> {}
interface RoleRepository extends JpaRepository<Role, Long> { Optional<Role> findByName(String name); }

/** Service used by web.md/testing.md; the docs show its callers, not its body. */
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
class UserService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    Page<UserResponse> findAll(Pageable pageable) { return userRepository.findAll(pageable).map(UserResponse::from); }

    UserResponse findById(Long id) {
        return userRepository.findById(id).map(UserResponse::from)
            .orElseThrow(() -> new ResourceNotFoundException("User not found"));
    }

    @Transactional
    UserResponse create(UserCreateRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new DuplicateResourceException("Email already registered");
        }
        User user = User.builder().email(request.email()).password(passwordEncoder.encode(request.password()))
            .username(request.username()).age(request.age()).build();
        return UserResponse.from(userRepository.save(user));
    }

    @Transactional UserResponse update(Long id, UserUpdateRequest request) { return findById(id); }
    @Transactional void delete(Long id) { userRepository.deleteById(id); }
}

/** Mirrors web.md "API Versioning" (the doc elides the method bodies). */
@RestController
@RequestMapping("/api/users")
class UserVersionedController {
    @GetMapping(path = "/{id}", version = "1.0")
    UserResponse getUserV1(@PathVariable Long id) { return new UserResponse(id, "v1@example.com", "v1", null, true, null, null); }

    @GetMapping(path = "/{id}", version = "1.1+")
    UserResponseV2 getUserV2(@PathVariable Long id) { return new UserResponseV2(id, "v2@example.com"); }
}
