"""initial schema

Revision ID: 1342c34cea7a
Revises: 
Create Date: 2026-10-19 03:45:56.676095
"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

revision: str = '1342c34cea7a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('faskes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('integration_mode', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('region', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_faskes'))
    )
    op.create_table('risk_vector',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_risk_vector')),
    sa.UniqueConstraint('code', name=op.f('uq_risk_vector_code'))
    )
    op.create_table('app_user',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_app_user_faskes_id_faskes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_app_user')),
    sa.UniqueConstraint('email', name=op.f('uq_app_user_email'))
    )
    op.create_index(op.f('ix_app_user_faskes_id'), 'app_user', ['faskes_id'], unique=False)
    op.create_table('evidence_source',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('source_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('system_ref', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_evidence_source_faskes_id_faskes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evidence_source'))
    )
    op.create_index(op.f('ix_evidence_source_faskes_id'), 'evidence_source', ['faskes_id'], unique=False)
    op.create_table('rule_set',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('vector_id', sa.Uuid(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['vector_id'], ['risk_vector.id'], name=op.f('fk_rule_set_vector_id_risk_vector')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rule_set'))
    )
    op.create_index(op.f('ix_rule_set_vector_id'), 'rule_set', ['vector_id'], unique=False)
    op.create_table('audit_log',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('entity_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('entity_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('actor_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('prev_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('record_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['app_user.id'], name=op.f('fk_audit_log_actor_id_app_user')),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_audit_log_faskes_id_faskes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_log'))
    )
    op.create_index(op.f('ix_audit_log_actor_id'), 'audit_log', ['actor_id'], unique=False)
    op.create_index('ix_audit_log_entity_type_entity_id', 'audit_log', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_audit_log_faskes_id_created_at', 'audit_log', ['faskes_id', 'created_at'], unique=False)
    op.create_table('claim',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('episode_no', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('patient_pseudonym', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('inacbgb_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('submitted_by', sa.Uuid(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locked_by', sa.Uuid(), nullable=True),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_claim_faskes_id_faskes')),
    sa.ForeignKeyConstraint(['locked_by'], ['app_user.id'], name=op.f('fk_claim_locked_by_app_user')),
    sa.ForeignKeyConstraint(['submitted_by'], ['app_user.id'], name=op.f('fk_claim_submitted_by_app_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_claim'))
    )
    op.create_index('ix_claim_faskes_id_episode_no', 'claim', ['faskes_id', 'episode_no'], unique=False)
    op.create_index(op.f('ix_claim_locked_by'), 'claim', ['locked_by'], unique=False)
    op.create_index(op.f('ix_claim_submitted_by'), 'claim', ['submitted_by'], unique=False)
    op.create_table('policy_version',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('config_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['approved_by'], ['app_user.id'], name=op.f('fk_policy_version_approved_by_app_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_policy_version')),
    sa.UniqueConstraint('version', name=op.f('uq_policy_version_version'))
    )
    op.create_index(op.f('ix_policy_version_approved_by'), 'policy_version', ['approved_by'], unique=False)
    op.create_table('rule_version',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('rule_set_id', sa.Uuid(), nullable=False),
    sa.Column('version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('approved_by', sa.Uuid(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['approved_by'], ['app_user.id'], name=op.f('fk_rule_version_approved_by_app_user')),
    sa.ForeignKeyConstraint(['rule_set_id'], ['rule_set.id'], name=op.f('fk_rule_version_rule_set_id_rule_set')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rule_version')),
    sa.UniqueConstraint('rule_set_id', 'version', name=op.f('uq_rule_version_rule_set_id'))
    )
    op.create_index(op.f('ix_rule_version_approved_by'), 'rule_version', ['approved_by'], unique=False)
    op.create_table('claim_code',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('claim_id', sa.Uuid(), nullable=False),
    sa.Column('code_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('position', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['claim_id'], ['claim.id'], name=op.f('fk_claim_code_claim_id_claim')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_claim_code'))
    )
    op.create_index(op.f('ix_claim_code_claim_id'), 'claim_code', ['claim_id'], unique=False)
    op.create_index(op.f('ix_claim_code_code'), 'claim_code', ['code'], unique=False)
    op.create_table('evidence_item',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('source_id', sa.Uuid(), nullable=False),
    sa.Column('claim_id', sa.Uuid(), nullable=False),
    sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('content_text', sa.Text(), nullable=True),
    sa.Column('content_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=True),
    sa.Column('content_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['claim_id'], ['claim.id'], name=op.f('fk_evidence_item_claim_id_claim')),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_evidence_item_faskes_id_faskes')),
    sa.ForeignKeyConstraint(['source_id'], ['evidence_source.id'], name=op.f('fk_evidence_item_source_id_evidence_source')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evidence_item'))
    )
    op.create_index('ix_evidence_item_claim_id_recorded_at', 'evidence_item', ['claim_id', 'recorded_at'], unique=False)
    op.create_index(op.f('ix_evidence_item_content_hash'), 'evidence_item', ['content_hash'], unique=False)
    op.create_index('ix_evidence_item_embedding_hnsw', 'evidence_item', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'}, postgresql_with={'m': 16, 'ef_construction': 64})
    op.create_index(op.f('ix_evidence_item_faskes_id'), 'evidence_item', ['faskes_id'], unique=False)
    op.create_index(op.f('ix_evidence_item_source_id'), 'evidence_item', ['source_id'], unique=False)
    op.create_table('expected_rule',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('rule_version_id', sa.Uuid(), nullable=False),
    sa.Column('code_pattern', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('expected_evidence_spec', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.ForeignKeyConstraint(['rule_version_id'], ['rule_version.id'], name=op.f('fk_expected_rule_rule_version_id_rule_version')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_expected_rule'))
    )
    op.create_index(op.f('ix_expected_rule_rule_version_id'), 'expected_rule', ['rule_version_id'], unique=False)
    op.create_table('investigation_job',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('claim_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('attempt_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('idempotency_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['claim_id'], ['claim.id'], name=op.f('fk_investigation_job_claim_id_claim')),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_investigation_job_faskes_id_faskes')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_investigation_job')),
    sa.UniqueConstraint('faskes_id', 'idempotency_key', name=op.f('uq_investigation_job_faskes_id'))
    )
    op.create_index(op.f('ix_investigation_job_claim_id'), 'investigation_job', ['claim_id'], unique=False)
    op.create_index('ix_investigation_job_status_created_at', 'investigation_job', ['status', 'created_at'], unique=False)
    op.create_table('metric_snapshot',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('rule_version_id', sa.Uuid(), nullable=True),
    sa.Column('policy_version_id', sa.Uuid(), nullable=True),
    sa.Column('vector_id', sa.Uuid(), nullable=True),
    sa.Column('metric_code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
    sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
    sa.Column('value', sa.Numeric(), nullable=False),
    sa.Column('numerator', sa.Numeric(), nullable=True),
    sa.Column('denominator', sa.Numeric(), nullable=True),
    sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_metric_snapshot_faskes_id_faskes')),
    sa.ForeignKeyConstraint(['policy_version_id'], ['policy_version.id'], name=op.f('fk_metric_snapshot_policy_version_id_policy_version')),
    sa.ForeignKeyConstraint(['rule_version_id'], ['rule_version.id'], name=op.f('fk_metric_snapshot_rule_version_id_rule_version')),
    sa.ForeignKeyConstraint(['vector_id'], ['risk_vector.id'], name=op.f('fk_metric_snapshot_vector_id_risk_vector')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_metric_snapshot'))
    )
    op.create_index('ix_metric_snapshot_faskes_id_metric_code_window_end', 'metric_snapshot', ['faskes_id', 'metric_code', 'window_end'], unique=False)
    op.create_table('policy_rule',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('policy_version_id', sa.Uuid(), nullable=False),
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('tier', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('condition_spec', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.ForeignKeyConstraint(['policy_version_id'], ['policy_version.id'], name=op.f('fk_policy_rule_policy_version_id_policy_version')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_policy_rule')),
    sa.UniqueConstraint('policy_version_id', 'code', name=op.f('uq_policy_rule_policy_version_id'))
    )
    op.create_table('investigation_run',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('faskes_id', sa.Uuid(), nullable=False),
    sa.Column('claim_id', sa.Uuid(), nullable=False),
    sa.Column('job_id', sa.Uuid(), nullable=True),
    sa.Column('rule_version_id', sa.Uuid(), nullable=False),
    sa.Column('policy_version_id', sa.Uuid(), nullable=False),
    sa.Column('trigger', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('outcome', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('abstain_reason', sa.Text(), nullable=True),
    sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('model_version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('prompt_version', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['claim_id'], ['claim.id'], name=op.f('fk_investigation_run_claim_id_claim')),
    sa.ForeignKeyConstraint(['faskes_id'], ['faskes.id'], name=op.f('fk_investigation_run_faskes_id_faskes')),
    sa.ForeignKeyConstraint(['job_id'], ['investigation_job.id'], name=op.f('fk_investigation_run_job_id_investigation_job')),
    sa.ForeignKeyConstraint(['policy_version_id'], ['policy_version.id'], name=op.f('fk_investigation_run_policy_version_id_policy_version')),
    sa.ForeignKeyConstraint(['rule_version_id'], ['rule_version.id'], name=op.f('fk_investigation_run_rule_version_id_rule_version')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_investigation_run'))
    )
    op.create_index(op.f('ix_investigation_run_claim_id'), 'investigation_run', ['claim_id'], unique=False)
    op.create_index(op.f('ix_investigation_run_faskes_id'), 'investigation_run', ['faskes_id'], unique=False)
    op.create_index(op.f('ix_investigation_run_job_id'), 'investigation_run', ['job_id'], unique=False)
    op.create_index(op.f('ix_investigation_run_policy_version_id'), 'investigation_run', ['policy_version_id'], unique=False)
    op.create_index(op.f('ix_investigation_run_rule_version_id'), 'investigation_run', ['rule_version_id'], unique=False)
    op.create_table('agent_step',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('step_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('tool_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('query', sa.Text(), nullable=True),
    sa.Column('source_id', sa.Uuid(), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('result_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], ['investigation_run.id'], name=op.f('fk_agent_step_run_id_investigation_run')),
    sa.ForeignKeyConstraint(['source_id'], ['evidence_source.id'], name=op.f('fk_agent_step_source_id_evidence_source')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_step')),
    sa.UniqueConstraint('run_id', 'seq', name=op.f('uq_agent_step_run_id'))
    )
    op.create_index(op.f('ix_agent_step_source_id'), 'agent_step', ['source_id'], unique=False)
    op.create_table('finding',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('vector_id', sa.Uuid(), nullable=False),
    sa.Column('claim_code_id', sa.Uuid(), nullable=True),
    sa.Column('mismatch_desc', sa.Text(), nullable=False),
    sa.Column('delta', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('confidence', sa.Numeric(), nullable=False),
    sa.ForeignKeyConstraint(['claim_code_id'], ['claim_code.id'], name=op.f('fk_finding_claim_code_id_claim_code')),
    sa.ForeignKeyConstraint(['run_id'], ['investigation_run.id'], name=op.f('fk_finding_run_id_investigation_run')),
    sa.ForeignKeyConstraint(['vector_id'], ['risk_vector.id'], name=op.f('fk_finding_vector_id_risk_vector')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_finding'))
    )
    op.create_index(op.f('ix_finding_claim_code_id'), 'finding', ['claim_code_id'], unique=False)
    op.create_index(op.f('ix_finding_run_id'), 'finding', ['run_id'], unique=False)
    op.create_index(op.f('ix_finding_vector_id'), 'finding', ['vector_id'], unique=False)
    op.create_table('evidence_citation',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('finding_id', sa.Uuid(), nullable=False),
    sa.Column('evidence_item_id', sa.Uuid(), nullable=False),
    sa.Column('quote_span', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('evidence_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('cited_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['evidence_item_id'], ['evidence_item.id'], name=op.f('fk_evidence_citation_evidence_item_id_evidence_item')),
    sa.ForeignKeyConstraint(['finding_id'], ['finding.id'], name=op.f('fk_evidence_citation_finding_id_finding')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evidence_citation'))
    )
    op.create_index(op.f('ix_evidence_citation_evidence_item_id'), 'evidence_citation', ['evidence_item_id'], unique=False)
    op.create_index(op.f('ix_evidence_citation_finding_id'), 'evidence_citation', ['finding_id'], unique=False)
    op.create_table('intervention',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('finding_id', sa.Uuid(), nullable=True),
    sa.Column('policy_rule_id', sa.Uuid(), nullable=False),
    sa.Column('tier', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('policy_rule_ref', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.ForeignKeyConstraint(['finding_id'], ['finding.id'], name=op.f('fk_intervention_finding_id_finding')),
    sa.ForeignKeyConstraint(['policy_rule_id'], ['policy_rule.id'], name=op.f('fk_intervention_policy_rule_id_policy_rule')),
    sa.ForeignKeyConstraint(['run_id'], ['investigation_run.id'], name=op.f('fk_intervention_run_id_investigation_run')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_intervention'))
    )
    op.create_index(op.f('ix_intervention_finding_id'), 'intervention', ['finding_id'], unique=False)
    op.create_index(op.f('ix_intervention_policy_rule_id'), 'intervention', ['policy_rule_id'], unique=False)
    op.create_index(op.f('ix_intervention_run_id'), 'intervention', ['run_id'], unique=False)
    op.create_table('cognitive_assessment',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('intervention_id', sa.Uuid(), nullable=False),
    sa.Column('verifier_id', sa.Uuid(), nullable=False),
    sa.Column('self_verdict', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('self_note', sa.Text(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['intervention_id'], ['intervention.id'], name=op.f('fk_cognitive_assessment_intervention_id_intervention')),
    sa.ForeignKeyConstraint(['verifier_id'], ['app_user.id'], name=op.f('fk_cognitive_assessment_verifier_id_app_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cognitive_assessment'))
    )
    op.create_index(op.f('ix_cognitive_assessment_intervention_id'), 'cognitive_assessment', ['intervention_id'], unique=False)
    op.create_index(op.f('ix_cognitive_assessment_verifier_id'), 'cognitive_assessment', ['verifier_id'], unique=False)
    op.create_table('human_verdict',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('intervention_id', sa.Uuid(), nullable=False),
    sa.Column('verifier_id', sa.Uuid(), nullable=False),
    sa.Column('verdict', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('rationale', sa.Text(), nullable=True),
    sa.Column('time_to_decision_ms', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['intervention_id'], ['intervention.id'], name=op.f('fk_human_verdict_intervention_id_intervention')),
    sa.ForeignKeyConstraint(['verifier_id'], ['app_user.id'], name=op.f('fk_human_verdict_verifier_id_app_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_human_verdict'))
    )
    op.create_index(op.f('ix_human_verdict_intervention_id'), 'human_verdict', ['intervention_id'], unique=False)
    op.create_index(op.f('ix_human_verdict_verifier_id'), 'human_verdict', ['verifier_id'], unique=False)
    op.create_table('rule_update',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('verdict_id', sa.Uuid(), nullable=False),
    sa.Column('base_rule_version_id', sa.Uuid(), nullable=False),
    sa.Column('result_rule_version_id', sa.Uuid(), nullable=True),
    sa.Column('proposed_change', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('decided_by', sa.Uuid(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['base_rule_version_id'], ['rule_version.id'], name=op.f('fk_rule_update_base_rule_version_id_rule_version')),
    sa.ForeignKeyConstraint(['decided_by'], ['app_user.id'], name=op.f('fk_rule_update_decided_by_app_user')),
    sa.ForeignKeyConstraint(['result_rule_version_id'], ['rule_version.id'], name=op.f('fk_rule_update_result_rule_version_id_rule_version')),
    sa.ForeignKeyConstraint(['verdict_id'], ['human_verdict.id'], name=op.f('fk_rule_update_verdict_id_human_verdict')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_rule_update'))
    )
    op.create_index(op.f('ix_rule_update_base_rule_version_id'), 'rule_update', ['base_rule_version_id'], unique=False)
    op.create_index(op.f('ix_rule_update_decided_by'), 'rule_update', ['decided_by'], unique=False)
    op.create_index(op.f('ix_rule_update_result_rule_version_id'), 'rule_update', ['result_rule_version_id'], unique=False)
    op.create_index(op.f('ix_rule_update_verdict_id'), 'rule_update', ['verdict_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rule_update_verdict_id'), table_name='rule_update')
    op.drop_index(op.f('ix_rule_update_result_rule_version_id'), table_name='rule_update')
    op.drop_index(op.f('ix_rule_update_decided_by'), table_name='rule_update')
    op.drop_index(op.f('ix_rule_update_base_rule_version_id'), table_name='rule_update')
    op.drop_table('rule_update')
    op.drop_index(op.f('ix_human_verdict_verifier_id'), table_name='human_verdict')
    op.drop_index(op.f('ix_human_verdict_intervention_id'), table_name='human_verdict')
    op.drop_table('human_verdict')
    op.drop_index(op.f('ix_cognitive_assessment_verifier_id'), table_name='cognitive_assessment')
    op.drop_index(op.f('ix_cognitive_assessment_intervention_id'), table_name='cognitive_assessment')
    op.drop_table('cognitive_assessment')
    op.drop_index(op.f('ix_intervention_run_id'), table_name='intervention')
    op.drop_index(op.f('ix_intervention_policy_rule_id'), table_name='intervention')
    op.drop_index(op.f('ix_intervention_finding_id'), table_name='intervention')
    op.drop_table('intervention')
    op.drop_index(op.f('ix_evidence_citation_finding_id'), table_name='evidence_citation')
    op.drop_index(op.f('ix_evidence_citation_evidence_item_id'), table_name='evidence_citation')
    op.drop_table('evidence_citation')
    op.drop_index(op.f('ix_finding_vector_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_run_id'), table_name='finding')
    op.drop_index(op.f('ix_finding_claim_code_id'), table_name='finding')
    op.drop_table('finding')
    op.drop_index(op.f('ix_agent_step_source_id'), table_name='agent_step')
    op.drop_table('agent_step')
    op.drop_index(op.f('ix_investigation_run_rule_version_id'), table_name='investigation_run')
    op.drop_index(op.f('ix_investigation_run_policy_version_id'), table_name='investigation_run')
    op.drop_index(op.f('ix_investigation_run_job_id'), table_name='investigation_run')
    op.drop_index(op.f('ix_investigation_run_faskes_id'), table_name='investigation_run')
    op.drop_index(op.f('ix_investigation_run_claim_id'), table_name='investigation_run')
    op.drop_table('investigation_run')
    op.drop_table('policy_rule')
    op.drop_index('ix_metric_snapshot_faskes_id_metric_code_window_end', table_name='metric_snapshot')
    op.drop_table('metric_snapshot')
    op.drop_index('ix_investigation_job_status_created_at', table_name='investigation_job')
    op.drop_index(op.f('ix_investigation_job_claim_id'), table_name='investigation_job')
    op.drop_table('investigation_job')
    op.drop_index(op.f('ix_expected_rule_rule_version_id'), table_name='expected_rule')
    op.drop_table('expected_rule')
    op.drop_index(op.f('ix_evidence_item_source_id'), table_name='evidence_item')
    op.drop_index(op.f('ix_evidence_item_faskes_id'), table_name='evidence_item')
    op.drop_index('ix_evidence_item_embedding_hnsw', table_name='evidence_item', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'}, postgresql_with={'m': 16, 'ef_construction': 64})
    op.drop_index(op.f('ix_evidence_item_content_hash'), table_name='evidence_item')
    op.drop_index('ix_evidence_item_claim_id_recorded_at', table_name='evidence_item')
    op.drop_table('evidence_item')
    op.drop_index(op.f('ix_claim_code_code'), table_name='claim_code')
    op.drop_index(op.f('ix_claim_code_claim_id'), table_name='claim_code')
    op.drop_table('claim_code')
    op.drop_index(op.f('ix_rule_version_approved_by'), table_name='rule_version')
    op.drop_table('rule_version')
    op.drop_index(op.f('ix_policy_version_approved_by'), table_name='policy_version')
    op.drop_table('policy_version')
    op.drop_index(op.f('ix_claim_submitted_by'), table_name='claim')
    op.drop_index(op.f('ix_claim_locked_by'), table_name='claim')
    op.drop_index('ix_claim_faskes_id_episode_no', table_name='claim')
    op.drop_table('claim')
    op.drop_index('ix_audit_log_faskes_id_created_at', table_name='audit_log')
    op.drop_index('ix_audit_log_entity_type_entity_id', table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_actor_id'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_index(op.f('ix_rule_set_vector_id'), table_name='rule_set')
    op.drop_table('rule_set')
    op.drop_index(op.f('ix_evidence_source_faskes_id'), table_name='evidence_source')
    op.drop_table('evidence_source')
    op.drop_index(op.f('ix_app_user_faskes_id'), table_name='app_user')
    op.drop_table('app_user')
    op.drop_table('risk_vector')
    op.drop_table('faskes')
