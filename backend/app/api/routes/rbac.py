"""
RBAC API Routes

Role-based access control management endpoints
"""

from typing import List, Optional
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.role import Role
from app.models.role_assignment import RoleAssignment, ScopeType
from app.models.project import Project
from app.models.agent_group import AgentGroup
from app.schemas.bonobot import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleAssignmentCreate,
    RoleAssignmentResponse,
    UserPermissionResponse,
    ScopeType as ScopeTypeSchema
)
from app.services.feature_gate import feature_gate

router = APIRouter()


async def _require_rbac(db: AsyncSession, user: User):
    """Check that the organization has access to the RBAC feature (Enterprise only)."""
    await feature_gate.require_feature(db, str(user.org_id), "rbac")


# ─── Role Management ───

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a custom role. Only org_admin can create roles."""
    await _require_rbac(db, current_user)
    # TODO: Check permission - require org_admin role
    
    # Check if role name already exists in org
    stmt = select(Role).where(
        and_(
            Role.org_id == current_user.org_id,
            Role.name == role_data.name
        )
    )
    result = await db.execute(stmt)
    existing_role = result.scalar_one_or_none()
    
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role name already exists"
        )
    
    # Create role
    role = Role(
        org_id=current_user.org_id,
        name=role_data.name,
        description=role_data.description,
        is_managed=False,  # Custom roles are not managed
        permissions=role_data.permissions
    )
    
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    return RoleResponse.model_validate(role)


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all roles in the organization."""
    await _require_rbac(db, current_user)
    # TODO: Check permission - require appropriate access
    
    stmt = select(Role).where(Role.org_id == current_user.org_id).order_by(Role.is_managed.desc(), Role.name)
    result = await db.execute(stmt)
    roles = result.scalars().all()
    
    return [RoleResponse.model_validate(role) for role in roles]


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get role details."""
    await _require_rbac(db, current_user)
    stmt = select(Role).where(
        and_(
            Role.id == role_id,
            Role.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # TODO: Check permission - require appropriate access
    
    return RoleResponse.model_validate(role)


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a custom role. Managed roles cannot be updated."""
    await _require_rbac(db, current_user)
    stmt = select(Role).where(
        and_(
            Role.id == role_id,
            Role.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if role.is_managed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Managed roles cannot be updated"
        )
    
    # TODO: Check permission - require org_admin role
    
    # Check for name conflicts if name is being changed
    if role_data.name and role_data.name != role.name:
        stmt = select(Role).where(
            and_(
                Role.org_id == current_user.org_id,
                Role.name == role_data.name
            )
        )
        result = await db.execute(stmt)
        existing_role = result.scalar_one_or_none()
        
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists"
            )
    
    # Update fields
    update_data = role_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    
    await db.commit()
    await db.refresh(role)
    
    return RoleResponse.model_validate(role)


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a custom role. Managed roles cannot be deleted."""
    await _require_rbac(db, current_user)
    stmt = select(Role).where(
        and_(
            Role.id == role_id,
            Role.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    if role.is_managed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Managed roles cannot be deleted"
        )
    
    # TODO: Check permission - require org_admin role
    
    # Check if role is assigned to any users
    stmt = select(RoleAssignment).where(RoleAssignment.role_id == role_id)
    result = await db.execute(stmt)
    assignments = result.scalars().all()
    
    if assignments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role is assigned to users and cannot be deleted"
        )
    
    await db.delete(role)
    await db.commit()


# ─── Role Assignments ───

@router.post("/role-assignments", response_model=RoleAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_role_assignment(
    assignment_data: RoleAssignmentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign a role to a user with specific scope."""
    await _require_rbac(db, current_user)
    # Verify user exists and is in same org
    stmt = select(User).where(
        and_(
            User.id == assignment_data.user_id,
            User.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify role exists and is in same org
    stmt = select(Role).where(
        and_(
            Role.id == assignment_data.role_id,
            Role.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Validate scope
    scope_name = None
    if assignment_data.scope_type == ScopeTypeSchema.PROJECT:
        if not assignment_data.scope_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope_id required for project scope"
            )
        
        # Verify project exists
        stmt = select(Project).where(
            and_(
                Project.id == assignment_data.scope_id,
                Project.org_id == current_user.org_id
            )
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        scope_name = project.name
        
    elif assignment_data.scope_type == ScopeTypeSchema.GROUP:
        if not assignment_data.scope_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope_id required for group scope"
            )
        
        # Verify group exists
        stmt = select(AgentGroup).where(
            and_(
                AgentGroup.id == assignment_data.scope_id,
                AgentGroup.org_id == current_user.org_id
            )
        )
        result = await db.execute(stmt)
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent group not found"
            )
        
        scope_name = group.name
        
    elif assignment_data.scope_type == ScopeTypeSchema.ORG:
        if assignment_data.scope_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scope_id should be null for org scope"
            )
    
    # TODO: Check permission - require appropriate role assignment permissions
    
    # Check if assignment already exists
    stmt = select(RoleAssignment).where(
        and_(
            RoleAssignment.user_id == assignment_data.user_id,
            RoleAssignment.role_id == assignment_data.role_id,
            RoleAssignment.scope_type == assignment_data.scope_type,
            RoleAssignment.scope_id == assignment_data.scope_id
        )
    )
    result = await db.execute(stmt)
    existing_assignment = result.scalar_one_or_none()
    
    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role assignment already exists"
        )
    
    # Create assignment
    assignment = RoleAssignment(
        user_id=assignment_data.user_id,
        role_id=assignment_data.role_id,
        org_id=current_user.org_id,
        scope_type=ScopeType(assignment_data.scope_type.value),
        scope_id=assignment_data.scope_id
    )
    
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    
    # Create response with populated names
    response = RoleAssignmentResponse.model_validate(assignment)
    response.user_name = target_user.name
    response.role_name = role.name
    response.scope_name = scope_name
    
    return response


