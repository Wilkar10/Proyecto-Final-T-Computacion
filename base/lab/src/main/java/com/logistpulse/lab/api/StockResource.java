package com.logistpulse.lab.api;

import com.logistpulse.lab.api.dto.MovementInput;
import com.logistpulse.lab.api.dto.PurchaseSuggestionDto;
import com.logistpulse.lab.api.dto.StockItemDto;
import com.logistpulse.lab.service.InventoryService;
import jakarta.validation.Valid;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.DefaultValue;
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
@Path("/api/stock")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class StockResource {

    private final InventoryService service;

    public StockResource(InventoryService service) {
        this.service = service;
    }

    @GET
    public List<StockItemDto> list(@QueryParam("belowMin") @DefaultValue("false") boolean belowMin) {
        return service.listStock(belowMin).stream().map(StockItemDto::from).toList();
    }

    @GET
    @Path("/suggestions")
    public List<PurchaseSuggestionDto> suggestions() {
        return service.suggestions();
    }

    @GET
    @Path("/{sku}")
    public StockItemDto get(@PathParam("sku") String sku) {
        return StockItemDto.from(service.getStock(sku));
    }

    @POST
    @Path("/{sku}/movements")
    public Response movement(@PathParam("sku") String sku, @HeaderParam("Idempotency-Key") String key,
                             @Valid MovementInput in) {
        var r = service.registerMovement(key, sku, in.kind(), in.qty(), in.ref());
        return Response.status(r.created() ? 201 : 200).entity(StockItemDto.from(r.value())).build();
    }
}
