package com.erdemgural.newssearch.search.internal;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
class SearchConfiguration {

    /** "Şu an" tek yerden alınır; süreye bağlı kurallar (Son Dakika) buna göre hesaplanır. */
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
