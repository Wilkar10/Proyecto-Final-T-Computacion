package com.logistpulse.lab.repo;

import com.logistpulse.lab.domain.PackingJob;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PackingJobRepository extends JpaRepository<PackingJob, Long> {

    Optional<PackingJob> findByIdempotencyKey(String idempotencyKey);

    Optional<PackingJob> findByOrderCode(String orderCode);
}
