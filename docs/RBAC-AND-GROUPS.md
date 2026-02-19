# RBAC and Agent Groups Architecture

## Overview

This document describes the design and implementation of two critical features for the Bonito platform:

1. **Agent Groups/Departments** - Organizing agents into isolated groups with their own knowledge bases and settings
2. **Role-Based Access Control (RBAC)** - Granular permissions system for controlling access to agents, groups, and projects

## Current State

The platform currently has:
- Basic roles (`admin`, `member`, `viewer`) stored in `users.role` 
- JWT tokens containing `{sub, org_id, role, type}`
- Organization-level isolation
- Agent model with `knowledge_base_ids` as JSON array
- Project → Agent hierarchy

## New Architecture

### Database Schema

#### 1. Agent Groups Table

```sql
CREATE TABLE agent_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Knowledge Base Isolation
    knowledge_base_ids JSON NOT NULL DEFAULT '[]',  -- Array of KB UUIDs for this group
    
    -- Group-level Settings
    budget_limit DECIMAL(10,2),  -- Monthly budget cap for this group
    model_allowlist JSON NOT NULL DEFAULT '[]',  -- Models this group can use ["gpt-4", "claude-3"]
    tool_policy JSON NOT NULL DEFAULT '{"mode": "inherit", "allowed": [], "denied": []}',
    
    -- Visual Grouping (for React Flow canvas)
    canvas_position JSON DEFAULT '{"x": 0, "y": 0}',
    canvas_style JSON DEFAULT '{"backgroundColor": "#f0f0f0", "borderColor": "#ccc"}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_groups_project_id ON agent_groups(project_id);
CREATE INDEX idx_agent_groups_org_id ON agent_groups(org_id);
```

#### 2. Enhanced Roles Table

```sql
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_managed BOOLEAN NOT NULL DEFAULT false,  -- Built-in roles cannot be deleted
    
    -- Permissions as JSON array of permission objects
    permissions JSON NOT NULL DEFAULT '[]',
    -- Example: [
    --   {"action": "manage_agents", "resource_type": "group", "resource_ids": ["group-uuid"]},
    --   {"action": "view_sessions", "resource_type": "project", "resource_ids": ["*"]}
    -- ]
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(org_id, name)
);

CREATE INDEX idx_roles_org_id ON roles(org_id);
CREATE INDEX idx_roles_managed ON roles(is_managed);
```

#### 3. Role Assignments Table

```sql
CREATE TYPE scope_type AS ENUM ('org', 'project', 'group');

CREATE TABLE role_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Scope defines WHERE this role applies
    scope_type scope_type NOT NULL,
    scope_id UUID,  -- NULL for org-level, project_id for project-level, group_id for group-level
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, role_id, scope_type, scope_id)
);

CREATE INDEX idx_role_assignments_user_id ON role_assignments(user_id);
CREATE INDEX idx_role_assignments_role_id ON role_assignments(role_id);
CREATE INDEX idx_role_assignments_scope ON role_assignments(scope_type, scope_id);
```

#### 4. Update Agents Table

```sql
ALTER TABLE agents ADD COLUMN group_id UUID REFERENCES agent_groups(id) ON DELETE SET NULL;
CREATE INDEX idx_agents_group_id ON agents(group_id);
```

### Permission Model

#### Built-in Managed Roles

These roles are created during migration and cannot be deleted:

```json
[
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
      {"action": "execute_agents", "resource_type": "project", "resource_ids": ["*"]}
    ]
  },
  {
    "name": "group_manager",
    "description": "Manage agents and context within assigned groups",
    "permissions": [
      {"action": "manage_agents", "resource_type": "group", "resource_ids": ["*"]},
      {"action": "manage_knowledge_bases", "resource_type": "group", "resource_ids": ["*"]},
      {"action": "view_sessions", "resource_type": "group", "resource_ids": ["*"]},
      {"action": "execute_agents", "resource_type": "group", "resource_ids": ["*"]}
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
```

#### Permission Actions

Standard actions that can be granted:

- `manage_projects` - Create, update, delete projects
- `manage_groups` - Create, update, delete agent groups  
- `manage_agents` - Create, update, delete agents
- `execute_agents` - Run agents and create sessions
- `manage_knowledge_bases` - Upload, update, delete knowledge bases
- `view_sessions` - Read agent sessions and messages
- `view_agents` - Read agent configurations
- `view_metrics` - Access dashboards and analytics
- `manage_roles` - Create custom roles and assignments (org_admin only)

#### Resource Types

- `org` - Organization-wide permissions
- `project` - Project-specific permissions  
- `group` - Group-specific permissions
- `agent` - Individual agent permissions (for fine-grained control)

