package com.logistpulse.lab.api;

import com.logistpulse.lab.api.dto.PurchaseOrderDto;
import com.logistpulse.lab.api.dto.PurchaseOrderInput;
import com.logistpulse.lab.domain.PurchaseStatus;
import com.logistpulse.lab.service.InventoryService;
import jakarta.validation.Valid;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.QueryParam;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import java.util.List;
import org.springframework.stereotype.Component;

@Component
@Path("/api/purchase-orders")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class PurchaseOrderResource {

    private final InventoryService service;

    public PurchaseOrderResource(InventoryService service) {
        this.service = service;
    }

    @GET
    public List<PurchaseOrderDto> list(@QueryParam("status") PurchaseStatus status) {
        return service.listPurchaseOrders(status).stream().map(PurchaseOrderDto::from).toList();
    }

    @POST
    public Response propose(@HeaderParam("Idempotency-Key") String key, @Valid PurchaseOrderInput in) {
        var r = service.proposePurchaseOrder(key, in.sku(), in.qty(), in.proposedBy());
        return Response.status(r.created() ? 201 : 200).entity(PurchaseOrderDto.from(r.value())).build();
    }

    @POST
    @Path("/{id}/approve")
    public PurchaseOrderDto approve(@PathParam("id") Long id, @HeaderParam("X-Approver") String approver) {
        return PurchaseOrderDto.from(service.approve(id, approver));
    }

    @POST
    @Path("/{id}/receive")
    public PurchaseOrderDto receive(@PathParam("id") Long id) {
        return PurchaseOrderDto.from(service.receive(id));
    }
}
