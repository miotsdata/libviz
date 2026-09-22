"""drop unique constraint on smiles and pubchem_id

Revision ID: e1a2b3c4d5f6
Revises: c97671612f06
Create Date: 2026-09-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5f6'
down_revision: Union[str, Sequence[str], None] = 'c97671612f06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('compound', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_compound_smiles'))
        batch_op.drop_index(batch_op.f('ix_compound_pubchem_id'))
        batch_op.create_index(batch_op.f('ix_compound_smiles'), ['smiles'], unique=False)
        batch_op.create_index(batch_op.f('ix_compound_pubchem_id'), ['pubchem_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('compound', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_compound_pubchem_id'))
        batch_op.drop_index(batch_op.f('ix_compound_smiles'))
        batch_op.create_index(batch_op.f('ix_compound_smiles'), ['smiles'], unique=True)
        batch_op.create_index(batch_op.f('ix_compound_pubchem_id'), ['pubchem_id'], unique=True)
