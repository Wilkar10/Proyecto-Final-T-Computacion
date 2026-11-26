package com.logistpulse.lab.api.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record PurchaseOrderInput(@NotBlank @Size(max = 20) String sku, @Min(1) @Max(10000) int qty,
                                 @Size(max = 60) String proposedBy) {
}
