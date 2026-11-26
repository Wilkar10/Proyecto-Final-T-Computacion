package com.logistpulse.lab.repo;

import com.logistpulse.lab.domain.Trip;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface TripRepository extends JpaRepository<Trip, Long> {

    Optional<Trip> findByIdempotencyKey(String idempotencyKey);
}
