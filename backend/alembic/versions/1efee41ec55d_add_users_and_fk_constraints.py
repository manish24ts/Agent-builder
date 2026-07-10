"""add users table and FK constraints on agents/conversations.user_id

Revision ID: 1efee41ec55d
Revises: dc4b14ea260c
Create Date: 2026-07-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1efee41ec55d'
down_revision: Union[str, None] = 'dc4b14ea260c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('google_id', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('google_id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)

    # NOTE: assumes agents/conversations tables are empty at migration time (fresh setup).
    # If you have existing rows with user_ids that don't map to a users row yet,
    # backfill the users table before running this migration, or drop existing rows first.
    op.create_foreign_key(
        'fk_agents_user_id_users', 'agents', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )
    op.create_foreign_key(
        'fk_conversations_user_id_users', 'conversations', 'users', ['user_id'], ['id'], ondelete='CASCADE'
    )

    # agent_id FK on conversations existed without ON DELETE CASCADE — align it.
    op.drop_constraint('conversations_agent_id_fkey', 'conversations', type_='foreignkey')
    op.create_foreign_key(
        'conversations_agent_id_fkey', 'conversations', 'agents', ['agent_id'], ['id'], ondelete='CASCADE'
    )

    op.drop_constraint('messages_conversation_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key(
        'messages_conversation_id_fkey', 'messages', 'conversations', ['conversation_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    op.drop_constraint('messages_conversation_id_fkey', 'messages', type_='foreignkey')
    op.create_foreign_key(
        'messages_conversation_id_fkey', 'messages', 'conversations', ['conversation_id'], ['id']
    )

    op.drop_constraint('conversations_agent_id_fkey', 'conversations', type_='foreignkey')
    op.create_foreign_key(
        'conversations_agent_id_fkey', 'conversations', 'agents', ['agent_id'], ['id']
    )

    op.drop_constraint('fk_conversations_user_id_users', 'conversations', type_='foreignkey')
    op.drop_constraint('fk_agents_user_id_users', 'agents', type_='foreignkey')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
