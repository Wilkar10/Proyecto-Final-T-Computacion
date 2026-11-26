package com.logistpulse.lab.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;

class InMemoryRateLimiterTest {

    private static final long SECOND = 1_000_000_000L;

    @Test
    void permiteExactamenteLaRafagaYLuegoNiega() {
        AtomicLong clock = new AtomicLong(0);
        var limiter = new InMemoryRateLimiter(20, 10, clock::get);
        for (int i = 0; i < 20; i++) {
            assertThat(limiter.tryAcquire("c1").allowed()).as("petición %d", i + 1).isTrue();
        }
        var denied = limiter.tryAcquire("c1");
        assertThat(denied.allowed()).isFalse();
        assertThat(denied.limit()).isEqualTo(20);
        assertThat(denied.remaining()).isZero();
        assertThat(denied.retryAfterSeconds()).isGreaterThanOrEqualTo(1);
    }

    @Test
    void recargaALaTasaConfigurada() {
        AtomicLong clock = new AtomicLong(0);
        var limiter = new InMemoryRateLimiter(20, 10, clock::get);
        for (int i = 0; i < 20; i++) {
            limiter.tryAcquire("c1");
        }
        clock.addAndGet(SECOND / 2);             // 0,5 s => 5 fichas
        int permitidas = 0;
        for (int i = 0; i < 10; i++) {
            if (limiter.tryAcquire("c1").allowed()) {
                permitidas++;
            }
        }
        assertThat(permitidas).isEqualTo(5);
    }

    @Test
    void laRecargaNuncaSuperaLaCapacidad() {
        AtomicLong clock = new AtomicLong(0);
        var limiter = new InMemoryRateLimiter(20, 10, clock::get);
        limiter.tryAcquire("c1");
        clock.addAndGet(3600 * SECOND);          // una hora de inactividad
        int permitidas = 0;
        for (int i = 0; i < 40; i++) {
            if (limiter.tryAcquire("c1").allowed()) {
                permitidas++;
            }
        }
        assertThat(permitidas).isEqualTo(20);
    }

    @Test
    void cadaClienteTieneSuPropiaCubeta() {
        AtomicLong clock = new AtomicLong(0);
        var limiter = new InMemoryRateLimiter(2, 1, clock::get);
        assertThat(limiter.tryAcquire("a").allowed()).isTrue();
        assertThat(limiter.tryAcquire("a").allowed()).isTrue();
        assertThat(limiter.tryAcquire("a").allowed()).isFalse();
        assertThat(limiter.tryAcquire("b").allowed()).isTrue();
    }

    @Test
    void retryAfterReflejaElTiempoHastaLaProximaFicha() {
        AtomicLong clock = new AtomicLong(0);
        var limiter = new InMemoryRateLimiter(1, 0.5, clock::get);   // una ficha cada 2 s
        assertThat(limiter.tryAcquire("a").allowed()).isTrue();
        assertThat(limiter.tryAcquire("a").retryAfterSeconds()).isEqualTo(2);
    }

    @Test
    void rechazaConfiguracionInvalida() {
        assertThatThrownBy(() -> new InMemoryRateLimiter(0, 10)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new InMemoryRateLimiter(5, 0)).isInstanceOf(IllegalArgumentException.class);
    }
}
