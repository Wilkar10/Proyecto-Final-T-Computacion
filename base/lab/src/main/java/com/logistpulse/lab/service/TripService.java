package com.logistpulse.lab.service;

import com.logistpulse.lab.api.ApiException;
import com.logistpulse.lab.domain.Trip;
import com.logistpulse.lab.repo.TripRepository;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import java.util.List;
import java.util.Optional;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.stereotype.Service;

/** Orquesta el despacho de un viaje con idempotencia. NO es transaccional a propósito (ver TripTx). */
@Service
public class TripService {

    /** Resultado: el viaje y si se creó ahora (201) o es una repetición (200). */
    public record Result(Trip trip, boolean created) {
    }

    private final TripTx tx;
    private final TripRepository trips;
    private final Counter tripsCreated;
    private final Counter tripsReplayed;

    public TripService(TripTx tx, TripRepository trips, MeterRegistry registry) {
        this.tx = tx;
        this.trips = trips;
        this.tripsCreated = Counter.builder("logistpulse.trips").description("Viajes multi-parada creados").register(registry);
        this.tripsReplayed = Counter.builder("logistpulse.trips.replayed").description("Repeticiones idempotentes").register(registry);
    }

    public Result dispatch(String key, String robot, List<String> codes) {
        if (key == null || key.isBlank() || key.length() > 64) {
            throw new ApiException(400, "Falta la cabecera Idempotency-Key (1..64 caracteres)");
        }
        Optional<Trip> existing = trips.findByIdempotencyKey(key);
        if (existing.isPresent()) {
            tripsReplayed.increment();
            return new Result(existing.get(), false);
        }
        try {
            Trip t = tx.create(key, robot, codes);
            tripsCreated.increment();
            return new Result(t, true);
        } catch (DataIntegrityViolationException | ObjectOptimisticLockingFailureException race) {
            // Otra petición con la MISMA clave ganó la carrera: devolvemos su resultado, sin efectos nuevos.
            Optional<Trip> winner = trips.findByIdempotencyKey(key);
            if (winner.isPresent()) {
                tripsReplayed.increment();
                return new Result(winner.get(), false);
            }
            throw race;
        }
    }
}
