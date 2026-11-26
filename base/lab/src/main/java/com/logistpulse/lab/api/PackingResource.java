package com.logistpulse.lab.api;

import com.logistpulse.lab.api.dto.PackingInput;
import com.logistpulse.lab.api.dto.PackingJobDto;
import com.logistpulse.lab.service.InventoryService;
import jakarta.validation.Valid;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.springframework.stereotype.Component;

@Component
@Path("/api/packing-jobs")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class PackingResource {

    private final InventoryService service;

    public PackingResource(InventoryService service) {
        this.service = service;
    }

    @POST
    public Response pack(@HeaderParam("Idempotency-Key") String key, @Valid PackingInput in) {
        var r = service.pack(key, in.orderCode(), in.lines());
        return Response.status(r.created() ? 201 : 200).entity(PackingJobDto.from(r.value())).build();
    }

    @GET
    @Path("/{id}")
    public PackingJobDto get(@PathParam("id") Long id) {
        return PackingJobDto.from(service.getPackingJob(id));
    }
}
