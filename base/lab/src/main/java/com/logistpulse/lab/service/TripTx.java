package com.logistpulse.lab.service;

import com.logistpulse.lab.api.ApiException;
import com.logistpulse.lab.domain.Order;
import com.logistpulse.lab.domain.OrderStatus;
import com.logistpulse.lab.domain.OutboxEvent;
import com.logistpulse.lab.domain.Robot;
import com.logistpulse.lab.domain.RobotStatus;
import com.logistpulse.lab.domain.Trip;
import com.logistpulse.lab.domain.Warehouse;
import com.logistpulse.lab.repo.OrderRepository;
import com.logistpulse.lab.repo.OutboxRepository;
import com.logistpulse.lab.repo.RobotRepository;
import com.logistpulse.lab.repo.TripRepository;
import com.logistpulse.lab.route.Point;
import com.logistpulse.lab.route.RoutePlanner;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Parte transaccional de la creación de un viaje: TODO O NADA. Va en un bean aparte para que
 * TripService pueda capturar la violación de unicidad (que aflora al confirmar) fuera de la transacción.
 */
@Service
public class TripTx {

    static final int MIN_BATTERY = OrderService.MIN_BATTERY;
    static final int MAX_ORDERS = 12;

    private final OrderRepository orders;
    private final RobotRepository robots;
    private final TripRepository trips;
    private final OutboxRepository outbox;
    private final RoutePlanner planner;

    public TripTx(OrderRepository orders, RobotRepository robots, TripRepository trips,
                  OutboxRepository outbox, RoutePlanner planner) {
        this.orders = orders;
        this.robots = robots;
        this.trips = trips;
        this.outbox = outbox;
        this.planner = planner;
    }

    @Transactional
    public Trip create(String key, String robotCode, List<String> codes) {
        if (codes == null || codes.isEmpty() || codes.size() > MAX_ORDERS) {
            throw new ApiException(400, "Se requieren entre 1 y " + MAX_ORDERS + " pedidos");
        }
        if (new HashSet<>(codes).size() != codes.size()) {
            throw new ApiException(400, "La lista de pedidos tiene duplicados");
        }
        Robot robot = robots.findByCode(robotCode)
                .orElseThrow(() -> new ApiException(404, "Robot " + robotCode + " no existe"));
        Map<String, Order> byCode = orders.findByCodeIn(codes).stream()
                .collect(Collectors.toMap(Order::getCode, Function.identity()));
        List<Order> ordered = new ArrayList<>();
        for (String c : codes) {
            Order o = byCode.get(c);
            if (o == null) {
                throw new ApiException(404, "Pedido " + c + " no existe");
            }
            ordered.add(o);
        }
        for (Order o : ordered) {
            if (o.getStatus() != OrderStatus.CREATED) {
                throw new ApiException(409, "Pedido " + o.getCode() + " ya no está CREATED (" + o.getStatus() + ")");
            }
        }
        if (robot.getStatus() != RobotStatus.IDLE) {
            throw new ApiException(409, "Robot " + robotCode + " no está libre");
        }

        // Ciclo cerrado: origen -> p1 -> ... -> pn -> origen (cada tramo con A*, 422 si algún destino es inalcanzable)
        Warehouse w = ordered.get(0).getWarehouse();
        Point origin = new Point(w.getOriginX(), w.getOriginY());
        Point prev = origin;
        int cost = 0;
        int[] cumulative = new int[ordered.size()];
        for (int i = 0; i < ordered.size(); i++) {
            Point next = new Point(ordered.get(i).getDestX(), ordered.get(i).getDestY());
            cost += planner.plan(prev, next).cost();
            cumulative[i] = cost;
            prev = next;
        }
        cost += planner.plan(prev, origin).cost();
        if (robot.getBattery() - cost < MIN_BATTERY) {
            throw new ApiException(409, "Batería insuficiente: costo " + cost + " con " + robot.getBattery()
                    + " % y reserva " + MIN_BATTERY + " %");
        }

        Trip trip = trips.saveAndFlush(new Trip(key, robotCode, cost, codes));   // UNIQUE(idempotencyKey) decide la carrera
        robot.setBattery(robot.getBattery() - cost);
        robot.setStatus(RobotStatus.BUSY);
        for (int i = 0; i < ordered.size(); i++) {
            Order o = ordered.get(i);
            o.setStatus(OrderStatus.DISPATCHED);
            o.setRobot(robot);
            o.setTripId(trip.getId());
            o.setEtaMinutes(cumulative[i] * 2);
            outbox.save(new OutboxEvent("order.dispatched", String.valueOf(o.getId())));   // misma transacción
        }
        return trip;
    }
}
