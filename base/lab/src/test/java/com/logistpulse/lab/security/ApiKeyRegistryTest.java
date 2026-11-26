package com.logistpulse.lab.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

class ApiKeyRegistryTest {

    private static final String SPEC =
            "dispatcher:dispatcher-key-0123456789:read,write;viewer:viewer-key-0123456789ab:read";

    @Test
    void autenticaClavesValidasYDevuelveSusScopes() {
        var reg = ApiKeyRegistry.parse(SPEC);
        assertThat(reg.size()).isEqualTo(2);
        var d = reg.authenticate("dispatcher-key-0123456789").orElseThrow();
        assertThat(d.name()).isEqualTo("dispatcher");
        assertThat(d.can("read")).isTrue();
        assertThat(d.can("write")).isTrue();
        var v = reg.authenticate("viewer-key-0123456789ab").orElseThrow();
        assertThat(v.can("read")).isTrue();
        assertThat(v.can("write")).isFalse();
    }

    @Test
    void clavesAusentesOIncorrectasNoAutentican() {
        var reg = ApiKeyRegistry.parse(SPEC);
        assertThat(reg.authenticate(null)).isEmpty();
        assertThat(reg.authenticate("  ")).isEmpty();
        assertThat(reg.authenticate("dispatcher-key-0123456780")).isEmpty();
    }

    @Test
    void scopeSegunMetodoHttp() {
        assertThat(ApiKeyRegistry.scopeFor("GET")).isEqualTo("read");
        assertThat(ApiKeyRegistry.scopeFor("head")).isEqualTo("read");
        assertThat(ApiKeyRegistry.scopeFor("POST")).isEqualTo("write");
        assertThat(ApiKeyRegistry.scopeFor("DELETE")).isEqualTo("write");
        assertThat(ApiKeyRegistry.scopeFor(null)).isEqualTo("write");
    }

    @Test
    void rechazaConfiguracionInvalidaSinFiltrarLaClave() {
        assertThatThrownBy(() -> ApiKeyRegistry.parse("solo-nombre"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ApiKeyRegistry.parse("a:corta:read"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageNotContaining("corta");
        assertThatThrownBy(() -> ApiKeyRegistry.parse("a:una-clave-bastante-larga:admin"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ApiKeyRegistry.parse(
                "a:una-clave-bastante-larga:read;a:otra-clave-bastante-larga:read"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ApiKeyRegistry.parse(
                "a:una-clave-bastante-larga:read;b:una-clave-bastante-larga:read"))
                .isInstanceOf(IllegalArgumentException.class).hasMessageNotContaining("una-clave-bastante-larga");
    }

    @Test
    void vacioEsValido() {
        assertThat(ApiKeyRegistry.parse("").isEmpty()).isTrue();
        assertThat(ApiKeyRegistry.parse(null).isEmpty()).isTrue();
        assertThat(ApiKeyRegistry.empty().authenticate("lo-que-sea-1234567890")).isEmpty();
    }
}
