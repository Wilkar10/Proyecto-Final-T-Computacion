package com.logistpulse.lab.security;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Propiedades {@code lab.security.*}. Por defecto (modo lite) la autenticación está APAGADA para que el lab
 * siga siendo fácil de probar; el perfil docker la enciende. El rate limit está encendido en ambos.
 */
@Component
@ConfigurationProperties(prefix = "lab.security")
public class LabSecurityProperties {

    private boolean enabled = false;
    /** Formato: nombre:clave:read,write;otro:clave:read */
    private String apiKeys = "";
    /** Solo true si hay un proxy de confianza delante que reescribe X-Forwarded-For. */
    private boolean trustForwardedFor = false;
    private final RateLimit rateLimit = new RateLimit();

    public static class RateLimit {
        private boolean enabled = true;
        private int burst = 20;
        private double refillPerSecond = 10;
        /** memory | redis */
        private String store = "memory";

        public boolean isEnabled() { return enabled; }
        public void setEnabled(boolean enabled) { this.enabled = enabled; }
        public int getBurst() { return burst; }
        public void setBurst(int burst) { this.burst = burst; }
        public double getRefillPerSecond() { return refillPerSecond; }
        public void setRefillPerSecond(double refillPerSecond) { this.refillPerSecond = refillPerSecond; }
        public String getStore() { return store; }
        public void setStore(String store) { this.store = store; }
    }

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
    public String getApiKeys() { return apiKeys; }
    public void setApiKeys(String apiKeys) { this.apiKeys = apiKeys; }
    public boolean isTrustForwardedFor() { return trustForwardedFor; }
    public void setTrustForwardedFor(boolean trustForwardedFor) { this.trustForwardedFor = trustForwardedFor; }
    public RateLimit getRateLimit() { return rateLimit; }
}
