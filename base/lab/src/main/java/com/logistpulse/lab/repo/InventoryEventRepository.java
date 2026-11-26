package com.logistpulse.lab.repo;

import com.logistpulse.lab.domain.InventoryEvent;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InventoryEventRepository extends JpaRepository<InventoryEvent, Long> {

    List<InventoryEvent> findTop50ByPublishedAtIsNullOrderByIdAsc();
}
