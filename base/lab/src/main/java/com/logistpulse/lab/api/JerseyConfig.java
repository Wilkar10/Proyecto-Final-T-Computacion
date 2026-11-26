package com.logistpulse.lab.api;

import com.logistpulse.lab.security.ApiKeyFilter;
import com.logistpulse.lab.security.RateLimitFilter;
import com.logistpulse.lab.security.RequestIdFilter;
import org.glassfish.jersey.server.ResourceConfig;
import org.springframework.stereotype.Component;

@Component
public class JerseyConfig extends ResourceConfig {

    public JerseyConfig() {
        register(OrderResource.class);
        register(RobotResource.class);
        register(RouteResource.class);
        register(TripResource.class);
        register(StockResource.class);
        register(PurchaseOrderResource.class);
        register(PackingResource.class);
        register(UiResource.class);
        register(ApiExceptionMapper.class);
        register(OptimisticLockMapper.class);
        // Capa de API: correlación (900) -> rate limit (950) -> clave y permisos (1000)
        register(RequestIdFilter.class);
        register(RateLimitFilter.class);
        register(ApiKeyFilter.class);
    }
}
