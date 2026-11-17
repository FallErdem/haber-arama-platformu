package com.erdemgural.newssearch.web;

import org.springframework.http.HttpStatus;

/**
 * İstemciye belirli bir durum kodu ve hata koduyla bildirilecek, beklenen bir hata (örneğin sayfa
 * sınırının aşılması). Beklenmeyen hatalardan farkı: yığın izi loga yazılmaz ve yanıt
 * {@code 500} değildir.
 */
public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final ErrorCode code;

    public ApiException(HttpStatus status, ErrorCode code) {
        this(status, code, null);
    }

    public ApiException(HttpStatus status, ErrorCode code, Throwable cause) {
        super(code.name(), cause);
        this.status = status;
        this.code = code;
    }

    public HttpStatus status() {
        return status;
    }

    public ErrorCode code() {
        return code;
    }
}
