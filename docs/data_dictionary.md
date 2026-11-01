# Data Quality & Recovery Pipeline: Data Dictionary

## 1. Relational Database Tables Overview

The persistence layer is hosted on **Supabase PostgreSQL 15** and comprises 8 relational tables managed via Django ORM migrations:

| Table Name | Django Model | Purpose | Primary Key |
| :--- | :--- | :--- | :--- |
| `source_files` | `SourceFile` | Registry of uploaded datasets, SHA-256 hashes, and file sizes | `file_id` (UUID) |
| `pipeline_runs` | `PipelineRun` | Audit ledger of batch pipeline executions, yields, and durations | `run_id` (UUID) |
| `source_records` | `SourceRecord` | Granular audit trace of every raw row ingested per run | `record_id` (UUID) |
| `processed_orders` | `ProcessedOrder` | Canonical target store for validated and published records | `order_id` (VARCHAR 128) |
| `quarantine_records` | `QuarantineRecord` | Quarantine store for non-compliant records and error metadata | `quarantine_id` (UUID) |
| `correction_history` | `CorrectionHistory` | Audit trail of operator edits and payload diffs | `correction_id` (UUID) |
| `replay_history` | `ReplayHistory` | Execution history of controlled replay batches | `replay_id` (UUID) |
| `customers` | `Customer` | Optional reference master table for commercial demonstration schema | `customer_id` (VARCHAR 64) |

---

## 2. Table Schemas & Column Definitions

### 2.1 Target Canonical Store (`processed_orders`)
The target table is designed with multi-schema compatibility, storing primary keys, telemetry observations, generic event attributes, or commercial transaction fields:

| Column | Data Type | Nullable | Indexed | Description & Domain Rules |
| :--- | :--- | :---: | :---: | :--- |
| `order_id` | VARCHAR(128) | No | PK | Primary business identifier (maps to `reading_id`, `record_id`, or `order_id`). |
| `reading_id` | VARCHAR(128) | Yes | Yes | Asset telemetry reading identifier. |
| `asset_code` | VARCHAR(128) | Yes | Yes | Asset/machine code for telemetry (e.g. `ASSET-101`). |
| `metric_name` | VARCHAR(64) | Yes | Yes | Telemetry metric (`temperature`, `humidity`, `pressure`, `vibration`). |
| `metric_value`| NUMERIC(14,4) | Yes | No | Precise numeric reading value. |
| `unit` | VARCHAR(32) | Yes | No | Engineering unit (`C`, `%`, `kPa`, `mm/s`). |
| `observed_at` | TIMESTAMPTZ | Yes | Yes | Observation timestamp in UTC ISO-8601. |
| `quality_flag` | VARCHAR(32) | Yes | Yes | Reading quality classification (`GOOD`, `REVIEW`). |
| `entity_id` | VARCHAR(128) | Yes | Yes | Generic event entity identifier. |
| `event_type` | VARCHAR(64) | Yes | Yes | Event classification (`CREATED`, `UPDATED`, `COMPLETED`, `CANCELLED`). |
| `amount` | NUMERIC(14,2) | Yes | No | Financial or numerical magnitude. Must be `>= 0.00`. |
| `quantity` | INTEGER | Yes | No | Count of items or units. Must be a positive integer `>= 1`. |
| `event_timestamp`| TIMESTAMPTZ | Yes | Yes | Event timestamp in UTC ISO-8601. |
| `status` | VARCHAR(32) | Yes | Yes | Lifecycle status (`ACTIVE`, `COMPLETED`, `CANCELLED`, `GOOD`, `REVIEW`). |
| `customer_id` | VARCHAR(64) | Yes | Yes | FK referencing `customers.customer_id` (optional commercial schema). |
| `product_name`| VARCHAR(255) | Yes | No | Description or item name. Extra whitespace stripped. |
| `unit_price` | NUMERIC(12,2) | Yes | No | Unit financial value. Must be `>= 0.00`. |
| `total_amount`| NUMERIC(14,2) | Yes | No | Total amount. In commercial schema, equals `quantity * unit_price`. |
| `order_date` | TIMESTAMPTZ | Yes | Yes | Transaction timestamp in UTC ISO-8601. |
| `order_status`| VARCHAR(32) | Yes | Yes | Commercial status (`PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`). |
| `source_file` | VARCHAR(255) | No | No | Originating source file name. |
| `source_row_number` | INTEGER | No | No | 1-indexed row number in source file. |
| `run_id` | UUID | No | Yes | Reference to pipeline run execution. |
| `raw_payload` | JSONB | Yes | No | Complete raw record payload before transformation. |
| `processed_at`| TIMESTAMPTZ | No | Yes | UTC timestamp when record was published to database. |
| `created_at` | TIMESTAMPTZ | No | No | Database row creation timestamp. |
| `updated_at` | TIMESTAMPTZ | No | No | Database row update timestamp. |

### 2.2 Quarantine Store (`quarantine_records`)

