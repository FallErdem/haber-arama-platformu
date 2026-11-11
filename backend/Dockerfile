# Spring Boot API imajı. Derleme bağlamı deponun köküdür, çünkü geçiş betikleri
# backend/ dışında, db/migrations/ altındadır (ADR-0018):
#
#   docker build -f backend/Dockerfile -t <imaj adı> .

# ---- 1. aşama: derleme (JDK ve Maven burada kalır, son imaja girmez) ----
FROM eclipse-temurin:25.0.4.1_1-jdk-noble AS build
WORKDIR /workspace/backend

COPY backend/.mvn .mvn
COPY backend/mvnw backend/pom.xml ./
COPY backend/src src
# pom.xml betikleri ../db/migrations yolundan okur.
COPY db/migrations /workspace/db/migrations

# Testler burada çalıştırılmaz: Testcontainers Docker ister; testler ./mvnw verify
# ile (ve CI'da) çalışır. İndirilen bağımlılıklar derlemeler arasında önbellekte tutulur.
RUN --mount=type=cache,target=/root/.m2 ./mvnw --batch-mode -DskipTests package

# ---- 2. aşama: çalışma (yalnızca JRE ve uygulamanın jar dosyası) ----
FROM eclipse-temurin:25.0.4.1_1-jre-noble
WORKDIR /app

COPY --from=build /workspace/backend/target/newssearch-*.jar app.jar

# Uygulama root olarak çalışmaz.
USER 1000:1000
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
