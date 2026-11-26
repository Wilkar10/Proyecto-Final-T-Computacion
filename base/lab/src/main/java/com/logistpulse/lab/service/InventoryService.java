package com.logistpulse.lab.service;

import com.logistpulse.lab.api.ApiException;
import com.logistpulse.lab.api.dto.PackLine;
import com.logistpulse.lab.api.dto.PurchaseSuggestionDto;
import com.logistpulse.lab.domain.InventoryEvent;
import com.logistpulse.lab.domain.Order;
import com.logistpulse.lab.domain.OrderStatus;
import com.logistpulse.lab.domain.PackingJob;
import com.logistpulse.lab.domain.PurchaseOrder;
import com.logistpulse.lab.domain.PurchaseStatus;
import com.logistpulse.lab.domain.StockItem;
import com.logistpulse.lab.domain.StockMovement;
import com.logistpulse.lab.repo.InventoryEventRepository;
import com.logistpulse.lab.repo.OrderRepository;
import com.logistpulse.lab.repo.PackingJobRepository;
import com.logistpulse.lab.repo.PurchaseOrderRepository;
import com.logistpulse.lab.repo.StockItemRepository;
import com.logistpulse.lab.repo.StockMovementRepository;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Inventario, reposición y packing. Cada operación de escritura es TODO O NADA (una transacción) y las que crean algo
 * son idempotentes por Idempotency-Key (mismo patrón que /api/trips). El servicio SUGIERE compras; una persona las
 * crea y las aprueba. Los eventos se guardan en la misma transacción (Outbox) y un relé los publica.
 */
@Service
public class InventoryService {

    /** Resultado: el valor y si se creó ahora (201) o es una repetición (200). */
    public record Result<T>(T value, boolean created) {
    }

    private final TransactionTemplate tx;
    private final StockItemRepository stock;
    private final StockMovementRepository movements;
    private final PurchaseOrderRepository purchases;
    private final PackingJobRepository jobs;
    private final InventoryEventRepository events;
    private final OrderRepository orders;
    private final int boxCapacity;

    public InventoryService(PlatformTransactionManager txManager, StockItemRepository stock,
                            StockMovementRepository movements, PurchaseOrderRepository purchases,
                            PackingJobRepository jobs, InventoryEventRepository events, OrderRepository orders,
                            @Value("${lab.packing.box-capacity:10}") int boxCapacity) {
        this.tx = new TransactionTemplate(txManager);
        this.stock = stock;
        this.movements = movements;
        this.purchases = purchases;
        this.jobs = jobs;
        this.events = events;
        this.orders = orders;
        this.boxCapacity = boxCapacity;
    }

    // ------------------------------------------------------------------ consultas
    public List<StockItem> listStock(boolean belowMinOnly) {
        List<StockItem> all = stock.findAllByOrderBySkuAsc();
        return belowMinOnly ? all.stream().filter(StockItem::belowMin).toList() : all;
    }

    public StockItem getStock(String sku) {
        return stock.findById(sku).orElseThrow(() -> new ApiException(404, "SKU " + sku + " no existe"));
    }

    /** Sugiere (no crea) compras para los SKU cuya posición (disponible + ya pedido) cae bajo el mínimo. */
    public List<PurchaseSuggestionDto> suggestions() {
        List<PurchaseSuggestionDto> out = new ArrayList<>();
        List<PurchaseOrder> open = purchases.findByStatusIn(List.of(PurchaseStatus.PROPOSED, PurchaseStatus.APPROVED));
        for (StockItem s : stock.findAllByOrderBySkuAsc()) {
            int onOrder = open.stream().filter(p -> p.getSku().equals(s.getSku())).mapToInt(PurchaseOrder::getQty).sum();
            int qty = ReorderPolicy.suggestedQty(s.available(), onOrder, s.getMinStock(), s.getMaxStock());
            if (qty > 0) {
                out.add(new PurchaseSuggestionDto(s.getSku(), s.available(), onOrder, qty));
            }
        }
        return out;
    }

    public List<PurchaseOrder> listPurchaseOrders(PurchaseStatus status) {
        return status == null ? purchases.findAllByOrderByIdDesc() : purchases.findByStatusOrderByIdDesc(status);
    }

    public PackingJob getPackingJob(Long id) {
        return jobs.findById(id).orElseThrow(() -> new ApiException(404, "Empaque " + id + " no existe"));
    }

    // ------------------------------------------------------------------ escrituras
    public Result<StockItem> registerMovement(String key, String sku, String kind, int qty, String ref) {
        requireKey(key);
        if (!"RECEIPT".equals(kind) && !"ADJUST".equals(kind)) {
            throw new ApiException(400, "kind debe ser RECEIPT o ADJUST");
        }
        if ("RECEIPT".equals(kind) && qty <= 0) {
            throw new ApiException(400, "RECEIPT exige qty > 0");
        }
        if (qty == 0) {
            throw new ApiException(400, "qty no puede ser 0");
        }
        return once(() -> movements.findByIdempotencyKey(key).map(m -> stock.findById(m.getSku()).orElseThrow()),
                () -> {
                    StockItem item = getStock(sku);
                    if (item.getOnHand() + qty < 0) {
                        throw new ApiException(409, "El ajuste dejaría el saldo de " + sku + " bajo cero");
                    }
                    item.apply(qty);
                    stock.save(item);
                    movements.save(new StockMovement(sku, kind, qty, ref, key));
                    lowStockEvent(item);
                    return item;
                });
    }

