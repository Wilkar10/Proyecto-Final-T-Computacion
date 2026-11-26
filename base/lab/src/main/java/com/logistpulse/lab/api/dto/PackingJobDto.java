package com.logistpulse.lab.api.dto;

import com.logistpulse.lab.domain.PackingJob;
import java.time.Instant;
import java.util.List;

public record PackingJobDto(Long id, String orderCode, int boxCount, List<Integer> boxes, int pieceVolume,
                            int boxCapacity, double fillPct, Instant packedAt) {

    public static PackingJobDto from(PackingJob j) {
        double fill = Math.round(1000.0 * j.getPieceVolume() / (j.getBoxCount() * j.getBoxCapacity())) / 10.0;
        return new PackingJobDto(j.getId(), j.getOrderCode(), j.getBoxCount(), j.boxVolumes(), j.getPieceVolume(),
                j.getBoxCapacity(), fill, j.getPackedAt());
    }
}
