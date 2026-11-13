package com.erdemgural.newssearch;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class ModularityTests {

    private final ApplicationModules modules = ApplicationModules.of(NewsSearchApplication.class);

    @Test
    @DisplayName("modüller birbirinin iç paketlerine erişmez ve döngüsel bağımlılık kurmaz")
    void modulesRespectBoundaries() {
        modules.verify();
    }

    @Test
    @DisplayName("mimarideki altı iş modülü ve ortak web paketi tanınır")
    void allModulesAreDetected() {
        assertThat(modules.stream().map(module -> module.getIdentifier().toString()))
                .containsExactlyInAnyOrder("identity", "ingestion", "search", "library", "admin", "audit", "web");
    }
}
