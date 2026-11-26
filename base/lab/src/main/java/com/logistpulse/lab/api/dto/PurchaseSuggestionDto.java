package com.logistpulse.lab.api.dto;

public record PurchaseSuggestionDto(String sku, int available, int onOrder, int suggestedQty) {
}
