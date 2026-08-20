# Data Model

Use PostgreSQL, UUID primary keys, `timestamptz`, and Alembic.

Below is the required logical model. Exact column naming may be adapted, but semantics must be preserved.

## users
- id
- email (unique, normalized)
- password_hash
- display_name
- is_active
- created_at
- updated_at

## refresh_sessions
- id
- user_id
- token_hash
- family_id
- expires_at
- revoked_at
- replaced_by_id nullable
- user_agent nullable
- ip_hash nullable
- created_at

## workspaces
- id
- name
- slug
- created_by_user_id
- created_at
- updated_at

## workspace_members
- workspace_id
- user_id
- role enum: owner/admin/member/viewer
- created_at
Unique(workspace_id, user_id)

## processor_templates
System-seeded optional presets.
- id
- key
- name
- description
- schema_json
- instructions
- validation_config
- review_config
- is_active

## processors
- id
- workspace_id
- name
- description
- status enum draft/active/archived
- latest_version_id nullable
- created_by_user_id
- created_at
- updated_at
- archived_at nullable

## processor_versions
Immutable after publishing.
- id
- processor_id
- version_number
- state enum draft/published
- schema_json JSONB
- instructions TEXT
- validation_config JSONB
- review_config JSONB
- extraction_config JSONB
- created_by_user_id
- created_at
- published_at nullable
Unique(processor_id, version_number)

## documents
- id
- workspace_id
- original_filename
- mime_type
- file_size
- sha256
- object_key
- status
- selected_processor_id nullable
- selected_processor_version_id nullable
- page_count nullable
- detected_type nullable
- error_code nullable
- error_message_safe nullable
- uploaded_by_user_id nullable
- source enum ui/api
- created_at
- updated_at
- deleted_at nullable

Indexes:
- workspace_id, created_at
- workspace_id, status
- sha256

## document_status_events
- id
- document_id
- from_status nullable
- to_status
- message nullable
- metadata_json
- created_at

## processing_jobs
- id
- workspace_id
- document_id
- job_type enum parse/extract/validate/webhook/export
- status enum queued/running/succeeded/failed/retrying/cancelled
- idempotency_key unique
- celery_task_id nullable
- attempt
- started_at nullable
- finished_at nullable
- error_code nullable
- error_message_safe nullable
- created_at

## parse_runs
- id
- document_id
- parser_name
- parser_version nullable
- status
- canonical_storage enum database/object_storage
- canonical_json JSONB nullable
- canonical_object_key nullable
- markdown_object_key nullable
- page_assets_prefix nullable
- metadata_json
- started_at
- finished_at nullable
- created_at

## extraction_runs
Immutable model output.
- id
- document_id
- processor_version_id
- parse_run_id
- provider
- model
- prompt_version
- status
- raw_data JSONB
- provider_metadata JSONB
- input_hash
- latency_ms nullable
- input_tokens nullable
- output_tokens nullable
- cost_estimate nullable
- error_code nullable
- error_message_safe nullable
- created_at
- finished_at nullable

## extraction_fields
Materialized leaves for review/search/evidence.
- id
- extraction_run_id
- json_path
- field_label nullable
- value_json JSONB
- normalized_value_text nullable
- value_type nullable
- confidence nullable
- confidence_level nullable
- validation_state enum passed/warning/failed/not_run
- review_state enum pending/approved/rejected/corrected
- created_at

Unique(extraction_run_id, json_path)

For arrays, paths may include indices such as `$.line_items[0].amount`.

## field_evidence
- id
- extraction_field_id
- page_number nullable
- block_ids JSONB
- bbox JSONB nullable
- source_text nullable
- evidence_strength nullable
- parser_confidence nullable
- model_self_confidence nullable
- created_at

Multiple evidence entries per field allowed.

## validation_results
- id
- extraction_run_id
- extraction_field_id nullable
- rule_key
- scope enum field/document
- severity enum info/warning/error
- passed
- message
- metadata_json
- created_at

## review_overrides
Never mutate model output.
- id
- document_id
- extraction_run_id
- json_path
- original_value JSONB
- override_value JSONB
- action enum correct/approve/reject/reset
- note nullable
- reviewer_user_id
- created_at

## document_approvals
- id
- document_id
- extraction_run_id
- approved_by_user_id
- approved_at
- note nullable

## api_keys
- id
- workspace_id
- name
- key_prefix
- key_hash
- expires_at nullable
- last_used_at nullable
- revoked_at nullable
- created_by_user_id
- created_at

## webhooks
- id
- workspace_id
- name
- url
- secret_encrypted_or_managed
- events JSONB
- enabled
- created_by_user_id
- created_at
- updated_at

If application encryption is implemented, use a configured master key. Never expose secret again after creation if avoidable.

## webhook_deliveries
- id
- webhook_id
- event_id
- event_type
- payload JSONB
- status
- attempt
- response_status nullable
- response_excerpt nullable
- next_attempt_at nullable
- created_at
- delivered_at nullable

## workflow_rules
- id
- workspace_id
- name
- enabled
- processor_id nullable
- trigger
- conditions JSONB
- actions JSONB
- created_at
- updated_at

## audit_events
- id
- workspace_id
- actor_user_id nullable
- actor_api_key_id nullable
- action
- target_type
- target_id nullable
- metadata_json
- created_at

## usage_events
For future billing/analytics.
- id
- workspace_id
- document_id nullable
- event_type
- quantity
- unit
- metadata_json
- created_at

Examples:
- pages_parsed
- llm_input_tokens
- llm_output_tokens
- document_processed
- storage_bytes
