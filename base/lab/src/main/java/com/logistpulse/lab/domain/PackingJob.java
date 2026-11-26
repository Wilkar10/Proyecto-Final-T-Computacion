package com.logistpulse.lab.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "packing_job")
public class PackingJob {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Un pedido se empaca una sola vez. */
    @Column(nullable = false, unique = true, length = 20)
    private String orderCode;

    @Column(unique = true, length = 64)
    private String idempotencyKey;

    private int boxCapacity;
    private int pieceVolume;
    private int boxCount;

    /** Volumen usado en cada caja, separado por comas ("10,9,3"). */
    @Column(nullable = false, length = 200)
    private String boxes;

    @Column(nullable = false)
    private Instant packedAt = Instant.now();

    protected PackingJob() {
    }

    public PackingJob(String orderCode, String idempotencyKey, int boxCapacity, List<Integer> boxVolumes) {
        this.orderCode = orderCode;
        this.idempotencyKey = idempotencyKey;
        this.boxCapacity = boxCapacity;
        this.boxCount = boxVolumes.size();
        this.pieceVolume = boxVolumes.stream().mapToInt(Integer::intValue).sum();
        this.boxes = String.join(",", boxVolumes.stream().map(String::valueOf).toList());
    }

    public List<Integer> boxVolumes() {
        List<Integer> out = new ArrayList<>();
        for (String s : boxes.split(",")) {
            out.add(Integer.valueOf(s));
        }
        return out;
    }

    public Long getId() { return id; }
    public String getOrderCode() { return orderCode; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public int getBoxCapacity() { return boxCapacity; }
    public int getPieceVolume() { return pieceVolume; }
    public int getBoxCount() { return boxCount; }
    public Instant getPackedAt() { return packedAt; }
}
