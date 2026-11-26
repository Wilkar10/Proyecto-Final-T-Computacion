package com.logistpulse.lab.security;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

/**
 * Claves de API del laboratorio. Formato de la configuración (una cadena):
 * <pre>nombre:clave:scope,scope;nombre2:clave2:scope</pre>
 * Scopes válidos: {@code read} (GET/HEAD/OPTIONS) y {@code write} (POST/PUT/PATCH/DELETE).
 * Una clave desconocida es 401; una clave conocida sin el scope necesario es 403.
 *
 * Las claves se guardan solo como hash SHA-256 y se comparan en tiempo constante contra TODAS las
 * entradas (sin cortar en la primera coincidencia) para no filtrar información por tiempos.
 */
public final class ApiKeyRegistry {

    public static final String READ = "read";
    public static final String WRITE = "write";
    private static final int MIN_KEY_LENGTH = 16;

    public record Client(String name, Set<String> scopes) {
        public boolean can(String scope) {
            return scopes.contains(scope);
        }
    }

    private record Entry(Client client, byte[] digest) {
    }

    private final List<Entry> entries;

    private ApiKeyRegistry(List<Entry> entries) {
        this.entries = entries;
    }

    public static ApiKeyRegistry empty() {
        return new ApiKeyRegistry(List.of());
    }

    /** Los mensajes de error NUNCA incluyen el valor de una clave. */
    public static ApiKeyRegistry parse(String spec) {
        List<Entry> out = new ArrayList<>();
        Set<String> names = new HashSet<>();
        Set<String> digests = new HashSet<>();
        if (spec != null) {
            for (String raw : spec.split("[;\\n]")) {
                String item = raw.trim();
                if (item.isEmpty()) {
                    continue;
                }
                String[] parts = item.split(":", -1);
                if (parts.length != 3) {
                    throw new IllegalArgumentException("Entrada de clave inválida; se espera nombre:clave:scopes");
                }
                String name = parts[0].trim();
                String key = parts[1].trim();
                if (name.isEmpty()) {
                    throw new IllegalArgumentException("Cliente sin nombre en lab.security.api-keys");
                }
                if (key.length() < MIN_KEY_LENGTH) {
                    throw new IllegalArgumentException("La clave del cliente '" + name + "' tiene menos de "
                            + MIN_KEY_LENGTH + " caracteres");
                }
                Set<String> scopes = new HashSet<>();
                for (String s : parts[2].split(",")) {
                    String scope = s.trim();
                    if (!scope.equals(READ) && !scope.equals(WRITE)) {
                        throw new IllegalArgumentException("Scope inválido para '" + name + "': '" + scope + "'");
                    }
                    scopes.add(scope);
                }
                if (!names.add(name)) {
                    throw new IllegalArgumentException("Cliente repetido: " + name);
                }
                byte[] digest = sha256(key);
                if (!digests.add(java.util.HexFormat.of().formatHex(digest))) {
                    throw new IllegalArgumentException("Dos clientes comparten la misma clave: " + name);
                }
                out.add(new Entry(new Client(name, Set.copyOf(scopes)), digest));
            }
        }
        return new ApiKeyRegistry(List.copyOf(out));
    }

    public boolean isEmpty() {
        return entries.isEmpty();
    }

    public int size() {
        return entries.size();
    }

    public Optional<Client> authenticate(String presented) {
        if (presented == null || presented.isBlank()) {
            return Optional.empty();
        }
        byte[] d = sha256(presented.trim());
        Client found = null;
        for (Entry e : entries) {
            if (MessageDigest.isEqual(e.digest(), d)) {
                found = e.client();
            }
        }
        return Optional.ofNullable(found);
    }

    /** Scope que exige un método HTTP. */
    public static String scopeFor(String httpMethod) {
        return switch (httpMethod == null ? "" : httpMethod.toUpperCase()) {
            case "GET", "HEAD", "OPTIONS" -> READ;
            default -> WRITE;
        };
    }

    private static byte[] sha256(String s) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
