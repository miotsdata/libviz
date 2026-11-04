"""add spectrum.rt (retention time, minutes), filled from RT metadata

Revision ID: b5d1e2f3a4c7
Revises: e1a2b3c4d5f6
Create Date: 2026-11-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b5d1e2f3a4c7'
down_revision: Union[str, Sequence[str], None] = 'e1a2b3c4d5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Metadata keys that held RT before the column existed -> factor to minutes.
# Copied, not moved: the original key stays as provenance.
RT_KEYS = {"RT_MIN": 1.0, "RETENTIONTIME": 1.0, "RETENTION_TIME": 1.0, "RT": 1.0,
           "RTINMINUTES": 1.0, "RTINSECONDS": 1 / 60}


def upgrade() -> None:
    with op.batch_alter_table('spectrum', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rt', sa.Float(), nullable=True))
        batch_op.create_index(batch_op.f('ix_spectrum_rt'), ['rt'], unique=False)

    conn = op.get_bind()
    rows = conn.exec_driver_sql(
        "SELECT spectrum_id, UPPER(key), value FROM spectrum_metadata WHERE UPPER(key) IN (%s) ORDER BY id"
        % ",".join("?" * len(RT_KEYS)), tuple(RT_KEYS)).fetchall()
    updates = {}
    for spectrum_id, key, value in rows:
        try:
            rt = float(str(value).strip().replace(",", ".")) * RT_KEYS[key]
        except ValueError:
            continue  # free text ("n/a"): stays metadata only
        updates.setdefault(spectrum_id, rt)  # first parsable key wins
    if updates:
        conn.exec_driver_sql("UPDATE spectrum SET rt = ? WHERE id = ?",
                             [(rt, sid) for sid, rt in updates.items()])


def downgrade() -> None:
    with op.batch_alter_table('spectrum', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_spectrum_rt'))
        batch_op.drop_column('rt')
