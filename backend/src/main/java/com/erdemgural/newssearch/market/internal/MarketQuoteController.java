package com.erdemgural.newssearch.market.internal;

import com.erdemgural.newssearch.web.ListResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Ana sayfadaki piyasa kutusunun verileri. Giriş yapmış her aktif kullanıcı görebilir (SecurityConfiguration'daki
 * genel kural). API dışarıya istek atmaz; değerleri işçinin yazdığı tablodan okur.
 */
@RestController
@RequestMapping("/api/v1/market-quotes")
class MarketQuoteController {

    private final MarketQuoteService service;

    MarketQuoteController(MarketQuoteService service) {
        this.service = service;
    }

    @GetMapping
    ListResponse<MarketQuoteResponse> list() {
        return new ListResponse<>(service.findAll());
    }
}
