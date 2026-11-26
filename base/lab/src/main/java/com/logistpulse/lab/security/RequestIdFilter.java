package com.logistpulse.lab.security;

import jakarta.annotation.Priority;
import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.container.ContainerRequestFilter;
import jakarta.ws.rs.container.ContainerResponseContext;
import jakarta.ws.rs.container.ContainerResponseFilter;
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;

/**
 * Correlación: acepta el X-Request-Id del cliente (o del gateway) si es seguro; si no, genera uno.
 * Lo deja en el MDC (aparece en cada línea de log) y lo devuelve en la respuesta, también en errores 401/403/429.
 * Se valida el formato para impedir inyección de saltos de línea en los logs.
 */
@Component
@Priority(900)
public class RequestIdFilter implements ContainerRequestFilter, ContainerResponseFilter {

    public static final String HEADER = "X-Request-Id";
    public static final String PROPERTY = "lab.requestId";
    static final String MDC_KEY = "requestId";
    private static final Pattern SAFE = Pattern.compile("^[A-Za-z0-9._-]{8,64}$");

    @Override
    public void filter(ContainerRequestContext req) {
        String incoming = req.getHeaderString(HEADER);
        String id = incoming != null && SAFE.matcher(incoming).matches() ? incoming : UUID.randomUUID().toString();
        req.setProperty(PROPERTY, id);
        MDC.put(MDC_KEY, id);
    }

    @Override
    public void filter(ContainerRequestContext req, ContainerResponseContext res) {
        Object id = req.getProperty(PROPERTY);
        if (id != null) {
            res.getHeaders().putSingle(HEADER, id.toString());
        }
        MDC.remove(MDC_KEY);
    }
}
