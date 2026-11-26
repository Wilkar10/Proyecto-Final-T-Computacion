package com.logistpulse.lab.api.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record MovementInput(@NotBlank String kind, @NotNull Integer qty, @Size(max = 40) String ref) {
}
