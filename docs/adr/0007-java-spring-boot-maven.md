# ADR-0007: Java ve Spring Boot Sürümleri, Derleme Aracı

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-03

## Bağlam

Şartname backend için Spring Boot kullanılmasını sabit tutmakta; Java ve Spring Boot sürümlerini ve derleme aracını geliştiriciye bırakmaktadır.

Sürüm seçiminde şunlar gözetilmiştir:

- Seçilen sürümlerin proje süresince güvenlik yaması almaya devam etmesi.
- Depoyu ilk kez gören birinin uygulamayı ek bilgiye ihtiyaç duymadan kurabilmesi (FOG-38).

Spring Boot 4.1 serisi en az Java 17 gerektirmekte ve Java 27'ye kadar olan sürümlerle uyumlu olmaktadır. Derleme aracı olarak Maven 3.6.3 ve üstü ile Gradle 8.14 ve üstü desteklenmektedir.

## Değerlendirilen Seçenekler

### Java sürümü

Java'da uzun süreli destek (LTS) sürümleri iki yılda bir yayımlanır; ara sürümler yalnızca altı ay destek alır. Bu nedenle yalnızca LTS sürümleri değerlendirilmiştir.

**Java 21 (Eylül 2023)**

- Artı: Daha uzun süredir kullanımdadır; örneklerin ve kütüphanelerin büyük çoğunluğu bu sürümle test edilmiştir.
- Eksi: Daha eski olduğundan destek süresi Java 25'ten önce sona erer.

**Java 25 (Eylül 2025)**

- Artı: En güncel LTS sürümüdür; destek süresi daha uzundur.
- Artı: Yayımlanmasının üzerinden bir yıl geçtiğinden araç ve kütüphane desteği olgunlaşmıştır.
- Eksi: Örneklerin bir kısmı daha eski sürümlere aittir.

### Spring Boot sürümü

**3.5.x**

- Artı: Daha fazla örnek ve kaynak bulunmaktadır.
- Eksi: Açık kaynak desteği Haziran 2026'da sona ermiştir; desteği bitmiş bir sürümle yeni projeye başlanmış olur.

**4.1.x**

- Artı: Güncel kararlı seridir ve açık kaynak desteği devam etmektedir.
- Eksi: Daha yeni olduğundan örneklerin bir kısmı 3.x serisine aittir.

### Derleme aracı

**Maven**

- Artı: XML tabanlı, bildirimsel bir yapılandırması vardır; proje yapısı ve yaşam döngüsü her projede aynıdır, öğrenmesi daha kolaydır.
- Artı: Spring ekosisteminde yaygın olarak kullanılır.
- Eksi: Gradle'a göre daha yavaştır ve daha az esnektir.

**Gradle**

- Artı: Artımlı derleme ve önbellek sayesinde daha hızlıdır; Kotlin veya Groovy ile yazılan yapılandırması esnektir.
- Eksi: Esneklik, yapılandırmanın her projede farklı yazılabilmesi anlamına gelir; öğrenmesi daha zordur.
- Eksi: Hız ve esneklik avantajları, çok modüllü büyük projelerde belirginleşir.

## Karar

- **Java 25** kullanılacaktır.
- **Spring Boot 4.1.x** kullanılacaktır. Kesin yama sürümü, proje oluşturulurken o tarihteki en güncel 4.1 yama sürümü olarak seçilecek ve derleme dosyasında sabitlenecektir.
- Derleme aracı olarak **Maven** kullanılacaktır. Projeye **Maven Wrapper** (`mvnw`) eklenecek ve Maven sürümü wrapper yapılandırmasında sabitlenecektir.

Maven'ın tercih edilmesinin nedeni, projenin tek bir backend uygulamasından oluşmasıdır (ADR-0005). Gradle'ın hız ve esneklik avantajları bu ölçekte belirgin değildir; Maven'ın sade ve standart yapısı ise derleme yapılandırmasının anlaşılmasını ve anlatılmasını kolaylaştırır.

## Sonuçlar

- Uygulamayı kurmak için Java 25'in kurulu olması gerekir. Maven Wrapper, doğru Maven sürümünü kendisi indirdiğinden ayrıca Maven kurulmasına gerek yoktur. Bu gereksinimler README'de belirtilecektir.
- Geliştirme ortamında Java 25, Ubuntu depolarındaki OpenJDK paketiyle kurulmuştur. `JAVA_HOME`, update-alternatives ile seçilen Java sürümüne göre belirlenmektedir.
- Konteyner imajında kullanılacak Java temel imajı, dağıtım kararlarında belirlenecektir.
- Projenin Spring Boot 4.1'in açık kaynak destek süresi içinde tamamlanması öngörülmektedir; bu süre aşılırsa yükseltme değerlendirilecektir.

## Kaynaklar

- Spring Boot sistem gereksinimleri: https://docs.spring.io/spring-boot/4.1.2/system-requirements.html
- Spring Boot destek takvimi: https://spring.io/projects/spring-boot#support