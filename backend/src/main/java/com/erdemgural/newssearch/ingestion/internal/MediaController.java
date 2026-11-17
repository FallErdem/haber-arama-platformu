package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.services.s3.model.GetObjectResponse;

@RestController
@RequestMapping("/api/v1/media")
class MediaController {

    private final MediaUrlSigner signer;
    private final MediaRepository mediaRepository;
    private final MediaStorage storage;
    private final Clock clock;

    MediaController(MediaUrlSigner signer, MediaRepository mediaRepository, MediaStorage storage, Clock clock) {
        this.signer = signer;
        this.mediaRepository = mediaRepository;
        this.storage = storage;
        this.clock = clock;
    }

    /**
     * Görselin kendisi (API sözleşmesi 4.4). Token istemez; adresin imzası ve süresi denetlenir.
     * Sıra önemlidir: imza veritabanına bakılmadan önce denetlenir, böylece imzasız istekler
     * görsellerin var olup olmadığını öğrenemez.
     */
    @GetMapping("/{id}")
    ResponseEntity<InputStreamResource> media(
            @PathVariable UUID id,
            @RequestParam(required = false) String exp,
            @RequestParam(required = false) String sig) {
        Instant expiry = signer.verify(id, exp, sig)
                .orElseThrow(() -> new ApiException(HttpStatus.FORBIDDEN, ErrorCode.MEDIA_URL_INVALID));
        MediaRepository.StoredFile file = mediaRepository
                .findServableFile(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND));
        ResponseInputStream<GetObjectResponse> content = storage.open(file.storageKey());

        return ResponseEntity.ok()
                // Tür, işçinin dosyanın kendisinden doğruladığı türdür (sunucunun bildirdiği değil).
                .contentType(MediaType.parseMediaType(file.contentType()))
                .contentLength(content.response().contentLength())
                // Tarayıcı türü kendisi tahmin etmeye çalışmaz; görsel diye sunulan dosya betik olarak çalışamaz.
                .header("X-Content-Type-Options", "nosniff")
                // private: yalnızca kullanıcının tarayıcısı saklar, ara sunucular saklamaz. Süre, adresin kalan
                // geçerlilik süresini aşmaz.
                .cacheControl(CacheControl.maxAge(Duration.between(clock.instant(), expiry))
                        .cachePrivate())
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline")
                .body(new InputStreamResource(content));
    }
}
