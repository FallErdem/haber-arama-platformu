package com.erdemgural.newssearch;

import java.io.IOException;
import java.io.OutputStream;
import java.io.UncheckedIOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.List;
import java.util.UUID;
import java.util.function.Consumer;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import com.sun.net.httpserver.HttpServer;

/**
 * Testlerde Keycloak'ın yerini tutar: kendi anahtarıyla token imzalar ve açık
 * anahtarını Keycloak'ın {@code /certs} adresi gibi HTTP üzerinden yayımlar.
 * Uygulama anahtarı gerçekte olduğu gibi bu adresten indirdiği için token
 * doğrulama ayarlarının kendisi sınanmış olur.
 */
public class TestTokenIssuer {

	public static final String ISSUER = "http://haber.localhost/auth/realms/haber";
	public static final String AUDIENCE = "haber-api";

	private final RSAKey signingKey = generateKey("test-key");
	private final HttpServer jwksServer;

	TestTokenIssuer() {
		byte[] jwks = new JWKSet(signingKey.toPublicJWK()).toString().getBytes(StandardCharsets.UTF_8);
		try {
			// 0 numaralı port: işletim sistemi boş bir port seçer.
			jwksServer = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
		}
		catch (IOException exception) {
			throw new UncheckedIOException(exception);
		}
		jwksServer.createContext("/certs", exchange -> {
			exchange.getResponseHeaders().add("Content-Type", "application/json");
			exchange.sendResponseHeaders(200, jwks.length);
			try (OutputStream body = exchange.getResponseBody()) {
				body.write(jwks);
			}
		});
		jwksServer.start();
	}

	String jwksUrl() {
		return "http://localhost:" + jwksServer.getAddress().getPort() + "/certs";
	}

	void stop() {
		jwksServer.stop(0);
	}

	/**
	 * Geçerli bir token üretir; test, sınamak istediği alanı {@code customizer}
	 * ile değiştirir. Her token varsayılan olarak yeni bir kullanıcıya aittir.
	 */
	public String token(Consumer<JWTClaimsSet.Builder> customizer) {
		return sign(signingKey, customizer);
	}

	public String token() {
		return token(claims -> {
		});
	}

	/** Uygulamanın tanımadığı bir anahtarla imzalanmış, başka her yönüyle geçerli token. */
	public String tokenSignedWithUnknownKey() {
		return sign(generateKey("unknown-key"), claims -> {
		});
	}

	private static String sign(RSAKey key, Consumer<JWTClaimsSet.Builder> customizer) {
		Instant now = Instant.now();
		JWTClaimsSet.Builder claims = new JWTClaimsSet.Builder()
				.issuer(ISSUER)
				.audience(List.of(AUDIENCE, "account"))
				.subject(UUID.randomUUID().toString())
				.issueTime(Date.from(now))
				.expirationTime(Date.from(now.plusSeconds(300)))
				.claim("email", "kullanici@example.test")
				.claim("email_verified", true)
				.claim("name", "Test Kullanıcı")
				.claim("preferred_username", "testkullanici");
		customizer.accept(claims);

		SignedJWT token = new SignedJWT(
				new JWSHeader.Builder(JWSAlgorithm.RS256).keyID(key.getKeyID()).build(),
				claims.build());
		try {
			token.sign(new RSASSASigner(key));
		}
		catch (JOSEException exception) {
			throw new IllegalStateException("Test token'ı imzalanamadı", exception);
		}
		return token.serialize();
	}

	private static RSAKey generateKey(String keyId) {
		try {
			return new RSAKeyGenerator(2048).keyID(keyId).generate();
		}
		catch (JOSEException exception) {
			throw new IllegalStateException("Test anahtarı üretilemedi", exception);
		}
	}

}
