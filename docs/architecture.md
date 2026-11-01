# Data Quality & Recovery Pipeline: Architecture

## 1. System Overview

The **Data Quality & Recovery Pipeline** is an enterprise-grade, multi-schema data engineering application designed to ingest structured datasets, enforce strict schema and business rule validation, quarantine non-compliant records, and provide controlled, selective recovery without reprocessing previously successful records.

The pipeline is completely domain-agnostic, supporting multiple data schemas (including Generic Events, Industrial IoT Asset Telemetry, and Commercial Transaction records) through a centralized, configurable **Schema Registry**.

### High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph UI ["Client Layer (React 19 + Vite + TailwindCSS 4)"]
        DASH["Operations Dashboard"]
        INGEST["Data Ingestion & File Upload"]
        QUAR["Quarantine Store & Correction Modal"]
        REPLAY["Controlled Replay Engine UI"]
        RECS["Canonical Target Store Browser"]
        RUNS["Execution Audit Ledger"]
    end

    subgraph API ["API & Service Layer (Django 5.1 + Django REST Framework)"]
        REST["REST API Endpoints (/api/...)"]
        
        subgraph ENGINE ["Data Pipeline Engine"]
            DETECT["Dynamic Schema Detection"]
            REGISTRY["Configurable Schema Registry"]
            VAL_SCHEMA["Schema Validator (Types & Nullability)"]
            VAL_BIZ["Business Validator (Domain & Boundary Rules)"]
            DEDUP["In-Batch Duplicate Detector"]
            TRANSFORM["Transformer & Canonical Normalizer"]
            PUB["Idempotent PostgreSQL Publisher"]
            QM["Quarantine Manager & Error Ledger"]
            RE["Controlled Replay Engine"]
        end
    end

    subgraph DB ["Target Persistence Layer: Supabase PostgreSQL 15"]
        T_FILES[("source_files")]
        T_RUNS[("pipeline_runs")]
        T_RAW[("source_records - Raw Audit")]
        T_PUB[("processed_orders - Target Store")]
        T_QUAR[("quarantine_records - Quarantine Store")]
        T_HIST[("correction_history - Audit Trail")]
        T_REPLAY[("replay_history - Replay Ledger")]
    end

    UI -->|"REST / JSON & Multipart"| REST
    REST --> ENGINE
    DETECT --> REGISTRY
    REGISTRY --> VAL_SCHEMA
    VAL_SCHEMA --> VAL_BIZ
    VAL_BIZ --> DEDUP
    
    DEDUP -->|"Valid Records"| TRANSFORM
    TRANSFORM --> PUB
    PUB -->|"Atomic Upsert"| T_PUB

    VAL_SCHEMA -->|"Schema Errors"| QM
    VAL_BIZ -->|"Business Rule Violations"| QM
    DEDUP -->|"Duplicate Business Keys"| QM
    QM --> T_QUAR

    RE -->|"Atomic Claim - Row Lock"| T_QUAR
    RE -->|"Strict Re-Validation"| VAL_SCHEMA
    RE -->|"Re-Validated Records"| PUB
    RE --> T_HIST
    RE --> T_REPLAY

    ENGINE --> T_FILES
    ENGINE --> T_RUNS
    ENGINE --> T_RAW
```

---

## 2. Ingestion & Validation Pipeline Workflow

1. **File Ingestion & Fingerprinting**:
   - Accepts CSV and JSON payloads via `POST /api/ingestion/upload/`.
   - Generates deterministic SHA-256 fingerprint to ensure file integrity and prevent redundant storage.
   - Registers entry in `source_files` table with file metadata and size.

2. **Dynamic Schema Detection**:
   - Inspects file headers without hardcoded assumptions.
   - Matches column sets against the `SchemaRegistry` to automatically bind the correct schema definition:
     - **Asset Telemetry**: `reading_id`, `asset_code`, `metric_name`, `metric_value`, `unit`, `observed_at`, `quality_flag`
     - **Generic Events**: `record_id`, `entity_id`, `event_type`, `amount`, `quantity`, `event_timestamp`, `status`
     - **Transaction Records**: `order_id`, `customer_id`, `product_name`, `quantity`, `unit_price`, `total_amount`, `order_date`, `order_status`

3. **In-Batch Duplicate Detection**:
   - Enforces uniqueness on the active schema's unique identifier (`reading_id`, `record_id`, or `order_id`).
   - Allows repeated domain entity codes (e.g., repeated `asset_code` values are valid time-series observations).
   - Flags duplicates immediately with `ERR_DUPLICATE_RECORD_ID`.

4. **Two-Stage Validation Engine**:
   - **Schema Validation**: Verifies mandatory fields, non-null constraints, data types (integer, decimal, timestamp, date), and ISO-8601 formatting.
   - **Business Rule Validation**: Enforces numerical boundaries (e.g., humidity `0–100%`, vibration `>= 0`), metric-specific unit matching (e.g., pressure must be `kPa`, not `psi`), status enums, date range boundaries (2000–2100), and calculation integrity.

5. **Deterministic Bifurcation**:
   - **Valid Stream**: Transformed into canonical UTC ISO-8601 timestamps and precise decimal types, then bulk upserted into `processed_orders`.
   - **Quarantine Stream**: Captured verbatim with raw payload, source file, source row number, and structured error breakdown into `quarantine_records`.

---

## 3. Controlled Selective Replay Architecture

The foundational recovery guarantee is that **previously successful records are never reprocessed during recovery operations**.

```mermaid
stateDiagram-v2
    [*] --> Ingested: Raw File Received
    Ingested --> Validated: Validation Engine
    
    Validated --> Published: Validation Passed
    Published --> [*]: Canonical Target Store

    Validated --> Quarantine_Pending: Validation Failed
    
    Quarantine_Pending --> Quarantine_Corrected: Operator Edits in UI
    
    state "Controlled Replay Execution" as ReplayOp {
        Quarantine_Corrected --> Atomic_Claim: Atomic Claim - Row Lock
        Atomic_Claim --> Re_Validate: Full Schema & Business Re-Validation
        Re_Validate --> Replay_Success: All Rules Pass
        Re_Validate --> Replay_Fail: Flaws Persist
    }

    Replay_Success --> Published: Idempotent Target Upsert
    Replay_Success --> Quarantine_Replayed: Marked REPLAYED
    Quarantine_Replayed --> [*]: Audit Preserved

    Replay_Fail --> Quarantine_Failed: Marked FAILED
    Quarantine_Failed --> Quarantine_Corrected: Operator Re-Edits
```

### Recovery Guarantees:
1. **Strict Selection**: Replay queries only target records with `status = 'CORRECTED'`. Records already in `REPLAYED` or untouched `PENDING` status are ignored.
2. **Atomic Concurrency Protection**: Uses `select_for_update(skip_locked=True)` within Django `transaction.atomic()` blocks to prevent double-claiming by concurrent workers.
3. **Audit Immutability**: Every edit appends a full diff record to `correction_history` documenting changed fields, previous values, new values, operator ID, and timestamp.
4. **Target Idempotency**: Target store insertions utilize PostgreSQL `ON CONFLICT (order_id) DO UPDATE` to ensure zero duplicates upon replay.
