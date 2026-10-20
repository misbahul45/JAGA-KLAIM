"""claim code supersede and job requester

Revision ID: 90aa7d290da9
Revises: 53036b308906
Create Date: 2026-10-20 23:21:59.266280
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '90aa7d290da9'
down_revision: Union[str, Sequence[str], None] = '53036b308906'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claim_code', sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('investigation_job', sa.Column('requested_by', sa.Uuid(), nullable=True))
    op.add_column('investigation_job', sa.Column('reason', sa.Text(), nullable=True))
    op.create_index(op.f('ix_investigation_job_requested_by'), 'investigation_job', ['requested_by'], unique=False)
    op.create_foreign_key(op.f('fk_investigation_job_requested_by_app_user'), 'investigation_job', 'app_user', ['requested_by'], ['id'])


def downgrade() -> None:
    op.drop_constraint(op.f('fk_investigation_job_requested_by_app_user'), 'investigation_job', type_='foreignkey')
    op.drop_index(op.f('ix_investigation_job_requested_by'), table_name='investigation_job')
    op.drop_column('investigation_job', 'reason')
    op.drop_column('investigation_job', 'requested_by')
    op.drop_column('claim_code', 'superseded_at')