@router.get("/role-assignments", response_model=List[RoleAssignmentResponse])
async def list_role_assignments(
    user_id: Optional[UUID] = None,
    role_id: Optional[UUID] = None,
    scope_type: Optional[ScopeTypeSchema] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List role assignments with optional filters."""
    await _require_rbac(db, current_user)
    # TODO: Filter by user's permissions - only show assignments they can manage
    
    # Build query with joins
    stmt = (
        select(RoleAssignment, User.name.label("user_name"), Role.name.label("role_name"))
        .join(User, RoleAssignment.user_id == User.id)
        .join(Role, RoleAssignment.role_id == Role.id)
        .where(RoleAssignment.org_id == current_user.org_id)
    )
    
    # Apply filters
    if user_id:
        stmt = stmt.where(RoleAssignment.user_id == user_id)
    if role_id:
        stmt = stmt.where(RoleAssignment.role_id == role_id)
    if scope_type:
        stmt = stmt.where(RoleAssignment.scope_type == ScopeType(scope_type.value))
    
    stmt = stmt.order_by(RoleAssignment.created_at.desc())
    
    result = await db.execute(stmt)
    assignments_with_names = result.all()
    
    response = []
    for assignment, user_name, role_name in assignments_with_names:
        assignment_data = RoleAssignmentResponse.model_validate(assignment)
        assignment_data.user_name = user_name
        assignment_data.role_name = role_name
        
        # Get scope name
        if assignment.scope_type == ScopeType.PROJECT and assignment.scope_id:
            stmt = select(Project.name).where(Project.id == assignment.scope_id)
            result = await db.execute(stmt)
            scope_name = result.scalar_one_or_none()
            assignment_data.scope_name = scope_name
        elif assignment.scope_type == ScopeType.GROUP and assignment.scope_id:
            stmt = select(AgentGroup.name).where(AgentGroup.id == assignment.scope_id)
            result = await db.execute(stmt)
            scope_name = result.scalar_one_or_none()
            assignment_data.scope_name = scope_name
        
        response.append(assignment_data)
    
    return response


@router.delete("/role-assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a role assignment."""
    await _require_rbac(db, current_user)
    stmt = select(RoleAssignment).where(
        and_(
            RoleAssignment.id == assignment_id,
            RoleAssignment.org_id == current_user.org_id
        )
    )
    result = await db.execute(stmt)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found"
        )
    
    # TODO: Check permission - require appropriate role assignment permissions
    
    await db.delete(assignment)
    await db.commit()


