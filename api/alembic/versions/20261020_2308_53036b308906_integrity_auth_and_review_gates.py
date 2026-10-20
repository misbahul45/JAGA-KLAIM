"""integrity auth and review gates

Revision ID: 53036b308906
Revises: 1342c34cea7a
Create Date: 2026-10-20 23:08:05.152394
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

revision: str = '53036b308906'
down_revision: Union[str, Sequence[str], None] = '1342c34cea7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPROVER_NOT_AUTHOR = "created_by IS NULL OR approved_by IS NULL OR created_by <> approved_by"
VERSION_STATUSES = "'draft', 'pending_approval', 'approved', 'active', 'retired', 'rejected'"

CHECKS: list[tuple[str, str, str]] = [
    ("app_user", "role_valid", "role IN ('coder', 'verifier', 'faskes_admin', 'auditor', 'rule_admin', 'rule_approver')"),
    ("claim", "status_valid", "status IN ('draft', 'coding_submitted', 'under_review', 'needs_clarification', 'returned_to_coder', 'ready_to_lock', 'locked')"),
    ("claim", "version_positive", "version >= 1"),
    ("claim", "episode_period_valid", "episode_start IS NULL OR episode_end IS NULL OR episode_end >= episode_start"),
    ("evidence_source", "health_status_valid", "health_status IN ('unknown', 'healthy', 'degraded', 'down')"),
    ("evidence_source", "freshness_sla_positive", "freshness_sla_seconds > 0"),
    ("evidence_citation", "validation_status_valid", "validation_status IN ('unchecked', 'valid', 'invalid')"),
    ("rule_version", "status_valid", f"status IN ({VERSION_STATUSES})"),
    ("rule_version", "validation_status_valid", "validation_status IN ('belum_tervalidasi', 'simulasi', 'tervalidasi_pakar')"),
    ("rule_version", "approver_not_author", APPROVER_NOT_AUTHOR),
    ("policy_version", "status_valid", f"status IN ({VERSION_STATUSES})"),
    ("policy_version", "approver_not_author", APPROVER_NOT_AUTHOR),
    ("policy_rule", "tier_valid", "tier IN ('T0', 'T1', 'T2', 'T3')"),
    ("investigation_job", "status_valid", "status IN ('queued', 'processing', 'succeeded', 'partial', 'failed', 'cancelled', 'stale')"),
    ("investigation_job", "attempt_count_non_negative", "attempt_count >= 0"),
    ("investigation_job", "claim_version_positive", "claim_version >= 1"),
    ("investigation_run", "status_valid", "status IN ('running', 'succeeded', 'partial', 'failed', 'cancelled')"),
    ("investigation_run", "outcome_valid", "outcome IS NULL OR outcome IN ('no_action', 'findings', 'abstained')"),
    ("investigation_run", "claim_version_positive", "claim_version >= 1"),
    ("agent_step", "status_valid", "status IN ('ok', 'failed', 'blocked')"),
    ("finding", "status_valid", "status IN ('valid', 'downgraded', 'rejected')"),
    ("finding", "confidence_in_unit_range", "confidence >= 0 AND confidence <= 1"),
    ("intervention", "tier_valid", "tier IN ('T0', 'T1', 'T2', 'T3')"),
    ("cognitive_assessment", "self_verdict_valid", "self_verdict IN ('supports_finding', 'does_not_support_finding', 'needs_clarification', 'insufficient_evidence')"),
    ("human_verdict", "verdict_valid", "verdict IN ('supports_finding', 'does_not_support_finding', 'needs_clarification', 'insufficient_evidence')"),
    ("human_verdict", "follow_up_valid", "follow_up IN ('proceed', 'return_to_coder', 'request_clarification')"),
    ("human_verdict", "correction_requires_rationale", "supersedes_verdict_id IS NULL OR (rationale IS NOT NULL AND length(trim(rationale)) > 0)"),
    ("rule_update", "status_valid", "status IN ('proposed', 'evaluating', 'evaluated', 'approved', 'rejected', 'activated', 'rolled_back')"),
    ("rule_update", "decider_not_proposer", "proposed_by IS NULL OR decided_by IS NULL OR proposed_by <> decided_by"),
    ("audit_log", "seq_positive", "seq >= 1"),
    ("metric_snapshot", "window_valid", "window_end > window_start"),
]

IMMUTABLE_TABLES = ("audit_log", "human_verdict", "cognitive_assessment")


def upgrade() -> None:
    op.create_table('auth_session',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('expires_at > created_at', name=op.f('ck_auth_session_expiry_after_creation')),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_auth_session_user_id_app_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_session')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_auth_session_token_hash'))
    )
    op.create_index('ix_auth_session_user_id_expires_at', 'auth_session', ['user_id', 'expires_at'], unique=False)
    op.create_table('user_credential',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('failed_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('failed_attempts >= 0', name=op.f('ck_user_credential_failed_attempts_non_negative')),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], name=op.f('fk_user_credential_user_id_app_user')),
    sa.PrimaryKeyConstraint('user_id', name=op.f('pk_user_credential'))
    )
    op.create_table('rule_update_basis',
    sa.Column('rule_update_id', sa.Uuid(), nullable=False),
    sa.Column('verdict_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['rule_update_id'], ['rule_update.id'], name=op.f('fk_rule_update_basis_rule_update_id_rule_update')),
    sa.ForeignKeyConstraint(['verdict_id'], ['human_verdict.id'], name=op.f('fk_rule_update_basis_verdict_id_human_verdict')),
    sa.PrimaryKeyConstraint('rule_update_id', 'verdict_id', name=op.f('pk_rule_update_basis'))
    )

    op.add_column('audit_log', sa.Column('seq', sa.BigInteger(), nullable=True))
    op.execute(
        "UPDATE audit_log SET seq = ranked.rn FROM ("
        "SELECT id, row_number() OVER (PARTITION BY faskes_id ORDER BY created_at, id) AS rn "
        "FROM audit_log) AS ranked WHERE audit_log.id = ranked.id"
    )
    op.alter_column('audit_log', 'seq', nullable=False)
    op.create_unique_constraint('uq_audit_log_faskes_seq', 'audit_log', ['faskes_id', 'seq'])

    op.add_column('claim', sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('claim', sa.Column('episode_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('claim', sa.Column('episode_end', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_claim_faskes_id_status', 'claim', ['faskes_id', 'status'], unique=False)

    op.create_unique_constraint('uq_cognitive_assessment_intervention_verifier', 'cognitive_assessment', ['intervention_id', 'verifier_id'])

    op.add_column('evidence_citation', sa.Column('validation_status', sqlmodel.sql.sqltypes.AutoString(), server_default='unchecked', nullable=False))
    op.add_column('evidence_item', sa.Column('injection_suspected', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_unique_constraint('uq_evidence_item_claim_source_hash', 'evidence_item', ['claim_id', 'source_id', 'content_hash'])

    op.add_column('evidence_source', sa.Column('health_status', sqlmodel.sql.sqltypes.AutoString(), server_default='unknown', nullable=False))
    op.add_column('evidence_source', sa.Column('last_health_check_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('evidence_source', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('evidence_source', sa.Column('freshness_sla_seconds', sa.Integer(), server_default=sa.text('86400'), nullable=False))
    op.add_column('evidence_source', sa.Column('coverage', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.create_unique_constraint('uq_evidence_source_faskes_system_ref', 'evidence_source', ['faskes_id', 'system_ref'])

    op.add_column('finding', sa.Column('faskes_id', sa.Uuid(), nullable=True))
    op.add_column('finding', sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), server_default='valid', nullable=False))
    op.execute(
        "UPDATE finding SET faskes_id = investigation_run.faskes_id "
        "FROM investigation_run WHERE finding.run_id = investigation_run.id"
    )
    op.alter_column('finding', 'faskes_id', nullable=False)
    op.create_index(op.f('ix_finding_faskes_id'), 'finding', ['faskes_id'], unique=False)
    op.create_foreign_key(op.f('fk_finding_faskes_id_faskes'), 'finding', 'faskes', ['faskes_id'], ['id'])

    op.add_column('human_verdict', sa.Column('assessment_id', sa.Uuid(), nullable=True))
    op.add_column('human_verdict', sa.Column('supersedes_verdict_id', sa.Uuid(), nullable=True))
    op.add_column('human_verdict', sa.Column('follow_up', sqlmodel.sql.sqltypes.AutoString(), server_default='proceed', nullable=False))
    op.create_index(op.f('ix_human_verdict_assessment_id'), 'human_verdict', ['assessment_id'], unique=False)
    op.create_index('uq_human_verdict_original_per_intervention', 'human_verdict', ['intervention_id'], unique=True, postgresql_where=sa.text('supersedes_verdict_id IS NULL'))
    op.create_unique_constraint('uq_human_verdict_supersedes', 'human_verdict', ['supersedes_verdict_id'])
    op.create_foreign_key(op.f('fk_human_verdict_assessment_id_cognitive_assessment'), 'human_verdict', 'cognitive_assessment', ['assessment_id'], ['id'])
    op.create_foreign_key(op.f('fk_human_verdict_supersedes_verdict_id_human_verdict'), 'human_verdict', 'human_verdict', ['supersedes_verdict_id'], ['id'])

    op.add_column('intervention', sa.Column('faskes_id', sa.Uuid(), nullable=True))
    op.add_column('intervention', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE intervention SET faskes_id = investigation_run.faskes_id "
        "FROM investigation_run WHERE intervention.run_id = investigation_run.id"
    )
    op.alter_column('intervention', 'faskes_id', nullable=False)
    op.create_index(op.f('ix_intervention_faskes_id'), 'intervention', ['faskes_id'], unique=False)
    op.create_index('ix_intervention_faskes_id_resolved_at', 'intervention', ['faskes_id', 'resolved_at'], unique=False)
    op.create_index('uq_intervention_run_finding', 'intervention', ['run_id', 'finding_id'], unique=True, postgresql_where=sa.text('finding_id IS NOT NULL'))
    op.create_index('uq_intervention_run_without_finding', 'intervention', ['run_id'], unique=True, postgresql_where=sa.text('finding_id IS NULL'))
    op.create_foreign_key(op.f('fk_intervention_faskes_id_faskes'), 'intervention', 'faskes', ['faskes_id'], ['id'])

    op.add_column('investigation_job', sa.Column('claim_version', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('investigation_job', sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('investigation_job', sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_investigation_job_faskes_id'), 'investigation_job', ['faskes_id'], unique=False)

    op.add_column('investigation_run', sa.Column('claim_version', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('investigation_run', sa.Column('rerun_of_run_id', sa.Uuid(), nullable=True))
    op.add_column('investigation_run', sa.Column('correlation_id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False))
    op.add_column('investigation_run', sa.Column('coverage', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column('investigation_run', sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('investigation_run', sa.Column('stale_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_investigation_run_rerun_of_run_id'), 'investigation_run', ['rerun_of_run_id'], unique=False)
    op.create_foreign_key(op.f('fk_investigation_run_rerun_of_run_id_investigation_run'), 'investigation_run', 'investigation_run', ['rerun_of_run_id'], ['id'])

    op.create_index('uq_metric_snapshot_identity', 'metric_snapshot', ['faskes_id', 'metric_code', 'window_start', 'window_end', 'vector_id', 'rule_version_id', 'policy_version_id'], unique=True, postgresql_nulls_not_distinct=True)

    op.create_unique_constraint('uq_policy_rule_version_priority', 'policy_rule', ['policy_version_id', 'priority'])

    op.add_column('policy_version', sa.Column('created_by', sa.Uuid(), nullable=True))
    op.add_column('policy_version', sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_policy_version_created_by'), 'policy_version', ['created_by'], unique=False)
    op.create_index('uq_policy_version_single_active', 'policy_version', [sa.literal_column('(true)')], unique=True, postgresql_where=sa.text("status = 'active'"))
    op.create_foreign_key(op.f('fk_policy_version_created_by_app_user'), 'policy_version', 'app_user', ['created_by'], ['id'])

    op.create_unique_constraint('uq_rule_set_vector_name', 'rule_set', ['vector_id', 'name'])

    op.add_column('rule_update', sa.Column('proposed_by', sa.Uuid(), nullable=True))
    op.add_column('rule_update', sa.Column('evaluation', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('rule_update', sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_rule_update_proposed_by'), 'rule_update', ['proposed_by'], unique=False)
    op.create_foreign_key(op.f('fk_rule_update_proposed_by_app_user'), 'rule_update', 'app_user', ['proposed_by'], ['id'])

    op.add_column('rule_version', sa.Column('validation_status', sqlmodel.sql.sqltypes.AutoString(), server_default='belum_tervalidasi', nullable=False))
    op.add_column('rule_version', sa.Column('created_by', sa.Uuid(), nullable=True))
    op.add_column('rule_version', sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_rule_version_created_by'), 'rule_version', ['created_by'], unique=False)
    op.create_index('uq_rule_version_single_active', 'rule_version', ['rule_set_id'], unique=True, postgresql_where=sa.text("status = 'active'"))
    op.create_foreign_key(op.f('fk_rule_version_created_by_app_user'), 'rule_version', 'app_user', ['created_by'], ['id'])

    for table, name, expression in CHECKS:
        op.create_check_constraint(op.f(f'ck_{table}_{name}'), table, expression)
    op.execute(
        "ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_chain_link_consistent "
        "CHECK ((seq = 1 AND prev_hash IS NULL) OR (seq > 1 AND prev_hash IS NOT NULL)) NOT VALID"
    )

    op.execute(
        "CREATE FUNCTION forbid_row_mutation() RETURNS trigger LANGUAGE plpgsql AS $fn$ "
        "BEGIN RAISE EXCEPTION 'tabel % bersifat append-only; % ditolak', TG_TABLE_NAME, TG_OP "
        "USING ERRCODE = 'restrict_violation'; END; $fn$"
    )
    for table in IMMUTABLE_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION forbid_row_mutation()"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION forbid_row_mutation()"
        )


def downgrade() -> None:
    for table in IMMUTABLE_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
    op.execute("DROP FUNCTION IF EXISTS forbid_row_mutation()")

    op.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS ck_audit_log_chain_link_consistent")
    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(op.f(f'ck_{table}_{name}'), table, type_='check')

    op.drop_constraint(op.f('fk_rule_version_created_by_app_user'), 'rule_version', type_='foreignkey')
    op.drop_index('uq_rule_version_single_active', table_name='rule_version', postgresql_where=sa.text("status = 'active'"))
    op.drop_index(op.f('ix_rule_version_created_by'), table_name='rule_version')
    op.drop_column('rule_version', 'submitted_at')
    op.drop_column('rule_version', 'created_by')
    op.drop_column('rule_version', 'validation_status')
    op.drop_constraint(op.f('fk_rule_update_proposed_by_app_user'), 'rule_update', type_='foreignkey')
    op.drop_index(op.f('ix_rule_update_proposed_by'), table_name='rule_update')
    op.drop_column('rule_update', 'evaluated_at')
    op.drop_column('rule_update', 'evaluation')
    op.drop_column('rule_update', 'proposed_by')
    op.drop_constraint('uq_rule_set_vector_name', 'rule_set', type_='unique')
    op.drop_constraint(op.f('fk_policy_version_created_by_app_user'), 'policy_version', type_='foreignkey')
    op.drop_index('uq_policy_version_single_active', table_name='policy_version', postgresql_where=sa.text("status = 'active'"))
    op.drop_index(op.f('ix_policy_version_created_by'), table_name='policy_version')
    op.drop_column('policy_version', 'activated_at')
    op.drop_column('policy_version', 'created_by')
    op.drop_constraint('uq_policy_rule_version_priority', 'policy_rule', type_='unique')
    op.drop_index('uq_metric_snapshot_identity', table_name='metric_snapshot', postgresql_nulls_not_distinct=True)
    op.drop_constraint(op.f('fk_investigation_run_rerun_of_run_id_investigation_run'), 'investigation_run', type_='foreignkey')
    op.drop_index(op.f('ix_investigation_run_rerun_of_run_id'), table_name='investigation_run')
    op.drop_column('investigation_run', 'stale_at')
    op.drop_column('investigation_run', 'validation_errors')
    op.drop_column('investigation_run', 'coverage')
    op.drop_column('investigation_run', 'correlation_id')
    op.drop_column('investigation_run', 'rerun_of_run_id')
    op.drop_column('investigation_run', 'claim_version')
    op.drop_index(op.f('ix_investigation_job_faskes_id'), table_name='investigation_job')
    op.drop_column('investigation_job', 'locked_at')
    op.drop_column('investigation_job', 'next_attempt_at')
    op.drop_column('investigation_job', 'claim_version')
    op.drop_constraint(op.f('fk_intervention_faskes_id_faskes'), 'intervention', type_='foreignkey')
    op.drop_index('uq_intervention_run_without_finding', table_name='intervention', postgresql_where=sa.text('finding_id IS NULL'))
    op.drop_index('uq_intervention_run_finding', table_name='intervention', postgresql_where=sa.text('finding_id IS NOT NULL'))
    op.drop_index('ix_intervention_faskes_id_resolved_at', table_name='intervention')
    op.drop_index(op.f('ix_intervention_faskes_id'), table_name='intervention')
    op.drop_column('intervention', 'resolved_at')
    op.drop_column('intervention', 'faskes_id')
    op.drop_constraint(op.f('fk_human_verdict_supersedes_verdict_id_human_verdict'), 'human_verdict', type_='foreignkey')
    op.drop_constraint(op.f('fk_human_verdict_assessment_id_cognitive_assessment'), 'human_verdict', type_='foreignkey')
    op.drop_constraint('uq_human_verdict_supersedes', 'human_verdict', type_='unique')
    op.drop_index('uq_human_verdict_original_per_intervention', table_name='human_verdict', postgresql_where=sa.text('supersedes_verdict_id IS NULL'))
    op.drop_index(op.f('ix_human_verdict_assessment_id'), table_name='human_verdict')
    op.drop_column('human_verdict', 'follow_up')
    op.drop_column('human_verdict', 'supersedes_verdict_id')
    op.drop_column('human_verdict', 'assessment_id')
    op.drop_constraint(op.f('fk_finding_faskes_id_faskes'), 'finding', type_='foreignkey')
    op.drop_index(op.f('ix_finding_faskes_id'), table_name='finding')
    op.drop_column('finding', 'status')
    op.drop_column('finding', 'faskes_id')
    op.drop_constraint('uq_evidence_source_faskes_system_ref', 'evidence_source', type_='unique')
    op.drop_column('evidence_source', 'coverage')
    op.drop_column('evidence_source', 'freshness_sla_seconds')
    op.drop_column('evidence_source', 'last_synced_at')
    op.drop_column('evidence_source', 'last_health_check_at')
    op.drop_column('evidence_source', 'health_status')
    op.drop_constraint('uq_evidence_item_claim_source_hash', 'evidence_item', type_='unique')
    op.drop_column('evidence_item', 'injection_suspected')
    op.drop_column('evidence_citation', 'validation_status')
    op.drop_constraint('uq_cognitive_assessment_intervention_verifier', 'cognitive_assessment', type_='unique')
    op.drop_index('ix_claim_faskes_id_status', table_name='claim')
    op.drop_column('claim', 'episode_end')
    op.drop_column('claim', 'episode_start')
    op.drop_column('claim', 'version')
    op.drop_constraint('uq_audit_log_faskes_seq', 'audit_log', type_='unique')
    op.drop_column('audit_log', 'seq')
    op.drop_table('rule_update_basis')
    op.drop_table('user_credential')
    op.drop_index('ix_auth_session_user_id_expires_at', table_name='auth_session')
    op.drop_table('auth_session')
