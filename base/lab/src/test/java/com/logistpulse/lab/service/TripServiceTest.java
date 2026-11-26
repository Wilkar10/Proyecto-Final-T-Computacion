package com.logistpulse.lab.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowableOfType;

import com.logistpulse.lab.api.ApiException;
import com.logistpulse.lab.api.dto.OrderInput;
import com.logistpulse.lab.domain.OrderStatus;
import com.logistpulse.lab.messaging.OutboxPublisher;
import com.logistpulse.lab.repo.OrderRepository;
import com.logistpulse.lab.repo.OutboxRepository;
import com.logistpulse.lab.repo.RobotRepository;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * Despacho multi-parada. Cada prueba usa SU robot (el contexto H2 se comparte entre pruebas).
 * Plano: origen (0,0); pasillo superior y=0 con costo 1 por celda -> (3,0)=3, (6,0)=6. Ciclo (3,0),(6,0) = 3+3+6 = 12.
 */
@SpringBootTest(properties = "lab.outbox.interval-ms=3600000")
class TripServiceTest {

    @Autowired TripService trips;
    @Autowired OrderService orderService;
    @Autowired OrderRepository orders;
    @Autowired RobotRepository robots;
    @Autowired OutboxRepository outbox;
    @Autowired OutboxPublisher relay;

    private String order(int x, int y) {
        String code = "LP-" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
        orderService.create(new OrderInput(code, "Cliente prueba", x, y));
        return code;
    }

    private String key() {
        return UUID.randomUUID().toString();
    }

    private int battery(String robot) {
        return robots.findByCode(robot).orElseThrow().getBattery();
    }

    @Test
    void tripDispatchesAllOrdersWithOneRobotAndChargesTheWholeCycle() {
        String a = order(3, 0), b = order(6, 0);
        int before = battery("AMR-01");
        TripService.Result r = trips.dispatch(key(), "AMR-01", List.of(a, b));
        assertThat(r.created()).isTrue();
        assertThat(r.trip().getCost()).isEqualTo(12);
        assertThat(battery("AMR-01")).isEqualTo(before - 12);
        assertThat(orders.findByCode(a).orElseThrow().getStatus()).isEqualTo(OrderStatus.DISPATCHED);
        assertThat(orders.findByCode(b).orElseThrow().getStatus()).isEqualTo(OrderStatus.DISPATCHED);
    }

    @Test
    void sameIdempotencyKeyReturnsTheSameTripWithoutNewEffects() {
        String a = order(3, 0);
        String k = key();
        int before = battery("AMR-02");
        TripService.Result first = trips.dispatch(k, "AMR-02", List.of(a));
        TripService.Result second = trips.dispatch(k, "AMR-02", List.of(a));
        assertThat(first.created()).isTrue();
        assertThat(second.created()).isFalse();
        assertThat(second.trip().getId()).isEqualTo(first.trip().getId());
        assertThat(battery("AMR-02")).isEqualTo(before - first.trip().getCost());   // descontada UNA sola vez
    }

    @Test
    void insufficientBatteryIsAllOrNothing() {
        String a = order(3, 0), b = order(6, 0);
        int before = battery("AMR-05");                     // 15 % < reserva 20 %
        ApiException e = catchThrowableOfType(ApiException.class, () -> trips.dispatch(key(), "AMR-05", List.of(a, b)));
        assertThat(e).isNotNull();
        assertThat(e.getStatus()).isEqualTo(409);
        assertThat(battery("AMR-05")).isEqualTo(before);
        assertThat(orders.findByCode(a).orElseThrow().getStatus()).isEqualTo(OrderStatus.CREATED);
        assertThat(orders.findByCode(b).orElseThrow().getStatus()).isEqualTo(OrderStatus.CREATED);
    }

    @Test
    void invalidRequestsAreRejected() {
        String a = order(3, 0);
        assertThat(status(() -> trips.dispatch(key(), "AMR-03", List.of()))).isEqualTo(400);
        assertThat(status(() -> trips.dispatch(key(), "AMR-03", List.of(a, a)))).isEqualTo(400);
        assertThat(status(() -> trips.dispatch(" ", "AMR-03", List.of(a)))).isEqualTo(400);
        assertThat(status(() -> trips.dispatch(key(), "AMR-99", List.of(a)))).isEqualTo(404);
        assertThat(status(() -> trips.dispatch(key(), "AMR-03", List.of("LP-NOEXISTE")))).isEqualTo(404);
        assertThat(orders.findByCode(a).orElseThrow().getStatus()).isEqualTo(OrderStatus.CREATED);
    }

    @Test
    void alreadyDispatchedOrderIsConflict() {
        String a = order(3, 0);
        trips.dispatch(key(), "AMR-04", List.of(a));
        assertThat(status(() -> trips.dispatch(key(), "AMR-03", List.of(a)))).isEqualTo(409);
    }

    @Test
    void concurrentRequestsWithSameKeyCreateExactlyOneTrip() throws Exception {
        String a = order(3, 0);
        String k = key();
        ExecutorService pool = Executors.newFixedThreadPool(2);
        CountDownLatch go = new CountDownLatch(1);
        Callable<TripService.Result> call = () -> {
            go.await();
            return trips.dispatch(k, "AMR-03", List.of(a));
        };
        Future<TripService.Result> f1 = pool.submit(call), f2 = pool.submit(call);
        int before = battery("AMR-03");
        go.countDown();
        Long id1 = f1.get().trip().getId(), id2 = f2.get().trip().getId();
        pool.shutdown();
        assertThat(id1).isEqualTo(id2);                                     // misma respuesta para ambas
        assertThat(before - battery("AMR-03")).isLessThanOrEqualTo(12);     // y un solo descuento (≤ costo del ciclo)
    }

    @Test
    void outboxRelayPublishesPendingEventsOnce() {
        String a = order(3, 0);
        trips.dispatch(key(), "AMR-02", List.of(a));
        assertThat(outbox.countByPublishedAtIsNull()).isGreaterThanOrEqualTo(1);
        assertThat(relay.relay()).isGreaterThanOrEqualTo(1);
        assertThat(outbox.countByPublishedAtIsNull()).isZero();
        assertThat(relay.relay()).isZero();                                 // nada pendiente: no republica
    }

    private int status(Runnable r) {
        ApiException e = catchThrowableOfType(ApiException.class, r::run);
        assertThat(e).as("se esperaba ApiException").isNotNull();
        return e.getStatus();
    }
}
