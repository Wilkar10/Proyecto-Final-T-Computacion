package com.logistpulse.lab.repo;

import com.logistpulse.lab.domain.StockMovement;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StockMovementRepository extends JpaRepository<StockMovement, Long> {

    Optional<StockMovement> findByIdempotencyKey(String idempotencyKey);
}
