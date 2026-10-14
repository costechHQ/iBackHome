"""Create the evidence, suppliers and material_orders tables.

Revision ID: create_evidence_and_suppliers
Revises: create_boq
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "create_evidence_and_suppliers"
down_revision: str | Sequence[str] | None = "create_boq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "evidence",
        *_base_columns(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("milestone_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("captured_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("captured_by_role", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("storage_key", sa.String(300), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy_m", sa.Float(), nullable=False),
        sa.Column("device_id", sa.String(128), nullable=False),
        sa.Column("signature", sa.Text(), nullable=False),
        sa.Column("phash", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(16), server_default="pending_checks", nullable=False),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_evidence"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_evidence_project_id_projects"),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"], name="fk_evidence_milestone_id_milestones"),
        sa.ForeignKeyConstraint(["captured_by"], ["users.id"], name="fk_evidence_captured_by_users"),
        sa.UniqueConstraint("storage_key", name="uq_evidence_storage_key"),
        sa.CheckConstraint("kind IN ('photo', 'video')", name=op.f("ck_evidence_kind_valid")),
        sa.CheckConstraint(
            "status IN ('pending_checks', 'accepted', 'flagged', 'rejected')",
            name=op.f("ck_evidence_status_valid"),
        ),
        sa.CheckConstraint(
            "captured_by_role IN ('supervisor', 'contractor')", name=op.f("ck_evidence_captured_by_role_valid")
        ),
        sa.CheckConstraint(
            "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180",
            name=op.f("ck_evidence_coords_valid"),
        ),
        sa.CheckConstraint("accuracy_m >= 0", name=op.f("ck_evidence_accuracy_non_negative")),
    )
    op.create_index("ix_evidence_project_id", "evidence", ["project_id"])
    op.create_index("ix_evidence_milestone_id", "evidence", ["milestone_id"])
    op.create_index("ix_evidence_phash", "evidence", ["phash"])

    op.create_table(
        "suppliers",
        *_base_columns(),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("paystack_recipient_code", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_suppliers"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_suppliers_owner_id_users"),
    )
    op.create_index("ix_suppliers_owner_id", "suppliers", ["owner_id"])

    op.create_table(
        "material_orders",
        *_base_columns(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("total_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(16), server_default="requested", nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_material_orders"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name="fk_material_orders_project_id_projects"),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name="fk_material_orders_supplier_id_suppliers"
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], name="fk_material_orders_requested_by_users"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name="fk_material_orders_approved_by_users"),
        sa.CheckConstraint(
            "status IN ('requested', 'approved', 'delivered', 'paid', 'cancelled')",
            name=op.f("ck_material_orders_status_valid"),
        ),
        sa.CheckConstraint("total_minor > 0", name=op.f("ck_material_orders_total_positive")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_material_orders_currency_iso4217")),
    )
    op.create_index("ix_material_orders_project_id", "material_orders", ["project_id"])
    op.create_index("ix_material_orders_supplier_id", "material_orders", ["supplier_id"])


def downgrade() -> None:
    op.drop_table("material_orders")
    op.drop_table("suppliers")
    op.drop_table("evidence")
