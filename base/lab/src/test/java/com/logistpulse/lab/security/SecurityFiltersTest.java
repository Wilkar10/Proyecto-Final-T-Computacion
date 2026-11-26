package com.logistpulse.lab.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import jakarta.ws.rs.container.ContainerRequestContext;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.UriInfo;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

/** Pruebas unitarias de los filtros con peticiones simuladas (sin levantar Spring). */
class SecurityFiltersTest {

    private static final String SPEC =
            "dispatcher:dispatcher-key-0123456789:read,write;viewer:viewer-key-0123456789ab:read";

    private ContainerRequestContext request(String method, String path, String apiKey) {
        ContainerRequestContext ctx = mock(ContainerRequestContext.class);
        UriInfo uri = mock(UriInfo.class);
        when(uri.getPath()).thenReturn(path);
        when(ctx.getUriInfo()).thenReturn(uri);
        when(ctx.getMethod()).thenReturn(method);
        when(ctx.getHeaderString("X-Api-Key")).thenReturn(apiKey);
        return ctx;
    }

    private LabSecurityProperties props(boolean authEnabled) {
        var p = new LabSecurityProperties();
        p.setEnabled(authEnabled);
        return p;
    }

    private Response aborted(ContainerRequestContext ctx) {
        ArgumentCaptor<Response> c = ArgumentCaptor.forClass(Response.class);
        verify(ctx).abortWith(c.capture());
        return c.getValue();
    }

    @Test
    void sinClaveDevuelve401() {
        var filter = new ApiKeyFilter(props(true), ApiKeyRegistry.parse(SPEC));
        var ctx = request("GET", "api/orders", null);
        filter.filter(ctx);
        Response r = aborted(ctx);
        assertThat(r.getStatus()).isEqualTo(401);
        assertThat(r.getHeaderString("WWW-Authenticate")).startsWith("ApiKey");
    }

    @Test
    void claveSoloLecturaNoPuedeEscribir403() {
        var filter = new ApiKeyFilter(props(true), ApiKeyRegistry.parse(SPEC));
        var ctx = request("POST", "api/trips", "viewer-key-0123456789ab");
        filter.filter(ctx);
        assertThat(aborted(ctx).getStatus()).isEqualTo(403);
    }

    @Test
    void claveConPermisoPasaYQuedaIdentificada() {
        var filter = new ApiKeyFilter(props(true), ApiKeyRegistry.parse(SPEC));
        var ctx = request("POST", "api/trips", "dispatcher-key-0123456789");
        filter.filter(ctx);
        verify(ctx, never()).abortWith(any());
        verify(ctx).setProperty(ApiKeyFilter.CLIENT_PROPERTY, "dispatcher");
    }

    @Test
    void saludMetricasYUiNoExigenClave() {
        var filter = new ApiKeyFilter(props(true), ApiKeyRegistry.parse(SPEC));
        for (String path : new String[] {"actuator/health", "actuator/prometheus", "", "ui/index.html"}) {
            var ctx = request("GET", path, null);
            filter.filter(ctx);
            verify(ctx, never()).abortWith(any());
        }
    }

    @Test
    void conAutenticacionApagadaNoSeExigeNada() {
        var filter = new ApiKeyFilter(props(false), ApiKeyRegistry.empty());
        var ctx = request("DELETE", "api/orders/1", null);
        filter.filter(ctx);
        verify(ctx, never()).abortWith(any());
    }

    @Test
    void excederLaRafagaDevuelve429ConRetryAfter() {
        var clock = new AtomicLong(0);
        var filter = new RateLimitFilter(props(true), new InMemoryRateLimiter(3, 1, clock::get),
                ApiKeyRegistry.parse(SPEC));
        for (int i = 0; i < 3; i++) {
            var ok = request("GET", "api/orders", "dispatcher-key-0123456789");
            filter.filter(ok);
            verify(ok, never()).abortWith(any());
        }
        var ctx = request("GET", "api/orders", "dispatcher-key-0123456789");
        filter.filter(ctx);
        Response r = aborted(ctx);
        assertThat(r.getStatus()).isEqualTo(429);
        assertThat(Integer.parseInt(r.getHeaderString("Retry-After"))).isGreaterThanOrEqualTo(1);
        assertThat(r.getHeaderString("X-RateLimit-Remaining")).isEqualTo("0");
    }

    @Test
    void clientesDistintosNoComparteCubeta() {
        var clock = new AtomicLong(0);
        var filter = new RateLimitFilter(props(true), new InMemoryRateLimiter(1, 1, clock::get),
                ApiKeyRegistry.parse(SPEC));
        var a1 = request("GET", "api/orders", "dispatcher-key-0123456789");
        filter.filter(a1);
        var a2 = request("GET", "api/orders", "dispatcher-key-0123456789");
        filter.filter(a2);
        verify(a2).abortWith(any());
        var v1 = request("GET", "api/orders", "viewer-key-0123456789ab");
        filter.filter(v1);
        verify(v1, never()).abortWith(any());
    }

    @Test
    void rateLimitNoAplicaFueraDeApi() {
        var filter = new RateLimitFilter(props(true), new InMemoryRateLimiter(1, 1), ApiKeyRegistry.empty());
        for (int i = 0; i < 5; i++) {
            var ctx = request("GET", "actuator/prometheus", null);
            filter.filter(ctx);
            verify(ctx, never()).abortWith(any());
        }
    }

    @Test
    void xForwardedForSoloSeAceptaSiPareceIp() {
        assertThat(RateLimitFilter.firstForwarded("203.0.113.9, 10.0.0.1")).isEqualTo("203.0.113.9");
        assertThat(RateLimitFilter.firstForwarded("2001:db8::1")).isEqualTo("2001:db8::1");
        assertThat(RateLimitFilter.firstForwarded("evil\nSet-Cookie: x")).isNull();
        assertThat(RateLimitFilter.firstForwarded(null)).isNull();
    }

    @Test
    void requestIdSeAceptaSiEsSeguroYSeGeneraSiNo() {
        var filter = new RequestIdFilter();
        var ok = request("GET", "api/orders", null);
        when(ok.getHeaderString("X-Request-Id")).thenReturn("req-12345678");
        filter.filter(ok);
        verify(ok).setProperty(RequestIdFilter.PROPERTY, "req-12345678");

        var evil = request("GET", "api/orders", null);
        when(evil.getHeaderString("X-Request-Id")).thenReturn("x\nFAKE-LOG-LINE");
        filter.filter(evil);
        ArgumentCaptor<Object> c = ArgumentCaptor.forClass(Object.class);
        verify(evil).setProperty(org.mockito.ArgumentMatchers.eq(RequestIdFilter.PROPERTY), c.capture());
        assertThat(c.getValue().toString()).matches("[0-9a-f-]{36}");
    }
}