### Knowledge Base Isolation

#### Current Model
```python
# Agent model currently has:
knowledge_base_ids: List[UUID]  # Direct assignment to agent
```

#### New Model with Group Inheritance
```python
# Agent inherits from group by default, with optional overrides
class Agent:
    group_id: Optional[UUID]  # References agent_groups.id
    knowledge_base_ids: List[UUID]  # Agent-specific overrides (empty = inherit from group)

class AgentGroup:
    knowledge_base_ids: List[UUID]  # Group's default KBs
```

#### Resolution Logic
```python
def get_agent_knowledge_bases(agent: Agent, group: Optional[AgentGroup]) -> List[UUID]:
    """Get effective knowledge bases for an agent."""
    if agent.knowledge_base_ids:
        # Agent has explicit KB overrides
        return agent.knowledge_base_ids
    elif group and group.knowledge_base_ids:
        # Inherit from group
        return group.knowledge_base_ids
    else:
        # No KBs available
        return []
```

### API Design

#### Agent Groups Endpoints

```python
# Group CRUD
POST   /api/projects/{project_id}/groups                    # Create group
GET    /api/projects/{project_id}/groups                    # List groups in project
GET    /api/groups/{group_id}                               # Get group details  
PUT    /api/groups/{group_id}                               # Update group
DELETE /api/groups/{group_id}                               # Delete group

# Group agents
GET    /api/groups/{group_id}/agents                        # List agents in group
POST   /api/groups/{group_id}/agents/{agent_id}/assign     # Assign agent to group
POST   /api/groups/{group_id}/agents/{agent_id}/unassign   # Remove agent from group

# Knowledge base management per group
POST   /api/groups/{group_id}/knowledge-bases              # Upload KB to group
GET    /api/groups/{group_id}/knowledge-bases              # List group KBs
DELETE /api/groups/{group_id}/knowledge-bases/{kb_id}      # Remove KB from group
```

#### RBAC Endpoints

```python
# Role management (org_admin only)
POST   /api/roles                          # Create custom role
GET    /api/roles                          # List all roles in org
GET    /api/roles/{role_id}                # Get role details
PUT    /api/roles/{role_id}                # Update custom role
DELETE /api/roles/{role_id}                # Delete custom role (managed=false only)

# Role assignments
POST   /api/role-assignments               # Assign role to user with scope
GET    /api/role-assignments               # List assignments (filtered by permissions)
DELETE /api/role-assignments/{assignment_id}  # Remove role assignment

# User role queries
GET    /api/users/{user_id}/roles          # Get user's effective roles
GET    /api/users/{user_id}/permissions    # Get user's effective permissions
```

#### Updated Agent Endpoints

```python
# Modified to respect group permissions and KB inheritance
GET    /api/projects/{project_id}/agents   # Now filters by user's group access
POST   /api/projects/{project_id}/agents   # Requires manage_agents on project/group
PUT    /api/agents/{agent_id}              # Requires manage_agents on agent's group
POST   /api/agents/{agent_id}/execute      # Requires execute_agents permission
```

### Authentication & Authorization

#### JWT Token Enhancement

Current tokens contain `{sub, org_id, role, type}`. This will be enhanced to include role assignments:

```json
{
  "sub": "user-uuid",
  "org_id": "org-uuid", 
  "type": "access",
  "roles": [
    {"role_id": "role-uuid", "scope_type": "org", "scope_id": null},
    {"role_id": "role-uuid", "scope_type": "group", "scope_id": "group-uuid"}
  ]
}
```

#### Permission Checking Middleware

```python
from typing import List, Optional
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

async def check_permission(
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> bool:
    """Check if user has permission for the given action on resource."""
    
    # Get user's role assignments
    stmt = select(RoleAssignment, Role).join(Role).where(
        RoleAssignment.user_id == user.id,
        RoleAssignment.org_id == user.org_id
    )
    result = await db.execute(stmt)
    assignments = result.all()
    
    for assignment, role in assignments:
        # Check if role grants this permission
        if has_permission(role.permissions, action, resource_type, resource_id, assignment):
            return True
    
    return False

def require_permission(action: str, resource_type: str, resource_id: Optional[str] = None):
    """Dependency that raises 403 if user lacks permission."""
    async def _check(authorized: bool = Depends(lambda: check_permission(action, resource_type, resource_id))):
        if not authorized:
            raise HTTPException(status_code=403, detail=f"Permission denied: {action} on {resource_type}")
    return Depends(_check)

# Usage in routes:
@router.post("/agents/{agent_id}/execute")
async def execute_agent(
    agent_id: UUID,
    _: None = Depends(require_permission("execute_agents", "agent", str(agent_id))),
    # ... rest of the function
):
```

