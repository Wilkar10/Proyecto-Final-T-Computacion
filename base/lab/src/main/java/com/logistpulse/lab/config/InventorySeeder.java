package com.logistpulse.lab.config;

import com.logistpulse.lab.domain.StockItem;
import com.logistpulse.lab.repo.StockItemRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/** 12 SKU sintéticos, los mismos que 15_inventory_seed.sql y el simulador (volumen 1..4, stock inicial = 80% del máximo). */
@Component
public class InventorySeeder implements CommandLineRunner {

    private static final String[] NAMES = {"Arroz 1 kg", "Aceite 1 L", "Azúcar 1 kg", "Leche 1 L", "Atún lata",
            "Fideos 400 g", "Harina 1 kg", "Sal 500 g", "Café 250 g", "Galletas pack", "Detergente 1 kg",
            "Papel higiénico x4"};

    private final StockItemRepository stock;

    public InventorySeeder(StockItemRepository stock) {
        this.stock = stock;
    }

    @Override
    @Transactional
    public void run(String... args) {
        if (stock.count() > 0) {
            return;
        }
        for (int i = 1; i <= 12; i++) {
            int min = i <= 3 ? 30 : i <= 7 ? 15 : 8;
            int max = i <= 3 ? 90 : i <= 7 ? 45 : 24;
            stock.save(new StockItem(String.format("SKU-%02d", i), NAMES[i - 1], 1 + ((i - 1) * 7) % 4,
                    min, max, 2, (int) (max * 0.8)));
        }
    }
}
