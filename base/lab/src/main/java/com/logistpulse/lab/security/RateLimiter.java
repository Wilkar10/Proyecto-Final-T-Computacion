package com.logistpulse.lab.security;

/**
 * Límite de tasa por cliente (algoritmo de cubeta de fichas / token bucket).
 * Interfaz sin dependencias de Jersey ni de Spring, para poder probarla sola.
 */
public interface RateLimiter {

    /** Intenta consumir UNA ficha del cliente. Nunca lanza excepciones por falta de fichas. */
    Decision tryAcquire(String clientId);

    /**
     * @param allowed           true si la petición puede continuar
     * @param limit             capacidad de la cubeta (ráfaga máxima)
     * @param remaining         fichas que quedan después de esta petición
     * @param retryAfterSeconds segundos que debe esperar el cliente (0 si fue permitida; mínimo 1 si fue negada)
     */
    record Decision(boolean allowed, int limit, int remaining, long retryAfterSeconds) {
    }
}
