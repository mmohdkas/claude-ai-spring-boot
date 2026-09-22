package edu.iu.es.ep.app;

import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/** Checks runtime claims the docs make that no doc snippet exercises on its own. */
@Slf4j
@SpringBootTest
@AutoConfigureMockMvc
@ExtendWith(OutputCaptureExtension.class)
class Boot4ClaimsTest {

    @Autowired
    MockMvc mockMvc;

    @Autowired
    ExternalDataClient externalDataClient;

    @Test
    @WithMockUser
    void apiVersionHeaderSelectsHandler() throws Exception {   // web.md "API Versioning"
        mockMvc.perform(get("/api/users/1").header("X-API-Version", "1.0"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.email").value("v1@example.com"));
        mockMvc.perform(get("/api/users/1").header("X-API-Version", "1.1"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.email").value("v2@example.com"));
        mockMvc.perform(get("/api/users/1"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.email").value("v1@example.com"));
    }

    @Test
    void importHttpServicesCreatesClient() {   // web.md "HTTP Interface Clients"
        assertThat(externalDataClient).isNotNull();
    }

    @Test
    void structuredLoggingIncludesFluentKeyValues(CapturedOutput output) {   // logging-patterns "Adding Structured Fields"
        log.atInfo().addKeyValue("orderId", 42).addKeyValue("step", "order_created").log("Order created");
        assertThat(output.getOut())
            .contains("\"message\":\"Order created\"")
            .contains("\"orderId\":42")
            .contains("\"step\":\"order_created\"");
    }

    @Test
    void userCreateRequestToStringHidesPassword() {   // web.md "Request DTOs" / CLAUDE.md DTO rule
        var request = new UserCreateRequest("a@example.com", "Secret123", "alice", 30);
        assertThat(request.toString()).contains("a@example.com", "alice").doesNotContain("Secret123");
    }
}
