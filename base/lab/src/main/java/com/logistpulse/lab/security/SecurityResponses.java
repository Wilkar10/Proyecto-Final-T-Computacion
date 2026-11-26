package com.logistpulse.lab.security;

import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import java.util.LinkedHashMap;
import java.util.Map;

/** Respuestas de error de seguridad con el MISMO formato que {@code ApiExceptionMapper}, más un {@code code} estable. */
final class SecurityResponses {

    private SecurityResponses() {
    }

    static Response.ResponseBuilder error(int status, String code, String message) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", status);
        body.put("error", message);
        body.put("code", code);
        return Response.status(status).type(MediaType.APPLICATION_JSON).entity(body);
    }

    /** Solo las rutas /api/** se protegen; salud, métricas y la UI quedan fuera. */
    static boolean isProtectedPath(String relativePath) {
        if (relativePath == null) {
            return false;
        }
        String p = relativePath.startsWith("/") ? relativePath.substring(1) : relativePath;
        return p.equals("api") || p.startsWith("api/");
    }
}
