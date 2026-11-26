package com.logistpulse.lab.security;

import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

/**
 * Token bucket compartido en Redis. La lectura, la recarga y el consumo ocurren dentro de UN script Lua,
 * así que son atómicos aunque haya muchas réplicas del lab. El reloj es el de Redis (comando TIME),
 * no el de cada réplica, para que los relojes desfasados no alteren la recarga.
 *
 * Decisión de diseño (ver docs): si Redis no responde NO se bloquea la API; se degrada al límite en memoria
 * de esta réplica y se registra una advertencia. Prioriza disponibilidad; para una API de pagos se elegiría lo contrario.
 */
public class RedisRateLimiter implements RateLimiter {

    private static final Logger LOG = LoggerFactory.getLogger(RedisRateLimiter.class);
    private static final String PREFIX = "lp:rl:";

    static final String LUA = """
            local cap = tonumber(ARGV[1])
            local rate = tonumber(ARGV[2])
            local t = redis.call('TIME')
            local now = t[1] * 1000 + math.floor(t[2] / 1000)
            local h = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
            local tokens = tonumber(h[1])
            local ts = tonumber(h[2])
            if tokens == nil then
              tokens = cap
              ts = now
            end
            tokens = math.min(cap, tokens + math.max(0, now - ts) * rate / 1000)
            local allowed = 0
            local wait = 0
            if tokens >= 1 then
              tokens = tokens - 1
              allowed = 1
            else
              wait = math.ceil((1 - tokens) / rate)
            end
            redis.call('HSET', KEYS[1], 'tokens', tostring(tokens), 'ts', tostring(now))
            redis.call('PEXPIRE', KEYS[1], math.ceil(cap / rate * 1000) * 2)
            return {allowed, math.floor(tokens), wait}
            """;

    private final StringRedisTemplate redis;
    private final int burst;
    private final double refillPerSecond;
    private final RateLimiter fallback;
    @SuppressWarnings("rawtypes")
    private final DefaultRedisScript<List> script;

    @SuppressWarnings("rawtypes")
    public RedisRateLimiter(StringRedisTemplate redis, int burst, double refillPerSecond) {
        this.redis = redis;
        this.burst = burst;
        this.refillPerSecond = refillPerSecond;
        this.fallback = new InMemoryRateLimiter(burst, refillPerSecond);
        this.script = new DefaultRedisScript<>(LUA, List.class);
    }

    @Override
    @SuppressWarnings("unchecked")
    public Decision tryAcquire(String clientId) {
        try {
            List<Object> r = redis.execute(script, List.of(PREFIX + clientId),
                    String.valueOf(burst), String.valueOf(refillPerSecond));
            if (r == null || r.size() != 3) {
                throw new IllegalStateException("respuesta inesperada de Redis");
            }
            boolean allowed = ((Number) r.get(0)).longValue() == 1L;
            int remaining = ((Number) r.get(1)).intValue();
            long wait = ((Number) r.get(2)).longValue();
            return new Decision(allowed, burst, allowed ? remaining : 0, allowed ? 0 : Math.max(1, wait));
        } catch (RuntimeException e) {
            LOG.warn("Redis no disponible para el rate limit; se usa el límite local de esta réplica: {}", e.toString());
            return fallback.tryAcquire(clientId);
        }
    }
}
