package com.logistpulse.lab.repo;

import com.logistpulse.lab.domain.PurchaseOrder;
import com.logistpulse.lab.domain.PurchaseStatus;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PurchaseOrderRepository extends JpaRepository<PurchaseOrder, Long> {

    Optional<PurchaseOrder> findByIdempotencyKey(String idempotencyKey);

    List<PurchaseOrder> findAllByOrderByIdDesc();

    List<PurchaseOrder> findByStatusOrderByIdDesc(PurchaseStatus status);

    List<PurchaseOrder> findByStatusIn(Collection<PurchaseStatus> statuses);
}
