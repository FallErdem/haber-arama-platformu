package com.erdemgural.newssearch;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * "Şu an" uygulamada tek yerden alınır. Süreye bağlı kurallar (Son Dakika, görsel adreslerinin
 * geçerlilik süresi) buna göre hesaplanır; testlerde sabit bir saat verilebilir.
 */
@Configuration(proxyBeanMethods = false)
class TimeConfiguration {

    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
