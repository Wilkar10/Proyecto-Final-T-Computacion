package com.logistpulse.lab.api.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import java.util.List;

public record PackingInput(@NotBlank @Size(max = 20) String orderCode,
                           @NotNull @Size(min = 1, max = 20, message = "entre 1 y 20 líneas") List<@Valid PackLine> lines) {
}
