package com.logistpulse.lab.api;

import com.logistpulse.lab.api.dto.TripDto;
import com.logistpulse.lab.api.dto.TripInput;
import com.logistpulse.lab.service.TripService;
import jakarta.validation.Valid;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.springframework.stereotype.Component;

/** Contrato en deberes/desarrollo-software/api/trips.openapi.yaml (contract-first). */
@Component
@Path("/api/trips")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class TripResource {

    private final TripService service;

    public TripResource(TripService service) {
        this.service = service;
    }

    @POST
    public Response dispatch(@HeaderParam("Idempotency-Key") String key, @Valid TripInput input) {
        TripService.Result r = service.dispatch(key, input.robot(), input.orders());
        return Response.status(r.created() ? 201 : 200).entity(TripDto.from(r.trip())).build();
    }
}
