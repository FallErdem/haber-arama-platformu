/**
 * HTTP katmanının ortak parçaları: hata yanıtlarının biçimi (RFC 9457), hata
 * kodları ve istek kimliği. Bir iş modülü değildir; iş modülleri bu paketi
 * kullanır, bu paket hiçbir iş modülünü kullanmaz.
 */
@ApplicationModule(displayName = "Web Ortak")
package com.erdemgural.newssearch.web;

import org.springframework.modulith.ApplicationModule;