### Migration Strategy

#### Backward Compatibility

1. **Existing users**: Current `users.role` field maps to managed roles
   - `admin` → `org_admin` role assignment
   - `member` → `project_admin` role assignment on all projects
   - `viewer` → `viewer` role assignment

2. **Existing agents**: All agents remain functional
   - Agents without `group_id` continue using direct `knowledge_base_ids`
   - No changes to existing agent execution

3. **JWT tokens**: Enhanced gradually
   - Old tokens still work (fallback to `users.role`)
   - New tokens include role assignments
   - Token refresh provides new format

#### Migration Steps

1. **021_add_rbac_groups.py** - Create new tables
2. **Seed managed roles** - Insert built-in roles
3. **Migrate existing users** - Create role assignments based on current `users.role`
4. **Update JWT service** - Enhance token generation
5. **Update permission middleware** - Support new system
6. **Frontend updates** - Add group and role management UIs

### Frontend Integration

#### React Flow Canvas Updates

Groups appear as visual containers on the canvas:

```typescript
interface GroupNode {
  id: string;
  type: 'group';
  position: { x: number; y: number };
  data: {
    id: string;
    name: string;
    description?: string;
    agentCount: number;
    style: {
      backgroundColor: string;
      borderColor: string;
    };
  };
}

// Agents render inside group boundaries
interface AgentNode {
  id: string;
  type: 'agent';
  parentNode: string; // group ID
  position: { x: number; y: number; }; // relative to group
  extent: 'parent'; // constrain to group bounds
  data: { /* agent data */ };
}
```

#### Group Management UI

New pages in the project settings:

1. **Groups Tab** - Create/edit/delete groups
2. **Roles Tab** - Manage custom roles (admin only)  
3. **Users Tab** - Assign roles to users with scopes

#### Permission-Based UI

Components check user permissions to show/hide features:

```typescript
const { hasPermission } = usePermissions();

// Only show "Create Agent" if user can manage agents in this context
{hasPermission('manage_agents', 'group', groupId) && (
  <CreateAgentButton />
)}
```

### Security Considerations

1. **Least Privilege**: Users get minimal permissions by default
2. **Scope Isolation**: Group managers cannot access other groups
3. **Audit Trail**: All role assignments and permission changes logged
4. **Resource Validation**: Always verify resource belongs to user's org
5. **Token Security**: Role assignments embedded in JWT prevent database lookup on every request

### Performance Optimizations

1. **Permission Caching**: Cache role lookups in Redis
2. **Bulk Permission Checks**: Single query for multiple permission checks
3. **JWT Embedding**: Include common permissions in token to reduce DB calls
4. **Index Strategy**: Proper indexes on role assignments and scopes

### Example Use Cases

#### AdTech Team Setup

1. Admin creates "AdTech" group in Marketing project
2. Admin uploads AdTech-specific knowledge bases to the group
3. Admin creates custom role "AdTech Agent Manager" with group-scoped permissions
4. Admin assigns AdTech team lead the custom role scoped to AdTech group
5. AdTech team lead creates agents that inherit AdTech KBs automatically
6. Other teams cannot access AdTech's knowledge bases or agents

#### Finance Department Isolation

1. Admin creates "Finance" group with strict budget limits
2. Finance uploads sensitive financial documents to group KBs
3. Finance agents inherit financial KBs and budget constraints
4. Non-finance users cannot view/execute finance agents due to RBAC
5. Finance team manages their own agents without admin intervention

## Implementation Plan

### Phase 1: Database & Backend (Week 1)
- [ ] Create migration 021_add_rbac_groups
- [ ] Add SQLAlchemy models for new tables
- [ ] Seed managed roles
- [ ] Create role assignment migration for existing users

### Phase 2: Authentication & Authorization (Week 2)  
- [ ] Enhance JWT token generation with role assignments
- [ ] Implement permission checking middleware
- [ ] Update agent routes with permission checks
- [ ] Create groups and roles API endpoints

### Phase 3: Knowledge Base Integration (Week 3)
- [ ] Update agent execution to respect group KB inheritance  
- [ ] Add group KB management endpoints
- [ ] Test KB isolation between groups

### Phase 4: Frontend Implementation (Week 4)
- [ ] Add group management UI to project settings
- [ ] Update React Flow canvas to show groups as containers
- [ ] Implement role management interface (admin only)
- [ ] Add permission-based UI controls

### Phase 5: Testing & Polish (Week 5)
- [ ] Comprehensive permission testing
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] Migration validation

This architecture provides a robust foundation for enterprise-grade agent management with proper access controls and organizational structure.