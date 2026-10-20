import uuid
from datetime import timedelta

import pytest
from sqlalchemy import CheckConstraint, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlmodel import Session, SQLModel, select

from app.models import (
    AuditLog,
    Claim,
    Faskes,
    MetricSnapshot,
    PolicyVersion,
    RiskVector,
    RuleSet,
    RuleVersion,
)
from app.models.base import utcnow
from app.services import audit
from tests.builders import World
from tests.integration.helpers import Actors, make_claim, submit_and_process

RESUME_ONLY = [("emr", "resume_medis", "Resume sintetis: pasien dirawat dan pulang dalam kondisi baik.")]


def test_every_model_check_constraint_exists_in_the_database(session: Session):
    declared: set[tuple[str, str]] = set()
    for table in SQLModel.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint) and constraint.name:
                declared.add((table.name, str(constraint.name)))
    assert len(declared) >= 30
    present = {
        (row[0], row[1])
        for row in session.execute(
            text(
                "SELECT rel.relname, con.conname FROM pg_constraint con "
                "JOIN pg_class rel ON rel.oid = con.conrelid "
                "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
                "WHERE ns.nspname = 'public' AND con.contype = 'c'"
            )
        )
    }
    assert declared <= present


def test_invalid_claim_status_is_rejected_by_the_database(session: Session, world: World):
    session.add(
        Claim(faskes_id=world.a.faskes_id, episode_no="EP-DB-1", patient_pseudonym="PSEUDO-1", status="fraud_confirmed")
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_only_one_active_rule_version_per_rule_set(session: Session, world: World):
    active = session.exec(select(RuleVersion).where(RuleVersion.status == "active")).first()
    session.add(RuleVersion(rule_set_id=active.rule_set_id, version="sim-2.0", status="active"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_only_one_active_policy_version(session: Session, world: World):
    session.add(PolicyVersion(version="policy-lain", status="active", config_hash="x" * 64, config={}))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_rule_version_cannot_be_approved_by_its_author(session: Session, world: World):
    rule_set = session.exec(select(RuleSet)).first()
    author = world.a.user_ids["admin"]
    session.add(
        RuleVersion(
            rule_set_id=rule_set.id, version="sim-3.0", status="approved", created_by=author, approved_by=author
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_duplicate_evidence_hash_per_claim_and_source_is_rejected(session: Session, world: World):
    from app.seed import add_evidence

    claim = make_claim(session, world.a, episode_no="EP-DB-2", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    with pytest.raises(IntegrityError):
        add_evidence(
            session, claim, world.a.source_ids["emr"], kind="resume_medis", text=RESUME_ONLY[0][2]
        )
    session.rollback()


def test_audit_log_rejects_update_delete_and_truncate(session: Session, world: World):
    entry = audit.append_event(
        session,
        faskes_id=world.a.faskes_id,
        entity_type="test",
        entity_id=uuid.uuid4(),
        event_type="test.event",
        actor_type="system",
    )
    session.commit()
    for statement in (
        text("UPDATE audit_log SET event_type = 'x' WHERE id = :id"),
        text("DELETE FROM audit_log WHERE id = :id"),
    ):
        with pytest.raises(DBAPIError) as exc:
            session.execute(statement, {"id": entry.id})
        assert "append-only" in str(exc.value)
        session.rollback()
    with pytest.raises(DBAPIError):
        session.execute(text("TRUNCATE audit_log"))
    session.rollback()


def test_audit_chain_detects_tampering_when_protection_is_bypassed(session: Session, world: World):
    for index in range(4):
        audit.append_event(
            session,
            faskes_id=world.a.faskes_id,
            entity_type="test",
            entity_id=uuid.uuid4(),
            event_type=f"test.event{index}",
            actor_type="system",
            payload={"index": index},
        )
    session.commit()
    assert audit.verify_chain(session, world.a.faskes_id).valid

    session.execute(text("ALTER TABLE audit_log DISABLE TRIGGER trg_audit_log_append_only"))
    session.execute(
        text("UPDATE audit_log SET payload = '{\"index\": 99}'::jsonb WHERE faskes_id = :f AND seq = 2"),
        {"f": world.a.faskes_id},
    )
    session.expire_all()
    result = audit.verify_chain(session, world.a.faskes_id)
    assert not result.valid
    assert result.first_invalid_seq == 2
    assert "record_hash" in result.reason
    session.rollback()


def test_audit_chain_detects_a_removed_entry(session: Session, world: World):
    for index in range(3):
        audit.append_event(
            session,
            faskes_id=world.a.faskes_id,
            entity_type="test",
            entity_id=uuid.uuid4(),
            event_type=f"test.event{index}",
            actor_type="system",
        )
    session.commit()
    session.execute(text("ALTER TABLE audit_log DISABLE TRIGGER trg_audit_log_append_only"))
    session.execute(text("DELETE FROM audit_log WHERE faskes_id = :f AND seq = 2"), {"f": world.a.faskes_id})
    session.expire_all()
    result = audit.verify_chain(session, world.a.faskes_id)
    assert not result.valid and result.first_invalid_seq == 3
    session.rollback()


def test_audit_chains_are_independent_per_tenant(session: Session, world: World):
    for faskes in (world.a, world.b):
        for _ in range(3):
            audit.append_event(
                session,
                faskes_id=faskes.faskes_id,
                entity_type="test",
                entity_id=uuid.uuid4(),
                event_type="test.event",
                actor_type="system",
            )
    session.commit()
    seqs_a = [r.seq for r in session.exec(select(AuditLog).where(AuditLog.faskes_id == world.a.faskes_id))]
    seqs_b = [r.seq for r in session.exec(select(AuditLog).where(AuditLog.faskes_id == world.b.faskes_id))]
    assert sorted(seqs_a) == [1, 2, 3] and sorted(seqs_b) == [1, 2, 3]
    assert audit.verify_chain(session, world.a.faskes_id).valid
    assert audit.verify_chain(session, world.b.faskes_id).valid


def test_assessments_and_verdicts_cannot_be_rewritten(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-DB-3", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    [item] = team_a.verifier.get("/v1/interventions").json()["items"]
    url = f"/v1/interventions/{item['intervention_id']}"
    team_a.verifier.post(f"{url}/assessment", json={"self_verdict": "supports_finding"})
    team_a.verifier.post(f"{url}/verdict", json={"verdict": "supports_finding", "rationale": "Bukti tindakan tidak ditemukan"})
    for table in ("cognitive_assessment", "human_verdict"):
        with pytest.raises(DBAPIError) as exc:
            session.execute(text(f"UPDATE {table} SET id = id"))
        assert "append-only" in str(exc.value)
        session.rollback()
        with pytest.raises(DBAPIError):
            session.execute(text(f"DELETE FROM {table}"))
        session.rollback()


def test_confidence_must_stay_within_unit_range(session: Session, world: World, team_a: Actors):
    claim = make_claim(session, world.a, episode_no="EP-DB-4", codes=[("procedure", "SIM-PROC-101")], evidence=RESUME_ONLY)
    submit_and_process(session, team_a.coder, claim)
    with pytest.raises(IntegrityError):
        session.execute(text("UPDATE finding SET confidence = 1.5"))
    session.rollback()


def test_metric_snapshot_identity_is_unique_even_with_null_dimensions(session: Session, world: World):
    start = utcnow() - timedelta(days=1)
    end = utcnow()

    def snapshot() -> MetricSnapshot:
        return MetricSnapshot(
            faskes_id=world.a.faskes_id, metric_code="abstention_rate", window_start=start, window_end=end, value=0
        )

    session.add(snapshot())
    session.flush()
    session.add(snapshot())
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_vector_catalog_and_pgvector_index_are_present(session: Session, world: World):
    assert {v.code for v in session.exec(select(RiskVector))} == {"phantom_billing", "upcoding", "unbundling"}
    definition = session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_evidence_item_embedding_hnsw'")
    ).scalar_one()
    assert "hnsw" in definition and "vector_cosine_ops" in definition
    assert session.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")).scalar_one()


def test_faskes_rows_exist_for_both_tenants(session: Session, world: World):
    names = {f.name for f in session.exec(select(Faskes))}
    assert any("Uji A" in n for n in names) and any("Uji B" in n for n in names)
