package com.logistpulse.lab.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;

public record TripInput(
        @NotBlank @Size(max = 20) String robot,
        @NotNull @Size(min = 1, max = 12, message = "entre 1 y 12 pedidos") List<String> orders) {
}
