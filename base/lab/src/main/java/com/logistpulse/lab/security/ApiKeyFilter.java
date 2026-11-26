package com.logistpulse.lab.security;

import jakarta.annotation.Priority;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * Autenticación por X-Api-Key y autorización por scope (read/write) sobre /api/**.
 * Sin clave o clave desconocida => 401. Clave válida sin el scope del método => 403. Jamás se registra la clave.
 * Esta validación es la defensa en profundidad: aunque alguien llame al lab saltándose el gateway, no entra.
 */
@Component
@Priority(1000)
public class ApiKeyFilter implements ContainerRequestFilter {

    public static final String HEADER = "X-Api-Key";
    public static final String CLIENT_PROPERTY = "lab.client";
    private static final Logger LOG = LoggerFactory.getLogger(ApiKeyFilter.class);

    private final LabSecurityProperties props;
    private final ApiKeyRegistry keys;

    public ApiKeyFilter(LabSecurityProperties props, ApiKeyRegistry keys) {
        this.props = props;
        this.keys = keys;
    }

    @Override
    public void filter(ContainerRequestContext req) {
        if (!props.isEnabled() || !SecurityResponses.isProtectedPath(req.getUriInfo().getPath())) {
            return;
        }
        Optional<ApiKeyRegistry.Client> client = keys.authenticate(req.getHeaderString(HEADER));
        if (client.isEmpty()) {
            LOG.warn("401 sin clave válida path={} method={}", req.getUriInfo().getPath(), req.getMethod());
            req.abortWith(SecurityResponses.error(401, "UNAUTHORIZED", "Falta o es inválida la clave X-Api-Key")
                    .header("WWW-Authenticate", "ApiKey realm=\"logistpulse\"")
                    .build());
            return;
        }
        String scope = ApiKeyRegistry.scopeFor(req.getMethod());
        if (!client.get().can(scope)) {
            LOG.warn("403 client={} sin scope {} path={}", client.get().name(), scope, req.getUriInfo().getPath());
            req.abortWith(SecurityResponses.error(403, "FORBIDDEN", "La clave no tiene el permiso '" + scope + "'").build());
            return;
        }
        req.setProperty(CLIENT_PROPERTY, client.get().name());
    }
}
