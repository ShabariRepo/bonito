"""
Permission Service

Handles permission checking for RBAC system
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.role import Role
from app.models.role_assignment import RoleAssignment, ScopeType
from app.models.agent_group import AgentGroup
from app.models.project import Project


class PermissionAction(str, Enum):
    # Project permissions
    MANAGE_PROJECTS = "manage_projects"
    VIEW_PROJECTS = "view_projects"
    
    # Group permissions
    MANAGE_GROUPS = "manage_groups"
    VIEW_GROUPS = "view_groups"
    
    # Agent permissions
    MANAGE_AGENTS = "manage_agents"
    EXECUTE_AGENTS = "execute_agents"
    VIEW_AGENTS = "view_agents"
    
    # Knowledge base permissions
    MANAGE_KNOWLEDGE_BASES = "manage_knowledge_bases"
    VIEW_KNOWLEDGE_BASES = "view_knowledge_bases"
    
    # Session permissions
    VIEW_SESSIONS = "view_sessions"
    
    # Role management permissions
    MANAGE_ROLES = "manage_roles"
    VIEW_ROLES = "view_roles"
    
    # User management permissions
    MANAGE_USERS = "manage_users"
    VIEW_USERS = "view_users"
    
    # Metrics permissions
    VIEW_METRICS = "view_metrics"


class ResourceType(str, Enum):
    ORG = "org"
    PROJECT = "project"
    GROUP = "group"
    AGENT = "agent"
    ALL = "*"


class PermissionService:
    """Service for checking user permissions based on RBAC."""
    
    @staticmethod
    async def get_user_permissions(db: AsyncSession, user: User) -> List[Dict[str, Any]]:
        """Get all effective permissions for a user."""
        stmt = (
            select(RoleAssignment, Role.permissions)
            .join(Role, RoleAssignment.role_id == Role.id)
            .where(
                and_(
                    RoleAssignment.user_id == user.id,
                    RoleAssignment.org_id == user.org_id
                )
            )
        )
        
        result = await db.execute(stmt)
        assignments = result.all()
        
        all_permissions = []
        for assignment, role_permissions in assignments:
            # Add scope context to permissions
            for perm in role_permissions:
                scoped_perm = perm.copy()
                scoped_perm["scope"] = {
                    "type": assignment.scope_type.value,
                    "id": str(assignment.scope_id) if assignment.scope_id else None
                }
                all_permissions.append(scoped_perm)
        
        return all_permissions
    
    @staticmethod
    async def check_permission(
        db: AsyncSession,
        user: User,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission for specific action on resource."""
        
        # Get user's role assignments with permissions
        stmt = (
            select(RoleAssignment, Role.permissions)
            .join(Role, RoleAssignment.role_id == Role.id)
            .where(
                and_(
                    RoleAssignment.user_id == user.id,
                    RoleAssignment.org_id == user.org_id
                )
            )
        )
        
        result = await db.execute(stmt)
        assignments = result.all()
        
        for assignment, role_permissions in assignments:
            if await PermissionService._has_permission_in_role(
                db, role_permissions, assignment, action, resource_type, resource_id
            ):
                return True
        
        return False
    
    @staticmethod
    async def _has_permission_in_role(
        db: AsyncSession,
        permissions: List[Dict[str, Any]],
        assignment: RoleAssignment,
        action: str,
        resource_type: str,
        resource_id: Optional[str]
    ) -> bool:
        """Check if a specific role assignment grants the permission."""
        
        for perm in permissions:
            perm_action = perm.get("action", "")
            perm_resource_type = perm.get("resource_type", "")
            perm_resource_ids = perm.get("resource_ids", [])
            
            # Check action match (supports wildcards)
            if not PermissionService._matches_pattern(action, perm_action):
                continue
            
            # Check resource type match
            if not PermissionService._matches_pattern(resource_type, perm_resource_type):
                continue
            
            # Check resource scope and IDs
            if await PermissionService._check_resource_scope(
                db, assignment, resource_type, resource_id, perm_resource_ids
            ):
                return True
        
        return False
    
    @staticmethod
    def _matches_pattern(value: str, pattern: str) -> bool:
        """Check if value matches pattern (supports wildcards)."""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        return value == pattern
    
    @staticmethod
    async def _check_resource_scope(
        db: AsyncSession,
        assignment: RoleAssignment,
        resource_type: str,
        resource_id: Optional[str],
        perm_resource_ids: List[str]
    ) -> bool:
        """Check if the resource falls within the assignment's scope."""
        
        # If permission resource_ids contains "*", it applies to all resources
        if "*" in perm_resource_ids:
            return await PermissionService._check_scope_access(
                db, assignment, resource_type, resource_id
            )
        
        # If resource_id is specified in permission, check direct match
        if resource_id and resource_id in perm_resource_ids:
            return await PermissionService._check_scope_access(
                db, assignment, resource_type, resource_id
            )
        
        # For scoped permissions, check if resource belongs to the scope
        return await PermissionService._check_scope_access(
            db, assignment, resource_type, resource_id
        )
    
    @staticmethod
    async def _check_scope_access(
        db: AsyncSession,
        assignment: RoleAssignment,
        resource_type: str,
        resource_id: Optional[str]
    ) -> bool:
        """Check if resource is accessible within the assignment's scope."""
        
        # Org-level assignments can access everything in the org
        if assignment.scope_type == ScopeType.ORG:
            return True
        
        # Project-level assignments
        if assignment.scope_type == ScopeType.PROJECT:
            if not assignment.scope_id:
                return False
            
            project_id = assignment.scope_id
            
            if resource_type == "project":
                return not resource_id or str(project_id) == resource_id
            
            if resource_type == "group":
                if not resource_id:
                    return True  # Can access all groups in project
                
                # Check if group belongs to project
                stmt = select(AgentGroup.id).where(
                    and_(
                        AgentGroup.id == UUID(resource_id),
                        AgentGroup.project_id == project_id
                    )
                )
                result = await db.execute(stmt)
                return result.scalar_one_or_none() is not None
            
            if resource_type == "agent":
                if not resource_id:
                    return True  # Can access all agents in project
                
                # Check if agent belongs to project (through group or directly)
                from app.models.agent import Agent
                stmt = select(Agent.id).where(
                    and_(
                        Agent.id == UUID(resource_id),
                        Agent.project_id == project_id
                    )
                )
                result = await db.execute(stmt)
                return result.scalar_one_or_none() is not None
        
        # Group-level assignments
        if assignment.scope_type == ScopeType.GROUP:
            if not assignment.scope_id:
                return False
            
            group_id = assignment.scope_id
            
            if resource_type == "group":
                return not resource_id or str(group_id) == resource_id
            
            if resource_type == "agent":
                if not resource_id:
                    return True  # Can access all agents in group
                
                # Check if agent belongs to group
                from app.models.agent import Agent
                stmt = select(Agent.id).where(
                    and_(
                        Agent.id == UUID(resource_id),
                        Agent.group_id == group_id
                    )
                )
                result = await db.execute(stmt)
                return result.scalar_one_or_none() is not None
        
        return False
    
    @staticmethod
    async def filter_resources_by_permission(
        db: AsyncSession,
        user: User,
        action: str,
        resource_type: str,
        resource_ids: List[str]
    ) -> List[str]:
        """Filter a list of resource IDs to only those the user has permission for."""
        allowed_resources = []
        
        for resource_id in resource_ids:
            if await PermissionService.check_permission(db, user, action, resource_type, resource_id):
                allowed_resources.append(resource_id)
        
        return allowed_resources
    
    @staticmethod
    async def get_accessible_project_ids(db: AsyncSession, user: User) -> List[UUID]:
        """Get project IDs the user has any access to."""
        stmt = (
            select(RoleAssignment.scope_id)
            .where(
                and_(
                    RoleAssignment.user_id == user.id,
                    RoleAssignment.org_id == user.org_id,
                    RoleAssignment.scope_type == ScopeType.PROJECT
                )
            )
        )
        result = await db.execute(stmt)
        project_scopes = [row[0] for row in result.all() if row[0]]
        
        # Also include org-level access (can see all projects)
        org_stmt = select(RoleAssignment.id).where(
            and_(
                RoleAssignment.user_id == user.id,
                RoleAssignment.org_id == user.org_id,
                RoleAssignment.scope_type == ScopeType.ORG
            )
        )
        org_result = await db.execute(org_stmt)
        has_org_access = org_result.scalar_one_or_none() is not None
        
        if has_org_access:
            # Return all project IDs in org
            all_projects_stmt = select(Project.id).where(Project.org_id == user.org_id)
            all_result = await db.execute(all_projects_stmt)
            return [row[0] for row in all_result.all()]
        
        return project_scopes
    
    @staticmethod
    async def get_accessible_group_ids(db: AsyncSession, user: User) -> List[UUID]:
        """Get group IDs the user has any access to."""
        # Group-level access
        group_stmt = (
            select(RoleAssignment.scope_id)
            .where(
                and_(
                    RoleAssignment.user_id == user.id,
                    RoleAssignment.org_id == user.org_id,
                    RoleAssignment.scope_type == ScopeType.GROUP
                )
            )
        )
        result = await db.execute(group_stmt)
        group_scopes = [row[0] for row in result.all() if row[0]]
        
        # Project-level access (can see groups in those projects)
        accessible_projects = await PermissionService.get_accessible_project_ids(db, user)
        if accessible_projects:
            project_groups_stmt = select(AgentGroup.id).where(
                AgentGroup.project_id.in_(accessible_projects)
            )
            project_result = await db.execute(project_groups_stmt)
            group_scopes.extend([row[0] for row in project_result.all()])
        
        return list(set(group_scopes))  # Remove duplicates


# Convenience functions for FastAPI dependencies
async def check_permission(
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None
):
    """Factory function to create permission checking dependencies."""
    from fastapi import Depends, HTTPException
    from app.api.dependencies import get_current_user
    from app.core.database import get_db
    
    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> bool:
        has_permission = await PermissionService.check_permission(
            db, current_user, action, resource_type, resource_id
        )
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {action} on {resource_type}"
            )
        return True
    
    return _check


def require_permission(action: str, resource_type: str, resource_id: Optional[str] = None):
    """Dependency that raises 403 if user lacks permission."""
    from fastapi import Depends
    return Depends(check_permission(action, resource_type, resource_id))