| Column | Data Type | Nullable | Indexed | Description & Domain Rules |
| :--- | :--- | :---: | :---: | :--- |
| `quarantine_id` | UUID | No | PK | Unique identifier generated for the quarantined record. |
| `record_id` | VARCHAR(128) | No | Yes | Source identifier or synthetic fallback `GEN-XXXXXXXX`. |
| `source_file` | VARCHAR(255) | No | Yes | Source file where the rejection occurred. |
| `source_row_number` | INTEGER | No | Yes | Exact row number in source file for debugging. |
| `run_id` | UUID | No | Yes | Pipeline run ID during which quarantine occurred. |
| `raw_record` | JSONB | No | No | Verbatim raw source payload as received. |
| `corrected_record` | JSONB | Yes | No | Operator-corrected JSON payload (null until edited). |
| `error_code` | VARCHAR(64) | No | Yes | Primary classification error code. |
| `error_reason` | TEXT | No | No | Human-readable explanation of validation failure(s). |
| `validation_stage` | VARCHAR(32) | No | No | Validation failure stage: `SCHEMA`, `BUSINESS`, or `SYSTEM`. |
| `validation_errors` | JSONB | No | No | Array of all error objects: `[{error_code, error_reason, validation_stage, field_name}]`. |
| `status` | VARCHAR(32) | No | Yes | Current state: `PENDING`, `CORRECTED`, `REPLAYED`, `FAILED`. |
| `attempt_count` | INTEGER | No | No | Replay attempt counter (increments on every replay attempt). |
| `created_at` | TIMESTAMPTZ | No | Yes | Timestamp record was quarantined. |
| `updated_at` | TIMESTAMPTZ | No | No | Timestamp of latest operator edit or status change. |
| `replayed_at` | TIMESTAMPTZ | Yes | No | UTC timestamp when successfully replayed. |

### 2.3 Correction Audit History (`correction_history`)

| Column | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `correction_id` | UUID | No | Primary Key for audit history entry. |
| `quarantine_record_id` | UUID | No | FK referencing `quarantine_records.quarantine_id` (`ON DELETE CASCADE`). |
| `previous_payload` | JSONB | No | State of record immediately prior to edit. |
| `corrected_payload` | JSONB | No | State of record immediately after edit. |
| `changed_fields` | JSONB | No | Structured diff: `{"field_name": {"old": ..., "new": ...}}`. |
| `corrected_by` | VARCHAR(128) | No | Operator username or identifier (`operator`). |
| `correction_notes` | TEXT | Yes | Operator reasoning or justification for edit. |
| `created_at` | TIMESTAMPTZ | No | Timestamp when correction was committed. |

### 2.4 Pipeline Execution Runs (`pipeline_runs`)

| Column | Data Type | Nullable | Description |
| :--- | :--- | :---: | :--- |
| `run_id` | UUID | No | Primary Key for the execution run. |
| `source_file_id` | UUID | Yes | FK referencing `source_files.file_id`. |
| `filename` | VARCHAR(255) | No | File name processed. |
| `start_time` | TIMESTAMPTZ | No | Run initialization timestamp. |
| `end_time` | TIMESTAMPTZ | Yes | Run completion timestamp. |
| `total_records` | INTEGER | No | Total rows ingested from source file. |
| `valid_records` | INTEGER | No | Count of records passing all validation checks. |
| `rejected_records` | INTEGER | No | Count of records rejected into quarantine. |
| `execution_duration` | FLOAT | No | Total elapsed execution duration in seconds. |
| `run_status` | VARCHAR(32) | No | Status: `RUNNING`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`. |
| `failure_reason` | TEXT | Yes | Error message if run terminated unexpectedly. |
| `metadata` | JSONB | No | Run metadata: `schema_detected`, `id_column`, `file_hash`, `file_size_bytes`. |

---

## 3. Error Code Taxonomy

| Error Code | Stage | Trigger Condition | Example Error Reason |
| :--- | :---: | :--- | :--- |
| `ERR_MISSING_FIELD` | SCHEMA | Mandatory column missing from payload. | `Required column 'reading_id' is missing from record.` |
| `ERR_NULL_VALUE` | SCHEMA | Column exists but value is null or empty whitespace. | `Column 'asset_code' must not be null or empty.` |
| `ERR_INVALID_TYPE` | SCHEMA | Value cannot be parsed into required numeric or integer type. | `Metric value 'bad-value' is not a valid decimal number.` |
| `ERR_INVALID_DATE_FORMAT` | SCHEMA | Timestamp cannot be parsed as valid ISO-8601 with time component. | `Observed timestamp 'bad-timestamp' is not a valid timestamp.` |
| `ERR_DUPLICATE_RECORD_ID` | BUSINESS | Identifier already observed within the current ingestion batch. | `Duplicate reading_id 'READ-B-00901' found in current batch.` |
| `ERR_INVALID_METRIC_NAME` | BUSINESS | Telemetry metric name is not in supported list. | `Metric name 'unknown_metric' is invalid. Allowed: humidity, pressure, temperature, vibration.` |
| `ERR_INVALID_UNIT` | BUSINESS | Telemetry unit does not match the metric type. | `Invalid unit 'psi' for metric 'pressure'. Expected 'kPa'.` |
| `ERR_INVALID_BOUNDARY` | BUSINESS | Value is outside allowable physical or engineering limits. | `Metric value 109.00 exceeds allowable maximum of 100.0 for humidity.` |
| `ERR_INVALID_STATUS` | BUSINESS | Status or quality flag is not in configured enumeration. | `Quality flag 'UNKNOWN' is invalid. Allowed: GOOD, REVIEW.` |
| `ERR_INVALID_DATE_RANGE` | BUSINESS | Timestamp year is outside valid operational era (2000–2100). | `Observed timestamp '1995-01-01' is outside allowable range (2000-2100).` |
| `ERR_INVALID_QUANTITY` | BUSINESS | Quantity integer is less than or equal to zero. | `Quantity must be greater than zero. Received: 0.` |
| `ERR_INVALID_PRICE` | BUSINESS | Price or amount is negative. | `Amount must be greater than or equal to zero. Received: -25.00.` |
| `ERR_CALCULATION_MISMATCH`| BUSINESS | Total amount does not equal `quantity * unit_price`. | `Total amount mismatch: expected 100.00, received 115.50.` |
| `ERR_INVALID_FK` | BUSINESS | Referenced foreign key ID does not exist in master table. | `Customer ID 'NONEXISTENT-9999' does not exist in customers master table.` |
