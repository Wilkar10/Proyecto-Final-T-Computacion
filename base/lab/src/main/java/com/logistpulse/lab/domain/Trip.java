package com.logistpulse.lab.domain;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OrderColumn;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/** Viaje multi-parada: un robot recorre en orden varios pedidos y regresa al origen. */
@Entity
@Table(name = "trips", uniqueConstraints = @UniqueConstraint(name = "uk_trip_idem", columnNames = "idempotencyKey"))
public class Trip {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Idempotency-Key del cliente: la restricción UNIQUE es lo que impide el doble despacho bajo concurrencia. */
    @Column(nullable = false, length = 64)
    private String idempotencyKey;

    @Column(nullable = false, length = 20)
    private String robotCode;

    /** Costo del ciclo cerrado origen → paradas → origen (1 % de batería por unidad). */
    private int cost;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "trip_orders", joinColumns = @JoinColumn(name = "trip_id"))
    @OrderColumn(name = "seq")
    @Column(name = "order_code", length = 20)
    private List<String> orderCodes = new ArrayList<>();

    @Column(nullable = false)
    private Instant createdAt = Instant.now();

    protected Trip() {
    }

    public Trip(String idempotencyKey, String robotCode, int cost, List<String> orderCodes) {
        this.idempotencyKey = idempotencyKey;
        this.robotCode = robotCode;
        this.cost = cost;
        this.orderCodes = new ArrayList<>(orderCodes);
    }

    public Long getId() { return id; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public String getRobotCode() { return robotCode; }
    public int getCost() { return cost; }
    public List<String> getOrderCodes() { return orderCodes; }
    public Instant getCreatedAt() { return createdAt; }
}
