package com.logistpulse.lab.repo;

import com.logistpulse.lab.domain.Order;
import com.logistpulse.lab.domain.OrderStatus;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrderRepository extends JpaRepository<Order, Long> {

    // El EntityGraph evita el problema N+1 al mapear warehouse y robot en el DTO.
    // Ejercicio: quítalo, activa spring.jpa.show-sql=true y cuenta las consultas.
    @Override
    @EntityGraph(attributePaths = {"warehouse", "robot"})
    Page<Order> findAll(Pageable pageable);

    @EntityGraph(attributePaths = {"warehouse", "robot"})
    Page<Order> findByStatus(OrderStatus status, Pageable pageable);

    boolean existsByCode(String code);

    Optional<Order> findByCode(String code);

    List<Order> findByCodeIn(Collection<String> codes);

    long countByTripIdAndStatusIn(Long tripId, Collection<OrderStatus> statuses);
}
