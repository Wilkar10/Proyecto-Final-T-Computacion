package com.logistpulse.lab.repo;

import com.logistpulse.lab.domain.StockItem;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface StockItemRepository extends JpaRepository<StockItem, String> {

    List<StockItem> findAllByOrderBySkuAsc();
}
