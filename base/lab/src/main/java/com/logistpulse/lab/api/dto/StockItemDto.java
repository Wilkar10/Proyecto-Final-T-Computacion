package com.logistpulse.lab.api.dto;

import com.logistpulse.lab.domain.StockItem;

public record StockItemDto(String sku, String name, int unitVolume, int onHand, int reserved, int available,
                           int minStock, int maxStock, int leadTimeDays, boolean belowMin) {

    public static StockItemDto from(StockItem s) {
        return new StockItemDto(s.getSku(), s.getName(), s.getUnitVolume(), s.getOnHand(), s.getReserved(),
                s.available(), s.getMinStock(), s.getMaxStock(), s.getLeadTimeDays(), s.belowMin());
    }
}
