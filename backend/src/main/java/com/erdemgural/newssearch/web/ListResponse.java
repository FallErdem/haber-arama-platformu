package com.erdemgural.newssearch.web;

import java.util.List;

/**
 * Sayfalanmayan listelerin yanıtı (API sözleşmesi 2.4). Öğeler doğrudan bir dizi olarak değil,
 * sayfalı listelerdeki gibi {@code items} alanında döner: arayüz bütün listeleri aynı biçimde
 * okur ve yanıta sonradan alan eklemek var olan arayüzü bozmaz.
 */
public record ListResponse<T>(List<T> items) {}
