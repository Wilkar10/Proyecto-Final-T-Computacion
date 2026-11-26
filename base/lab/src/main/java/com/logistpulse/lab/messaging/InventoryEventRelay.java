package com.logistpulse.lab.messaging;

import com.logistpulse.lab.domain.InventoryEvent;
import com.logistpulse.lab.repo.InventoryEventRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Relé del Outbox de inventario (stock.low, purchase.received, order.packed). Mismo patrón que OutboxPublisher:
 * al menos una vez. En modo lite solo registra en el log y marca como publicado.
 */
@Component
public class InventoryEventRelay {

    private static final Logger log = LoggerFactory.getLogger(InventoryEventRelay.class);

    private final InventoryEventRepository events;
    private final ObjectProvider<RabbitTemplate> rabbit;
    private final boolean enabled;

    public InventoryEventRelay(InventoryEventRepository events, ObjectProvider<RabbitTemplate> rabbit,
                               @Value("${lab.messaging.enabled:false}") boolean enabled) {
        this.events = events;
        this.rabbit = rabbit;
        this.enabled = enabled;
    }

    @Scheduled(fixedDelayString = "${lab.outbox.interval-ms:1000}")
    public void tick() {
        relay();
    }

    public int relay() {
        int sent = 0;
        for (InventoryEvent e : events.findTop50ByPublishedAtIsNullOrderByIdAsc()) {
            try {
                String body = "{\"eventType\":\"" + e.getType() + "\",\"data\":" + e.getPayload() + "}";
                if (enabled) {
                    rabbit.getObject().convertAndSend(RabbitTopology.INVENTORY_QUEUE, body);
                } else {
                    log.info("[lite] evento {} {}", e.getType(), e.getPayload());
                }
                e.markPublished();
                events.save(e);
                sent++;
            } catch (RuntimeException ex) {
                log.warn("Outbox inventario: fallo publicando {}; se reintentará", e.getId(), ex);
                break;
            }
        }
        return sent;
    }
}
