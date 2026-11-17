package com.erdemgural.newssearch.search.internal;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Arama ifadesinin parçaları: tırnak içinde yazılmış kelime öbekleri ve geri kalan kelimeler.
 *
 * <p>Kullanıcı bir öbeği tırnak içinde yazarsa ({@code "merkez bankası" faiz}) yalnızca o öbeği
 * kelimeleri yan yana ve aynı sırada içeren haberler döner. Tırnak dışındaki kelimeler normal
 * kurallarla aranır.
 *
 * @param phrases tırnak içindeki öbekler; boş öbekler alınmaz
 * @param words tırnak dışında kalan kelimeler, aralarında birer boşlukla; yoksa boş metin
 */
record SearchText(List<String> phrases, String words) {

    /**
     * Düz tırnak ({@code "}) ve telefon klavyelerinin ürettiği eğik tırnaklar ({@code “ ”}) aynı
     * sayılır. Kapanmayan tırnak öbek oluşturmaz; işaret atılır, kelimeler normal aranır.
     */
    private static final Pattern PHRASE = Pattern.compile("[\"“”]([^\"“”]*)[\"“”]");

    private static final Pattern QUOTE = Pattern.compile("[\"“”]");
    private static final Pattern SPACES = Pattern.compile("\\s+");

    static SearchText parse(String query) {
        List<String> phrases = new ArrayList<>();
        Matcher matcher = PHRASE.matcher(query);
        StringBuilder rest = new StringBuilder();
        while (matcher.find()) {
            String phrase = normalizeSpaces(matcher.group(1));
            if (!phrase.isEmpty()) {
                phrases.add(phrase);
            }
            matcher.appendReplacement(rest, " ");
        }
        matcher.appendTail(rest);
        String words = normalizeSpaces(QUOTE.matcher(rest).replaceAll(" "));
        return new SearchText(List.copyOf(phrases), words);
    }

    /** İfadede aranacak bir şey kalmadıysa (örneğin yalnızca {@code ""} yazıldıysa) true. */
    boolean isEmpty() {
        return phrases.isEmpty() && words.isEmpty();
    }

    private static String normalizeSpaces(String text) {
        return SPACES.matcher(text).replaceAll(" ").strip();
    }
}
