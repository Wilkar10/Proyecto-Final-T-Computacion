package com.logistpulse.lab.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;

/** Saldo vigente de un SKU. El libro de movimientos (StockMovement) es la fuente de verdad del saldo. */
@Entity
@Table(name = "stock_item")
public class StockItem {

    @Id
    @Column(length = 20)
    private String sku;

    @Column(nullable = false, length = 60)
    private String name;

    private int unitVolume;
    private int minStock;
    private int maxStock;
    private int leadTimeDays;
    private int onHand;
    private int reserved;

    @Version
    private Long version;

    protected StockItem() {
    }

    public StockItem(String sku, String name, int unitVolume, int minStock, int maxStock, int leadTimeDays, int onHand) {
        this.sku = sku;
        this.name = name;
        this.unitVolume = unitVolume;
        this.minStock = minStock;
        this.maxStock = maxStock;
        this.leadTimeDays = leadTimeDays;
        this.onHand = onHand;
    }

    public int available() {
        return onHand - reserved;
    }

    public boolean belowMin() {
        return available() < minStock;
    }

    /** Suma (o resta, si es negativo) al saldo. El servicio valida antes que el resultado no sea negativo. */
    public void apply(int qty) {
        this.onHand += qty;
    }

    public String getSku() { return sku; }
    public String getName() { return name; }
    public int getUnitVolume() { return unitVolume; }
    public int getMinStock() { return minStock; }
    public int getMaxStock() { return maxStock; }
    public int getLeadTimeDays() { return leadTimeDays; }
    public int getOnHand() { return onHand; }
    public int getReserved() { return reserved; }
}