    public Result<PurchaseOrder> proposePurchaseOrder(String key, String sku, int qty, String proposedBy) {
        requireKey(key);
        return once(() -> purchases.findByIdempotencyKey(key), () -> {
            StockItem item = getStock(sku);
            String by = proposedBy == null || proposedBy.isBlank() ? "sistema" : proposedBy;
            return purchases.save(new PurchaseOrder(sku, qty, by, key,
                    Instant.now().plus(item.getLeadTimeDays(), ChronoUnit.DAYS)));
        });
    }

    public PurchaseOrder approve(Long id, String approver) {
        if (approver == null || approver.isBlank() || approver.length() > 60) {
            throw new ApiException(400, "Falta la cabecera X-Approver (1..60 caracteres)");
        }
        return tx.execute(s -> {
            PurchaseOrder p = purchases.findById(id).orElseThrow(() -> new ApiException(404, "Orden " + id + " no existe"));
            if (p.getStatus() != PurchaseStatus.PROPOSED) {
                throw new ApiException(409, "La orden " + id + " no está PROPOSED (" + p.getStatus() + ")");
            }
            p.approve(approver);
            return purchases.save(p);
        });
    }

    public PurchaseOrder receive(Long id) {
        return tx.execute(s -> {
            PurchaseOrder p = purchases.findById(id).orElseThrow(() -> new ApiException(404, "Orden " + id + " no existe"));
            if (p.getStatus() != PurchaseStatus.APPROVED) {
                throw new ApiException(409, "La orden " + id + " no está APPROVED (" + p.getStatus() + ")");
            }
            StockItem item = getStock(p.getSku());
            item.apply(p.getQty());
            stock.save(item);
            movements.save(new StockMovement(p.getSku(), "RECEIPT", p.getQty(), "PO-" + id, "po-receive-" + id));
            p.markReceived();
            events.save(new InventoryEvent("purchase.received",
                    "{\"poId\":" + id + ",\"sku\":\"" + p.getSku() + "\",\"qty\":" + p.getQty() + "}"));
            return purchases.save(p);
        });
    }

    public Result<PackingJob> pack(String key, String orderCode, List<PackLine> lines) {
        requireKey(key);
        Set<String> seen = new HashSet<>();
        for (PackLine l : lines) {
            if (!seen.add(l.sku())) {
                throw new ApiException(400, "El SKU " + l.sku() + " está repetido en las líneas");
            }
        }
        return once(() -> jobs.findByIdempotencyKey(key), () -> {
            Order order = orders.findByCode(orderCode)
                    .orElseThrow(() -> new ApiException(404, "Pedido " + orderCode + " no existe"));
            if (order.getStatus() != OrderStatus.CREATED) {
                throw new ApiException(409, "Pedido " + orderCode + " ya no está CREATED (" + order.getStatus() + ")");
            }
            if (jobs.findByOrderCode(orderCode).isPresent()) {
                throw new ApiException(409, "Pedido " + orderCode + " ya fue empacado");
            }
            // 1) verificar TODO el stock antes de tocar nada (todo o nada)
            List<StockItem> items = new ArrayList<>();
            for (PackLine l : lines) {
                StockItem item = getStock(l.sku());
                if (item.available() < l.qty()) {
                    throw new ApiException(409, "FALTA_PRODUCTO: " + l.sku() + " (disponible " + item.available()
                            + ", pedido " + l.qty() + ")");
                }
                items.add(item);
            }
            // 2) descontar, acomodar en cajas y registrar
            List<Integer> pieces = new ArrayList<>();
            for (int i = 0; i < lines.size(); i++) {
                StockItem item = items.get(i);
                int qty = lines.get(i).qty();
                item.apply(-qty);
                stock.save(item);
                movements.save(new StockMovement(item.getSku(), "PICK", -qty, orderCode, null));
                lowStockEvent(item);
                for (int k = 0; k < qty; k++) {
                    pieces.add(item.getUnitVolume());
                }
            }
            List<Integer> boxes;
            try {
                boxes = Packer.firstFitDecreasing(pieces, boxCapacity);
            } catch (IllegalArgumentException e) {
                throw new ApiException(422, e.getMessage());
            }
            PackingJob job = jobs.save(new PackingJob(orderCode, key, boxCapacity, boxes));
            double fill = Math.round(1000.0 * job.getPieceVolume() / (job.getBoxCount() * job.getBoxCapacity())) / 10.0;
            events.save(new InventoryEvent("order.packed", "{\"jobId\":" + job.getId() + ",\"orderCode\":\"" + orderCode
                    + "\",\"boxCount\":" + job.getBoxCount() + ",\"fillPct\":" + fill + "}"));
            return job;
        });
    }

    // ------------------------------------------------------------------ utilidades
    private void lowStockEvent(StockItem item) {
        if (item.belowMin()) {
            events.save(new InventoryEvent("stock.low", "{\"sku\":\"" + item.getSku() + "\",\"available\":"
                    + item.available() + ",\"minStock\":" + item.getMinStock() + "}"));
        }
    }

    private static void requireKey(String key) {
        if (key == null || key.isBlank() || key.length() > 64) {
            throw new ApiException(400, "Falta la cabecera Idempotency-Key (1..64 caracteres)");
        }
    }

    /** Ejecuta `create` en una transacción; si la misma clave ya existe (o gana una carrera), devuelve ese resultado. */
    private <T> Result<T> once(Supplier<Optional<T>> find, Supplier<T> create) {
        Optional<T> existing = find.get();
        if (existing.isPresent()) {
            return new Result<>(existing.get(), false);
        }
        try {
            return new Result<>(tx.execute(s -> create.get()), true);
        } catch (DataIntegrityViolationException | ObjectOptimisticLockingFailureException race) {
            Optional<T> winner = find.get();
            if (winner.isPresent()) {
                return new Result<>(winner.get(), false);
            }
            throw race;
        }
    }
}
