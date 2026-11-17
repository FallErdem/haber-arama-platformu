package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.web.ListResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/sources")
class SourceController {

    private final SourceRepository sourceRepository;

    SourceController(SourceRepository sourceRepository) {
        this.sourceRepository = sourceRepository;
    }

    /** Arama ekranındaki kaynak filtresinin seçenekleri. */
    @GetMapping
    ListResponse<SourceResponse> list() {
        return new ListResponse<>(sourceRepository.findEnabled());
    }
}
