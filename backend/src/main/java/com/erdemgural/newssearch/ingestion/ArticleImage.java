package com.erdemgural.newssearch.ingestion;

/**
 * Arayüze verilen bir görsel. {@code url}, görsel uç noktasının imzalı ve süreli adresidir
 * (API sözleşmesi 4.4); token gerektirmeden {@code <img>} etiketinde kullanılabilir.
 */
public record ArticleImage(String url, int width, int height) {}
