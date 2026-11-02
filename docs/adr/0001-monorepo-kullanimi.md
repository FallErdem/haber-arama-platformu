# ADR-0001: Monorepo Kullanımı

- **Durum:** Kabul edildi
- **Tarih:** 2026-11-02

## Bağlam

Proje; Spring Boot backend, React frontend, Kubernetes yapılandırmaları ve proje dokümanlarından oluşmaktadır. Proje tek geliştirici tarafından yürütülmektedir. İlerleme GitHub üzerinden takip edilmekte ve değerlendirme ekibi commit geçmişini, iş takip panosunu ve kod incelemelerini GitHub'da görmektedir.

## Değerlendirilen Seçenekler

### 1. Monorepo

- Artı: Tüm ilerleme tek bir commit geçmişinde ve tek bir iş takip panosunda görünür.
- Artı: Backend ve frontend'i birlikte etkileyen bir değişiklik tek bir pull request'te yapılabilir.
- Artı: CI yapılandırması, dokümanlar ve ortak ayarlar tek yerde durur.
- Eksi: CI'da yalnızca değişen parçanın testlerini çalıştırmak için yol filtreleri gerekir.
- Eksi: Depo zamanla büyür; parçalar bağımsız sürümlenemez.

### 2. Polyrepo

- Artı: Her parça bağımsız sürümlenir ve dağıtılır.
- Artı: Depo bazında farklı erişim yetkileri verilebilir.
- Eksi: Birden fazla parçayı etkileyen değişiklikler birden fazla depoya dağılır ve birlikte takip edilmesi zorlaşır.
- Eksi: Değerlendirme ekibinin ilerlemeyi birden fazla depodan takip etmesi gerekir.
- Eksi: CI yapılandırması ve ortak ayarlar her depoda tekrar edilir.

## Karar

Monorepo kullanılacaktır. Polyrepo'nun sağladığı bağımsız sürümleme ve depo bazında yetkilendirme, birden fazla ekibin aynı ürün üzerinde çalıştığı durumlarda değerlidir. Tek geliştiricili bu projede bu avantajlar kullanılmayacak, buna karşılık takip ve koordinasyon maliyeti oluşacaktır.

## Sonuçlar

- Değerlendirme ekibi tüm ilerlemeyi tek depodan izleyebilir.
- Parçalar arası değişiklikler tek commit veya pull request içinde tutarlı şekilde yapılabilir.
- CI iş akışlarında yol bazlı filtreler tanımlanacaktır
- Depo içi klasör yapısı mimari dokümanında belirlenecektir.