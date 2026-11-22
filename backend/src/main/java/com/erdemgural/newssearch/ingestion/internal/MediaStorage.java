package com.erdemgural.newssearch.ingestion.internal;

import com.erdemgural.newssearch.ingestion.ObjectStorageStatus;
import com.erdemgural.newssearch.web.ApiException;
import com.erdemgural.newssearch.web.ErrorCode;
import java.io.IOException;
import java.net.URI;
import java.time.Duration;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.ResponseInputStream;
import software.amazon.awssdk.core.checksums.ResponseChecksumValidation;
import software.amazon.awssdk.core.exception.SdkException;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.GetObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;
import software.amazon.awssdk.services.s3.model.S3Exception;

/**
 * Nesne depolamadan (MinIO) görsel okuma. MinIO, Amazon S3 ile aynı arayüzü sunar; bağlantı AWS
 * SDK'nın S3 istemcisiyle kurulur. İşçideki {@code boto3} ile aynı arayüz kullanıldığından ileride
 * başka bir S3 uyumlu depolamaya geçilirse kod değişmez (R-35).
 */
@Component
class MediaStorage implements ObjectStorageStatus {

    /** Nesne depolama yanıt vermiyorsa görsel isteği bu kadar beklemez. */
    static final Duration CALL_TIMEOUT = Duration.ofSeconds(5);

    /** Durum kontrolünde okunmaya çalışılan, var olmayan dosya. */
    private static final String STATUS_CHECK_KEY = "status-check/missing";

    private final S3Client client;
    private final String bucket;

    MediaStorage(MediaProperties properties) {
        this.client = S3Client.builder()
                .endpointOverride(URI.create(properties.storageUrl()))
                // MinIO bölge kullanmaz, ama S3 imzası bir bölge adı ister.
                .region(Region.US_EAST_1)
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(properties.accessKey(), properties.secretKey())))
                // Kova adı adresin yolunda (http://minio:9000/media/...). Varsayılan biçim kova adını alan
                // adına ekler (media.minio); küme içinde böyle bir ad yoktur.
                .forcePathStyle(true)
                // Sağlama toplamı yalnızca istek gerektirdiğinde doğrulanır; S3 uyumlu depolamalar Amazon'un
                // yeni sağlama toplamı başlıklarını her zaman döndürmez.
                .responseChecksumValidation(ResponseChecksumValidation.WHEN_REQUIRED)
                .overrideConfiguration(configuration -> configuration.apiCallTimeout(CALL_TIMEOUT))
                .build();
        this.bucket = properties.bucket();
    }

    /**
     * Dosyayı okumak için açar; çağıran akışı kapatmalıdır. Dosya yoksa {@code 404 NOT_FOUND}, nesne
     * depolamaya ulaşılamazsa {@code 503 MEDIA_UNAVAILABLE} fırlatır.
     */
    ResponseInputStream<GetObjectResponse> open(String storageKey) {
        try {
            return client.getObject(request -> request.bucket(bucket).key(storageKey));
        } catch (NoSuchKeyException exception) {
            throw new ApiException(HttpStatus.NOT_FOUND, ErrorCode.NOT_FOUND, exception);
        } catch (SdkException exception) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, ErrorCode.MEDIA_UNAVAILABLE, exception);
        }
    }

    /**
     * Var olmayan bir dosya ister. MinIO "dosya yok" (404) veya "erişim yok" (403 {@code AccessDenied}) derse
     * ayaktadır ve API'yi tanımıştır. Hiç yanıt vermezse ya da anahtarı reddederse kullanılamaz. API'nin
     * yalnızca dosya okuma yetkisi vardır; bu kontrol için yeni yetki gerekmez.
     */
    @Override
    public boolean isAvailable() {
        try (ResponseInputStream<GetObjectResponse> unexpected =
                client.getObject(request -> request.bucket(bucket).key(STATUS_CHECK_KEY))) {
            return true;
        } catch (NoSuchKeyException exception) {
            return true;
        } catch (S3Exception exception) {
            return exception.statusCode() == 403
                    && exception.awsErrorDetails() != null
                    && "AccessDenied".equals(exception.awsErrorDetails().errorCode());
        } catch (SdkException | IOException exception) {
            // IOException: dosya beklenmedik biçimde varsa, akış kapatılırken çıkabilir.
            return false;
        }
    }
}
