package com.logistpulse.lab.messaging;

import com.logistpulse.lab.domain.OutboxEvent;
import com.logistpulse.lab.repo.OutboxRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Relé del Outbox: publica los eventos pendientes y los marca. Garantía AL MENOS UNA VEZ:
 * si el proceso cae entre publicar y marcar, el evento se reenvía (los consumidores deben tolerar duplicados).
 */
@Component
public class OutboxPublisher {

    private static final Logger log = LoggerFactory.getLogger(OutboxPublisher.class);

    private final OutboxRepository outbox;
    private final DispatchEventPublisher events;

    public OutboxPublisher(OutboxRepository outbox, DispatchEventPublisher events) {
        this.outbox = outbox;
        this.events = events;
    }

    @Scheduled(fixedDelayString = "${lab.outbox.interval-ms:1000}")
    public void tick() {
        relay();
    }

    /** Publica hasta 50 eventos pendientes; devuelve cuántos publicó. Se detiene en el primer fallo y reintenta luego. */
    public int relay() {
        int sent = 0;
        for (OutboxEvent e : outbox.findTop50ByPublishedAtIsNullOrderByIdAsc()) {
            try {
                events.publishAfterCommit(Long.valueOf(e.getPayload()));   // sin transacción activa: envía de inmediato
                e.markPublished();
                outbox.save(e);
                sent++;
            } catch (RuntimeException ex) {
                log.warn("Outbox: fallo publicando evento {}; se reintentará", e.getId(), ex);
                break;
            }
        }
        return sent;
    }
}
