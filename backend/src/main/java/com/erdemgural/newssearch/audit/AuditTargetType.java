package com.erdemgural.newssearch.audit;

/** Audit kaydında işlemin yapıldığı nesnenin türü ({@code audit_events.target_type}). */
public enum AuditTargetType {
    USER,
    SOURCE,
    FEED,
    ARTICLE
}
