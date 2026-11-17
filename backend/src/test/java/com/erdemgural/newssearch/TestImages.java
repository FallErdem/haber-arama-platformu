package com.erdemgural.newssearch;

import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URI;
import java.util.UUID;
import javax.imageio.ImageIO;
import org.springframework.jdbc.core.simple.JdbcClient;
import software.amazon.awssdk.auth.credentials.AwsBasicCredentials;
import software.amazon.awssdk.auth.credentials.StaticCredentialsProvider;
import software.amazon.awssdk.core.checksums.RequestChecksumCalculation;
import software.amazon.awssdk.core.checksums.ResponseChecksumValidation;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.S3Object;

/**
 * Testler için haber görselleri oluşturur: kümede Python işçisinin yaptığı gibi dosyayı MinIO'ya
 * yükler ve {@code media} satırını yazar. Uygulamanın kullanıcısı yalnızca okuyabildiği için yükleme
 * yönetici kullanıcısıyla yapılır.
 */
public class TestImages {

    private static final String BUCKET = "media";

    private final String url;
    private final S3Client admin;
    private final JdbcClient jdbcClient;

    TestImages(String url, String rootUser, String rootPassword, JdbcClient jdbcClient) {
        this.url = url;
        this.jdbcClient = jdbcClient;
        this.admin = S3Client.builder()
                .endpointOverride(URI.create(url))
                .region(Region.US_EAST_1)
                .credentialsProvider(
                        StaticCredentialsProvider.create(AwsBasicCredentials.create(rootUser, rootPassword)))
                .forcePathStyle(true)
                .requestChecksumCalculation(RequestChecksumCalculation.WHEN_REQUIRED)
                .responseChecksumValidation(ResponseChecksumValidation.WHEN_REQUIRED)
                .build();
    }

    public String url() {
        return url;
    }

    /** Verilen boyutlarda küçük bir PNG görseli. */
    public static byte[] png(int width, int height) {
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        image.getGraphics().setColor(Color.RED);
        image.getGraphics().fillRect(0, 0, width, height);
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        try {
            ImageIO.write(image, "png", output);
        } catch (IOException exception) {
            throw new UncheckedIOException(exception);
        }
        return output.toByteArray();
    }

    /** İndirilmiş bir görsel: dosya MinIO'da, satır {@code DOWNLOADED}. Görselin kimliğini döner. */
    public UUID addDownloaded(UUID articleId, int position, byte[] body, String contentType, int width, int height) {
        UUID id = UUID.randomUUID();
        String key = "articles/" + articleId + "/" + id;
        admin.putObject(
                request -> request.bucket(BUCKET).key(key).contentType(contentType), RequestBody.fromBytes(body));
        insertDownloadedRow(id, articleId, position, key, contentType, body.length, width, height);
        return id;
    }

    /** Satırı {@code DOWNLOADED} olan ama dosyası nesne depolamada bulunmayan görsel. */
    public UUID addDownloadedWithoutFile(UUID articleId, int position) {
        UUID id = UUID.randomUUID();
        insertDownloadedRow(id, articleId, position, "articles/" + articleId + "/" + id, "image/png", 10, 4, 3);
        return id;
    }

    /** Henüz indirilmemiş ({@code PENDING}) veya indirilemeyen ({@code FAILED}) görsel. */
    public UUID addNotDownloaded(UUID articleId, int position, String status) {
        return jdbcClient
                .sql("""
				INSERT INTO media (article_id, media_type, position, source_url, status)
				VALUES (:articleId, 'IMAGE', :position, :sourceUrl, :status)
				RETURNING id
				""")
                .param("articleId", articleId)
                .param("position", position)
                .param("sourceUrl", sourceUrl())
                .param("status", status)
                .query(UUID.class)
                .single();
    }

    /** Testlerin yüklediği bütün dosyaları siler. Satırlar haberlerle birlikte silinir. */
    public void clearFiles() {
        for (S3Object object :
                admin.listObjectsV2(request -> request.bucket(BUCKET)).contents()) {
            admin.deleteObject(request -> request.bucket(BUCKET).key(object.key()));
        }
    }

    /**
     * İndirilmiş görselin satırı tek seferde, bütün alanlarıyla yazılır: tablodaki kısıt
     * ({@code media_downloaded_check}), anahtarı olmayan bir görselin indirilmiş sayılmasına izin vermez.
     */
    private void insertDownloadedRow(
            UUID id, UUID articleId, int position, String key, String contentType, long size, int width, int height) {
        jdbcClient
                .sql("""
				INSERT INTO media (id, article_id, media_type, position, source_url, status, storage_key,
				                   content_type, size_bytes, width, height)
				VALUES (:id, :articleId, 'IMAGE', :position, :sourceUrl, 'DOWNLOADED', :key,
				        :contentType, :size, :width, :height)
				""")
                .param("id", id)
                .param("articleId", articleId)
                .param("position", position)
                .param("sourceUrl", sourceUrl())
                .param("key", key)
                .param("contentType", contentType)
                .param("size", size)
                .param("width", width)
                .param("height", height)
                .update();
    }

    private static String sourceUrl() {
        return "https://images.example.test/" + UUID.randomUUID() + ".png";
    }
}
