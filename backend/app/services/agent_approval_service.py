"""
Agent Approval Service

Handles human-in-the-loop approval workflow for agent actions.
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import select, func, and_, or_, desc, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_approval import AgentApprovalAction, AgentApprovalConfig
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.models.user import User
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)


class AgentApprovalService:
    """Service for managing agent approval workflows."""
    
    def __init__(self):
        pass
    
    async def create_approval_action(
        self,
        agent_id: uuid.UUID,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        action_type: str,
        action_description: str,
        action_payload: Dict[str, Any],
        db: AsyncSession,
        requested_by: Optional[uuid.UUID] = None,
        risk_level: str = "medium",
        custom_timeout_hours: Optional[int] = None
    ) -> AgentApprovalAction:
        """Create a new approval action request."""
        
        # Get agent and session info
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Get approval configuration for this action type
        config = await self.get_approval_config(agent_id, action_type, db)
        
        # Check if approval is required
        if config and not config.requires_approval:
            # Check auto-approve conditions
            if await self._check_auto_approve_conditions(config, action_payload):
                # Auto-approve and return immediately with approved status
                action = AgentApprovalAction(
                    agent_id=agent_id,
                    session_id=session_id,
                    message_id=message_id,
                    project_id=agent.project_id,
                    org_id=agent.org_id,
                    action_type=action_type,
                    action_description=action_description,
                    action_payload=action_payload,
                    risk_level=risk_level,
                    status="approved",
                    requested_by=requested_by,
                    reviewed_by=None,  # Auto-approved
                    review_notes="Auto-approved based on configuration",
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),  # Still set expiry
                    reviewed_at=datetime.now(timezone.utc)
                )
                db.add(action)
                await db.commit()
                await db.refresh(action)
                return action
        
        # Determine timeout based on config or custom value
        timeout_hours = custom_timeout_hours or (config.timeout_hours if config else 24)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=timeout_hours)
        
        # Assess risk level if rules are configured
        if config and config.risk_assessment_rules:
            risk_level = await self._assess_risk_level(config.risk_assessment_rules, action_payload, risk_level)
        
        # Create approval action
        action = AgentApprovalAction(
            agent_id=agent_id,
            session_id=session_id,
            message_id=message_id,
            project_id=agent.project_id,
            org_id=agent.org_id,
            action_type=action_type,
            action_description=action_description,
            action_payload=action_payload,
            risk_level=risk_level,
            status="pending",
            requested_by=requested_by,
            expires_at=expires_at
        )
        
        db.add(action)
        await db.commit()
        await db.refresh(action)
        
        # Log audit event
        await log_audit_event(
            "agent_approval_requested",
            agent.org_id,
            requested_by,
            {
                "agent_id": str(agent_id),
                "action_type": action_type,
                "action_description": action_description,
                "risk_level": risk_level,
                "approval_id": str(action.id)
            },
            db
        )
        
        logger.info(f"Created approval action {action.id} for agent {agent_id} (type: {action_type})")
        return action
    
    async def review_approval_action(
        self,
        action_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        decision: str,  # "approve" or "reject"
        review_notes: Optional[str],
        db: AsyncSession
    ) -> AgentApprovalAction:
        """Review and approve/reject an approval action."""
        
        if decision not in ["approve", "reject"]:
            raise ValueError("Decision must be 'approve' or 'reject'")
        
        # Get the action
        stmt = select(AgentApprovalAction).where(AgentApprovalAction.id == action_id)
        result = await db.execute(stmt)
        action = result.scalar_one_or_none()
        
        if not action:
            raise ValueError(f"Approval action {action_id} not found")
        
        if action.status != "pending":
            raise ValueError(f"Approval action {action_id} is not pending (status: {action.status})")
        
        # Check if expired
        if action.expires_at < datetime.now(timezone.utc):
            action.status = "expired"
            await db.commit()
            raise ValueError(f"Approval action {action_id} has expired")
        
        # Update action
        action.status = "approved" if decision == "approve" else "rejected"
        action.reviewed_by = reviewer_id
        action.review_notes = review_notes
        action.reviewed_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(action)
        
        # Log audit event
        await log_audit_event(
            f"agent_approval_{decision}d",
            action.org_id,
            reviewer_id,
            {
                "agent_id": str(action.agent_id),
                "action_type": action.action_type,
                "approval_id": str(action.id),
                "review_notes": review_notes
            },
            db
        )
        
        logger.info(f"Approval action {action_id} {decision}d by user {reviewer_id}")
        return action
    
    async def execute_approved_action(
        self,
        action_id: uuid.UUID,
        db: AsyncSession
    ) -> AgentApprovalAction:
        """Execute an approved action."""
        
        # Get the action
        stmt = select(AgentApprovalAction).where(AgentApprovalAction.id == action_id)
        result = await db.execute(stmt)
        action = result.scalar_one_or_none()
        
        if not action:
            raise ValueError(f"Approval action {action_id} not found")
        
        if action.status != "approved":
            raise ValueError(f"Approval action {action_id} is not approved (status: {action.status})")
        
        if action.executed_at:
            raise ValueError(f"Approval action {action_id} already executed")
        
        try:
            # Execute the action based on its type
            execution_result = await self._execute_action(action)
            
            # Update action with success
            action.status = "executed"
            action.executed_at = datetime.now(timezone.utc)
            action.execution_result = execution_result
            
            await db.commit()
            
            # Log audit event
            await log_audit_event(
                "agent_approval_executed",
                action.org_id,
                action.reviewed_by,
                {
                    "agent_id": str(action.agent_id),
                    "action_type": action.action_type,
                    "approval_id": str(action.id),
                    "execution_result": execution_result
                },
                db
            )
            
            logger.info(f"Successfully executed approval action {action_id}")
            
        except Exception as e:
            # Update action with error
            action.execution_error = str(e)
            await db.commit()
            
            logger.error(f"Failed to execute approval action {action_id}: {e}")
            raise
        
        return action
    
    async def _execute_action(self, action: AgentApprovalAction) -> Dict[str, Any]:
        """Execute the actual action based on its type."""
        
        action_type = action.action_type
        payload = action.action_payload
        
        if action_type == "send_email":
            return await self._execute_send_email(payload)
        elif action_type == "external_api":
            return await self._execute_external_api(payload)
        elif action_type == "modify_data":
            return await self._execute_modify_data(payload)
        elif action_type == "file_operation":
            return await self._execute_file_operation(payload)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    async def _execute_send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a send email action."""
        try:
            from app.services.email_service import EmailService
            
            email_service = EmailService()
            
            to_emails = payload.get("to", [])
            subject = payload.get("subject", "")
            body = payload.get("body", "")
            
            if not to_emails:
                raise ValueError("No recipients specified")
            
            await email_service.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body
            )
            
            return {
                "status": "success",
                "recipients": to_emails,
                "subject": subject,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            raise ValueError(f"Failed to send email: {e}")
    
    async def _execute_external_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an external API call."""
        import httpx
        
        try:
            url = payload.get("url")
            method = payload.get("method", "GET").upper()
            headers = payload.get("headers", {})
            data = payload.get("data")
            timeout = payload.get("timeout", 30)
            
            if not url:
                raise ValueError("No URL specified")
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if method in ["POST", "PUT", "PATCH"] else None,
                    params=data if method == "GET" else None
                )
                
                return {
                    "status": "success",
                    "url": url,
                    "method": method,
                    "response_status": response.status_code,
                    "response_headers": dict(response.headers),
                    "response_body": response.text[:1000],  # Limit response body size
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
        except Exception as e:
            raise ValueError(f"External API call failed: {e}")
    
    async def _execute_modify_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a data modification action."""
        # This would integrate with specific data sources based on payload
        # For now, just return a placeholder
        return {
            "status": "success",
            "operation": payload.get("operation", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Data modification executed (placeholder implementation)"
        }
    
    async def _execute_file_operation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a file operation."""
        # This would integrate with secure file storage
        # For now, just return a placeholder
        return {
            "status": "success",
            "operation": payload.get("operation", "unknown"),
            "file": payload.get("file", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "File operation executed (placeholder implementation)"
        }
    
    async def get_approval_config(
        self,
        agent_id: uuid.UUID,
        action_type: str,
        db: AsyncSession
    ) -> Optional[AgentApprovalConfig]:
        """Get approval configuration for an agent and action type."""
        
        stmt = select(AgentApprovalConfig).where(
            and_(
                AgentApprovalConfig.agent_id == agent_id,
                AgentApprovalConfig.action_type == action_type
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_approval_config(
        self,
        agent_id: uuid.UUID,
        action_type: str,
        db: AsyncSession,
        requires_approval: bool = True,
        auto_approve_conditions: Optional[Dict[str, Any]] = None,
        timeout_hours: int = 24,
        required_approvers: int = 1,
        risk_assessment_rules: Optional[Dict[str, Any]] = None
    ) -> AgentApprovalConfig:
        """Create or update approval configuration."""
        
        # Get agent to validate and get org_id
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Check if config already exists
        existing_config = await self.get_approval_config(agent_id, action_type, db)
        
        if existing_config:
            # Update existing config
            existing_config.requires_approval = requires_approval
            existing_config.auto_approve_conditions = auto_approve_conditions
            existing_config.timeout_hours = timeout_hours
            existing_config.required_approvers = required_approvers
            existing_config.risk_assessment_rules = risk_assessment_rules
            
            await db.commit()
            await db.refresh(existing_config)
            return existing_config
        
        # Create new config
        config = AgentApprovalConfig(
            agent_id=agent_id,
            org_id=agent.org_id,
            action_type=action_type,
            requires_approval=requires_approval,
            auto_approve_conditions=auto_approve_conditions,
            timeout_hours=timeout_hours,
            required_approvers=required_approvers,
            risk_assessment_rules=risk_assessment_rules
        )
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"Created approval config for agent {agent_id}, action type {action_type}")
        return config
    
    async def get_pending_approvals(
        self,
        org_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        agent_id: Optional[uuid.UUID] = None,
        action_type: Optional[str] = None,
        risk_level: Optional[str] = None
    ) -> List[AgentApprovalAction]:
        """Get pending approval actions with filtering."""
        
        conditions = [
            AgentApprovalAction.org_id == org_id,
            AgentApprovalAction.status == "pending",
            AgentApprovalAction.expires_at > datetime.now(timezone.utc)
        ]
        
        if agent_id:
            conditions.append(AgentApprovalAction.agent_id == agent_id)
        
        if action_type:
            conditions.append(AgentApprovalAction.action_type == action_type)
        
        if risk_level:
            conditions.append(AgentApprovalAction.risk_level == risk_level)
        
        stmt = (
            select(AgentApprovalAction)
            .where(and_(*conditions))
            .order_by(
                AgentApprovalAction.risk_level.desc(),  # High risk first
                AgentApprovalAction.created_at.asc()    # Oldest first
            )
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_approval_queue_summary(
        self,
        org_id: uuid.UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get summary statistics for the approval queue."""
        
        now = datetime.now(timezone.utc)
        expiring_soon = now + timedelta(hours=2)
        
        # Get counts by status and risk level
        summary_stmt = select(
            func.count().filter(AgentApprovalAction.status == "pending").label("total_pending"),
            func.count().filter(
                and_(
                    AgentApprovalAction.status == "pending",
                    AgentApprovalAction.risk_level == "high"
                )
            ).label("high_risk_pending"),
            func.count().filter(
                and_(
                    AgentApprovalAction.status == "pending",
                    AgentApprovalAction.risk_level == "critical"
                )
            ).label("critical_risk_pending"),
            func.count().filter(
                and_(
                    AgentApprovalAction.status == "pending",
                    AgentApprovalAction.expires_at <= expiring_soon
                )
            ).label("expiring_soon")
        ).where(AgentApprovalAction.org_id == org_id)
        
        summary_result = await db.execute(summary_stmt)
        summary = summary_result.first()
        
        # Get counts by action type
        action_type_stmt = (
            select(
                AgentApprovalAction.action_type,
                func.count(AgentApprovalAction.id).label("count")
            )
            .where(
                and_(
                    AgentApprovalAction.org_id == org_id,
                    AgentApprovalAction.status == "pending"
                )
            )
            .group_by(AgentApprovalAction.action_type)
        )
        
        action_type_result = await db.execute(action_type_stmt)
        by_action_type = {row.action_type: row.count for row in action_type_result}
        
        # Get counts by agent
        agent_stmt = (
            select(
                Agent.id,
                Agent.name,
                func.count(AgentApprovalAction.id).label("count")
            )
            .join(Agent, AgentApprovalAction.agent_id == Agent.id)
            .where(
                and_(
                    AgentApprovalAction.org_id == org_id,
                    AgentApprovalAction.status == "pending"
                )
            )
            .group_by(Agent.id, Agent.name)
        )
        
        agent_result = await db.execute(agent_stmt)
        by_agent = {
            str(row.id): {"name": row.name, "count": row.count}
            for row in agent_result
        }
        
        return {
            "total_pending": summary.total_pending or 0,
            "high_risk_pending": summary.high_risk_pending or 0,
            "critical_risk_pending": summary.critical_risk_pending or 0,
            "expiring_soon": summary.expiring_soon or 0,
            "by_action_type": by_action_type,
            "by_agent": by_agent
        }
    
    async def expire_old_approvals(self, db: AsyncSession) -> int:
        """Expire old approval actions that have passed their timeout."""
        
        now = datetime.now(timezone.utc)
        
        # Update expired actions
        stmt = (
            update(AgentApprovalAction)
            .where(
                and_(
                    AgentApprovalAction.status == "pending",
                    AgentApprovalAction.expires_at <= now
                )
            )
            .values(status="expired", updated_at=now)
        )
        
        result = await db.execute(stmt)
        expired_count = result.rowcount
        await db.commit()
        
        if expired_count > 0:
            logger.info(f"Expired {expired_count} approval actions")
        
        return expired_count
    
    async def _check_auto_approve_conditions(
        self,
        config: AgentApprovalConfig,
        action_payload: Dict[str, Any]
    ) -> bool:
        """Check if an action meets auto-approval conditions."""
        
        if not config.auto_approve_conditions:
            return False
        
        conditions = config.auto_approve_conditions
        
        # Simple condition checking (can be extended)
        for key, expected_value in conditions.items():
            if key not in action_payload:
                return False
            
            actual_value = action_payload[key]
            
            # Handle different types of conditions
            if isinstance(expected_value, dict):
                if "max" in expected_value and actual_value > expected_value["max"]:
                    return False
                if "min" in expected_value and actual_value < expected_value["min"]:
                    return False
            elif actual_value != expected_value:
                return False
        
        return True
    
    async def _assess_risk_level(
        self,
        rules: Dict[str, Any],
        action_payload: Dict[str, Any],
        default_risk: str = "medium"
    ) -> str:
        """Assess risk level based on configured rules."""
        
        # Simple rule-based risk assessment (can be extended)
        risk_score = 0
        
        for rule_name, rule_config in rules.items():
            if rule_name in action_payload:
                value = action_payload[rule_name]
                
                if isinstance(rule_config, dict):
                    if "critical_threshold" in rule_config and value >= rule_config["critical_threshold"]:
                        return "critical"
                    elif "high_threshold" in rule_config and value >= rule_config["high_threshold"]:
                        risk_score += 3
                    elif "medium_threshold" in rule_config and value >= rule_config["medium_threshold"]:
                        risk_score += 2
        
        if risk_score >= 5:
            return "critical"
        elif risk_score >= 3:
            return "high"
        elif risk_score >= 1:
            return "medium"
        else:
            return "low"