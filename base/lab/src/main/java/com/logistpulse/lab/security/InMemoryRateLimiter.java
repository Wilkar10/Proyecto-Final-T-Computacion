package com.logistpulse.lab.security;

import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;

/**
 * Token bucket en memoria: una cubeta por cliente. Sirve para el modo lite (una sola instancia)
 * y como respaldo cuando Redis no responde. Con varias instancias del lab hay que usar
 * {@link RedisRateLimiter}: la cubeta debe ser compartida o cada réplica dejaría pasar su propia ráfaga.
 */
public class InMemoryRateLimiter implements RateLimiter {

    private static final int MAX_BUCKETS = 10_000;

    private final int burst;
    private final double refillPerSecond;
    private final LongSupplier nanoClock;
    private final ConcurrentHashMap<String, Bucket> buckets = new ConcurrentHashMap<>();

    public InMemoryRateLimiter(int burst, double refillPerSecond) {
        this(burst, refillPerSecond, System::nanoTime);
    }

    /** El reloj se inyecta para que las pruebas no dependan del tiempo real. */
    public InMemoryRateLimiter(int burst, double refillPerSecond, LongSupplier nanoClock) {
        if (burst < 1) {
            throw new IllegalArgumentException("burst debe ser >= 1");
        }
        if (!(refillPerSecond > 0)) {
            throw new IllegalArgumentException("refillPerSecond debe ser > 0");
        }
        this.burst = burst;
        this.refillPerSecond = refillPerSecond;
        this.nanoClock = nanoClock;
    }

    @Override
    public Decision tryAcquire(String clientId) {
        long now = nanoClock.getAsLong();
        if (buckets.size() > MAX_BUCKETS) {
            evictIdle(now);
        }
        Bucket b = buckets.computeIfAbsent(clientId, k -> new Bucket(burst, now));
        synchronized (b) {
            double elapsedSeconds = (now - b.lastNanos) / 1e9;
            b.tokens = Math.min(burst, b.tokens + Math.max(0, elapsedSeconds) * refillPerSecond);
            b.lastNanos = now;
            if (b.tokens >= 1.0) {
                b.tokens -= 1.0;
                return new Decision(true, burst, (int) Math.floor(b.tokens), 0);
            }
            long wait = (long) Math.ceil((1.0 - b.tokens) / refillPerSecond);
            return new Decision(false, burst, 0, Math.max(1, wait));
        }
    }

    /** Evita que un atacante que cambia de identidad llene la memoria: descarta cubetas inactivas. */
    private void evictIdle(long now) {
        long idleNanos = (long) (2.0 * burst / refillPerSecond * 1e9);
        buckets.entrySet().removeIf(e -> now - e.getValue().lastNanos > idleNanos);
    }

    int size() {
        return buckets.size();
    }

    private static final class Bucket {
        double tokens;
        long lastNanos;

        Bucket(double tokens, long lastNanos) {
            this.tokens = tokens;
            this.lastNanos = lastNanos;
        }
    }
}