# ─── User Permissions Query ───

@router.get("/users/{user_id}/roles", response_model=List[RoleAssignmentResponse])
async def get_user_roles(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all role assignments for a specific user."""
    await _require_rbac(db, current_user)
    # Verify user exists and is in same org (or is current user)
    if user_id != current_user.id:
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.org_id == current_user.org_id
            )
        )
        result = await db.execute(stmt)
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # TODO: Check permission - require appropriate access to view user roles
    
    # Get role assignments with role details
    stmt = (
        select(RoleAssignment, Role.name.label("role_name"))
        .join(Role, RoleAssignment.role_id == Role.id)
        .where(
            and_(
                RoleAssignment.user_id == user_id,
                RoleAssignment.org_id == current_user.org_id
            )
        )
        .order_by(RoleAssignment.created_at.desc())
    )
    
    result = await db.execute(stmt)
    assignments_with_roles = result.all()
    
    response = []
    for assignment, role_name in assignments_with_roles:
        assignment_data = RoleAssignmentResponse.model_validate(assignment)
        assignment_data.role_name = role_name
        
        # Get scope name
        if assignment.scope_type == ScopeType.PROJECT and assignment.scope_id:
            stmt = select(Project.name).where(Project.id == assignment.scope_id)
            result = await db.execute(stmt)
            scope_name = result.scalar_one_or_none()
            assignment_data.scope_name = scope_name
        elif assignment.scope_type == ScopeType.GROUP and assignment.scope_id:
            stmt = select(AgentGroup.name).where(AgentGroup.id == assignment.scope_id)
            result = await db.execute(stmt)
            scope_name = result.scalar_one_or_none()
            assignment_data.scope_name = scope_name
        
        response.append(assignment_data)
    
    return response


@router.get("/users/{user_id}/permissions", response_model=UserPermissionResponse)
async def get_user_permissions(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get effective permissions for a user based on their role assignments."""
    await _require_rbac(db, current_user)
    # Verify user exists and is in same org (or is current user)
    if user_id != current_user.id:
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.org_id == current_user.org_id
            )
        )
        result = await db.execute(stmt)
        target_user = result.scalar_one_or_none()
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # TODO: Check permission - require appropriate access to view user permissions
    
    # Get role assignments with role permissions
    stmt = (
        select(RoleAssignment, Role.permissions, Role.name.label("role_name"))
        .join(Role, RoleAssignment.role_id == Role.id)
        .where(
            and_(
                RoleAssignment.user_id == user_id,
                RoleAssignment.org_id == current_user.org_id
            )
        )
    )
    
    result = await db.execute(stmt)
    assignments_with_permissions = result.all()
    
    # Aggregate permissions from all roles
    all_permissions = []
    role_assignments = []
    
    for assignment, role_permissions, role_name in assignments_with_permissions:
        # Add scope context to permissions
        scoped_permissions = []
        for perm in role_permissions:
            scoped_perm = perm.copy()
            scoped_perm["scope"] = {
                "type": assignment.scope_type.value,
                "id": str(assignment.scope_id) if assignment.scope_id else None
            }
            scoped_permissions.append(scoped_perm)
        
        all_permissions.extend(scoped_permissions)
        
        # Create role assignment response
        assignment_data = RoleAssignmentResponse.model_validate(assignment)
        assignment_data.role_name = role_name
        role_assignments.append(assignment_data)
    
    return UserPermissionResponse(
        user_id=user_id,
        permissions=all_permissions,
        role_assignments=role_assignments
    )