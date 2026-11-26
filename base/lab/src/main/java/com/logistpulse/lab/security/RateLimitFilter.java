package com.logistpulse.lab.security;

import jakarta.annotation.Priority;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.container.ContainerResponseContext;
import jakarta.ws.rs.container.ContainerResponseFilter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;
import org.springframework.stereotype.Component;

/**
 * Límite de tasa por cliente. Corre ANTES de validar la clave (prioridad 950 < 1000) para que también
 * frene a quien prueba claves al azar; la identidad es el cliente de la clave si es válida, o la IP si no.
 * Respuesta al exceder: 429 + Retry-After + código RATE_LIMITED (igual que el canvas de la API).
 */
@Component
@Priority(950)
public class RateLimitFilter implements ContainerRequestFilter, ContainerResponseFilter {

    private static final Logger LOG = LoggerFactory.getLogger(RateLimitFilter.class);
    private static final String DECISION = "lab.rateLimit";

    private final LabSecurityProperties props;
    private final RateLimiter limiter;
    private final ApiKeyRegistry keys;

    public RateLimitFilter(LabSecurityProperties props, RateLimiter limiter, ApiKeyRegistry keys) {
        this.props = props;
        this.limiter = limiter;
        this.keys = keys;
    }

    @Override
    public void filter(ContainerRequestContext req) {
        if (!props.getRateLimit().isEnabled() || !SecurityResponses.isProtectedPath(req.getUriInfo().getPath())) {
            return;
        }
        String client = keys.authenticate(req.getHeaderString("X-Api-Key"))
                .map(ApiKeyRegistry.Client::name)
                .orElseGet(() -> "anon:" + remoteAddress(req.getHeaderString("X-Forwarded-For")));
        RateLimiter.Decision d = limiter.tryAcquire(client);
        req.setProperty(DECISION, d);
        if (!d.allowed()) {
            LOG.warn("rate limit excedido client={} path={}", client, req.getUriInfo().getPath());
            req.abortWith(SecurityResponses.error(429, "RATE_LIMITED", "Demasiadas solicitudes; espera antes de reintentar")
                    .header("Retry-After", d.retryAfterSeconds())
                    .header("X-RateLimit-Limit", d.limit())
                    .header("X-RateLimit-Remaining", 0)
                    .build());
        }
    }

    @Override
    public void filter(ContainerRequestContext req, ContainerResponseContext res) {
        Object o = req.getProperty(DECISION);
        if (o instanceof RateLimiter.Decision d && d.allowed()) {
            res.getHeaders().putSingle("X-RateLimit-Limit", String.valueOf(d.limit()));
            res.getHeaders().putSingle("X-RateLimit-Remaining", String.valueOf(d.remaining()));
        }
    }

    private String remoteAddress(String forwardedFor) {
        if (props.isTrustForwardedFor()) {
            String first = firstForwarded(forwardedFor);
            if (first != null) {
                return first;
            }
        }
        try {
            if (RequestContextHolder.currentRequestAttributes() instanceof ServletRequestAttributes a) {
                return a.getRequest().getRemoteAddr();
            }
        } catch (IllegalStateException ignored) {
            // sin contexto de petición: cae a una cubeta compartida "unknown" (más estricta, nunca más laxa)
        }
        return "unknown";
    }

    /** Primer elemento de X-Forwarded-For, o null si falta o no parece una IP. */
    static String firstForwarded(String header) {
        if (header == null) {
            return null;
        }
        String first = header.split(",")[0].trim();
        return first.matches("^[0-9a-fA-F:.]{3,45}$") ? first : null;
    }
}
