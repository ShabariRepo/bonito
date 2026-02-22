"""Add RBAC and Agent Groups

Revision ID: 021_add_rbac_groups  
Revises: 020_add_bonobot_tables
Create Date: 2026-02-19

Adds Role-Based Access Control and Agent Groups functionality:
- agent_groups: Department/team-based organization of agents with KB isolation
- roles: Enhanced role system with granular permissions  
- role_assignments: User role assignments with resource scoping
- Adds group_id to agents table for group membership
- Seeds managed roles and migrates existing users
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
import json

# revision identifiers
revision = "021_add_rbac_groups"
down_revision = "020_add_bonobot_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scope_type enum (checkfirst + create_type=False to prevent auto-creation during table build)
    scope_type_enum = postgresql.ENUM('org', 'project', 'group', name='scope_type', create_type=False)
    scope_type_enum.create(op.get_bind(), checkfirst=True)
    
    # ─── Agent Groups Table ───
    op.create_table(
        "agent_groups",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        
        # Knowledge Base Isolation
        sa.Column("knowledge_base_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        
        # Group-level Settings
        sa.Column("budget_limit", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("model_allowlist", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("tool_policy", sa.JSON(), nullable=False, server_default=sa.text("'{\"mode\": \"inherit\", \"allowed\": [], \"denied\": []}'")),
        
        # Visual Grouping (for React Flow canvas)
        sa.Column("canvas_position", sa.JSON(), nullable=True, server_default=sa.text("'{\"x\": 0, \"y\": 0}'")),
        sa.Column("canvas_style", sa.JSON(), nullable=True, server_default=sa.text("'{\"backgroundColor\": \"#f0f0f0\", \"borderColor\": \"#ccc\"}'")),
        
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─── Roles Table ───
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_managed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_roles_org_name"),
    )

    # ─── Role Assignments Table ───
    op.create_table(
        "role_assignments",
        sa.Column("id", sa.Uuid(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("org_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_type", scope_type_enum, nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", "scope_type", "scope_id", name="uq_role_assignments_unique"),
    )

    # ─── Add group_id to agents table ───
    op.add_column("agents", sa.Column("group_id", sa.Uuid(), sa.ForeignKey("agent_groups.id", ondelete="SET NULL"), nullable=True))

    # ─── Create Indexes ───
    op.create_index("idx_agent_groups_project_id", "agent_groups", ["project_id"])
    op.create_index("idx_agent_groups_org_id", "agent_groups", ["org_id"])
    op.create_index("idx_roles_org_id", "roles", ["org_id"])
    op.create_index("idx_roles_managed", "roles", ["is_managed"])
    op.create_index("idx_role_assignments_user_id", "role_assignments", ["user_id"])
    op.create_index("idx_role_assignments_role_id", "role_assignments", ["role_id"])
    op.create_index("idx_role_assignments_scope", "role_assignments", ["scope_type", "scope_id"])
    op.create_index("idx_agents_group_id", "agents", ["group_id"])

    # ─── Seed Managed Roles ───
    # Define managed roles with their permissions
    managed_roles = [
        {
            "name": "org_admin",
            "description": "Full access to everything in the organization",
            "permissions": [{"action": "*", "resource_type": "*", "resource_ids": ["*"]}]
        },
        {
            "name": "project_admin",
            "description": "Manage specific projects, groups, and agents within them",
            "permissions": [
                {"action": "manage_projects", "resource_type": "project", "resource_ids": ["*"]},
                {"action": "manage_groups", "resource_type": "project", "resource_ids": ["*"]},
                {"action": "manage_agents", "resource_type": "project", "resource_ids": ["*"]},
                {"action": "view_sessions", "resource_type": "project", "resource_ids": ["*"]},
                {"action": "execute_agents", "resource_type": "project", "resource_ids": ["*"]},
                {"action": "manage_knowledge_bases", "resource_type": "project", "resource_ids": ["*"]}
            ]
        },
        {
            "name": "group_manager", 
            "description": "Manage agents and context within assigned groups",
            "permissions": [
                {"action": "manage_agents", "resource_type": "group", "resource_ids": ["*"]},
                {"action": "manage_knowledge_bases", "resource_type": "group", "resource_ids": ["*"]},
                {"action": "view_sessions", "resource_type": "group", "resource_ids": ["*"]},
                {"action": "execute_agents", "resource_type": "group", "resource_ids": ["*"]},
                {"action": "view_agents", "resource_type": "group", "resource_ids": ["*"]}
            ]
        },
        {
            "name": "agent_operator",
            "description": "Execute agents and view sessions, but cannot create/edit agents", 
            "permissions": [
                {"action": "execute_agents", "resource_type": "*", "resource_ids": ["*"]},
                {"action": "view_sessions", "resource_type": "*", "resource_ids": ["*"]},
                {"action": "view_agents", "resource_type": "*", "resource_ids": ["*"]}
            ]
        },
        {
            "name": "viewer",
            "description": "Read-only access to dashboards and metrics",
            "permissions": [
                {"action": "view_*", "resource_type": "*", "resource_ids": ["*"]}
            ]
        }
    ]

    # Create roles for each organization
    connection = op.get_bind()
    
    # Get all organizations
    org_result = connection.execute(sa.text("SELECT id FROM organizations"))
    orgs = org_result.fetchall()
    
    for org in orgs:
        org_id = org[0]
        for role_def in managed_roles:
            role_id = str(uuid.uuid4())
            connection.execute(
                sa.text("""
                    INSERT INTO roles (id, org_id, name, description, is_managed, permissions)
                    VALUES (:id, :org_id, :name, :description, true, :permissions)
                """),
                {
                    "id": role_id,
                    "org_id": str(org_id),
                    "name": role_def["name"],
                    "description": role_def["description"],
                    "permissions": json.dumps(role_def["permissions"])
                }
            )
    
    # ─── Migrate Existing Users ───
    # Map current user roles to new managed roles with org scope
    role_mapping = {
        "admin": "org_admin",
        "member": "project_admin", 
        "viewer": "viewer"
    }
    
    # Get all users
    user_result = connection.execute(sa.text("SELECT id, org_id, role FROM users WHERE role IS NOT NULL"))
    users = user_result.fetchall()
    
    for user in users:
        user_id, user_org_id, current_role = user
        
        # Map to new role system
        new_role_name = role_mapping.get(current_role, "viewer")
        
        # Find the corresponding managed role
        role_result = connection.execute(
            sa.text("""
                SELECT id FROM roles 
                WHERE org_id = :org_id AND name = :name AND is_managed = true
            """),
            {"org_id": str(user_org_id), "name": new_role_name}
        )
        role_row = role_result.fetchone()
        
        if role_row:
            role_id = role_row[0]
            assignment_id = str(uuid.uuid4())
            
            # Create org-scoped role assignment
            connection.execute(
                sa.text("""
                    INSERT INTO role_assignments (id, user_id, role_id, org_id, scope_type, scope_id)
                    VALUES (:id, :user_id, :role_id, :org_id, 'org', NULL)
                """),
                {
                    "id": assignment_id,
                    "user_id": str(user_id),
                    "role_id": str(role_id),
                    "org_id": str(user_org_id)
                }
            )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_agents_group_id", table_name="agents")
    op.drop_index("idx_role_assignments_scope", table_name="role_assignments")
    op.drop_index("idx_role_assignments_role_id", table_name="role_assignments")
    op.drop_index("idx_role_assignments_user_id", table_name="role_assignments")
    op.drop_index("idx_roles_managed", table_name="roles")
    op.drop_index("idx_roles_org_id", table_name="roles")
    op.drop_index("idx_agent_groups_org_id", table_name="agent_groups")
    op.drop_index("idx_agent_groups_project_id", table_name="agent_groups")

    # Drop group_id from agents
    op.drop_column("agents", "group_id")
    
    # Drop tables in reverse order of dependencies
    op.drop_table("role_assignments")
    op.drop_table("roles")
    op.drop_table("agent_groups")
    
    # Drop enum
    op.execute("DROP TYPE scope_type")