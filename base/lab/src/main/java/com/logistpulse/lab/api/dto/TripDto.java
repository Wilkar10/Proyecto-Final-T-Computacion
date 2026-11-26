package com.logistpulse.lab.api.dto;

import com.logistpulse.lab.domain.Trip;
import java.time.Instant;
import java.util.List;

public record TripDto(Long id, String idempotencyKey, String robot, List<String> orders, int cost, Instant createdAt) {

    public static TripDto from(Trip t) {
        return new TripDto(t.getId(), t.getIdempotencyKey(), t.getRobotCode(), List.copyOf(t.getOrderCodes()),
                t.getCost(), t.getCreatedAt());
    }
}
