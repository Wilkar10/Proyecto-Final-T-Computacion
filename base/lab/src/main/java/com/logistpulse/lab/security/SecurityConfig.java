package com.logistpulse.lab.security;

import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.core.StringRedisTemplate;

@Configuration
public class SecurityConfig {

    /** Falla al arrancar si la autenticación está encendida pero no hay ninguna clave: mejor caerse que quedar abierto. */
    @Bean
    ApiKeyRegistry apiKeyRegistry(LabSecurityProperties props) {
        ApiKeyRegistry registry = ApiKeyRegistry.parse(props.getApiKeys());
        if (props.isEnabled() && registry.isEmpty()) {
            throw new IllegalStateException("lab.security.enabled=true pero lab.security.api-keys está vacío");
        }
        return registry;
    }

    @Bean
    RateLimiter rateLimiter(LabSecurityProperties props, ObjectProvider<StringRedisTemplate> redis) {
        LabSecurityProperties.RateLimit rl = props.getRateLimit();
        if ("redis".equalsIgnoreCase(rl.getStore())) {
            return new RedisRateLimiter(redis.getObject(), rl.getBurst(), rl.getRefillPerSecond());
        }
        return new InMemoryRateLimiter(rl.getBurst(), rl.getRefillPerSecond());
    }
}
