"""
Agent Scheduler Service

Handles scheduled autonomous execution of agents with cron-like scheduling.
Integrates with existing agent engine for execution.
"""

import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

import pytz
from croniter import croniter
from sqlalchemy import select, func, and_, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.agent import Agent
from app.models.agent_schedule import AgentSchedule, ScheduledExecution
from app.models.organization import Organization
from app.services.agent_engine import AgentEngine
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)


class AgentSchedulerService:
    """Service for managing and executing agent schedules."""
    
    def __init__(self):
        self.agent_engine = AgentEngine()
    
    async def create_schedule(
        self,
        agent_id: uuid.UUID,
        name: str,
        cron_expression: str,
        task_prompt: str,
        db: AsyncSession,
        description: Optional[str] = None,
        output_config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        timezone_str: str = "UTC",
        max_retries: int = 3,
        retry_delay_minutes: int = 5,
        timeout_minutes: int = 10
    ) -> AgentSchedule:
        """Create a new agent schedule."""
        
        # Validate agent exists
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Validate cron expression
        try:
            # Test that the cron expression is valid
            cron = croniter(cron_expression, datetime.now())
            next_run = cron.get_next(datetime)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{cron_expression}': {e}")
        
        # Validate timezone
        try:
            tz = pytz.timezone(timezone_str)
        except Exception:
            raise ValueError(f"Invalid timezone '{timezone_str}'")
        
        # Calculate next run time
        now = datetime.now(tz)
        cron = croniter(cron_expression, now)
        next_run_at = cron.get_next(datetime)
        
        # Create schedule
        schedule = AgentSchedule(
            agent_id=agent_id,
            project_id=agent.project_id,
            org_id=agent.org_id,
            name=name,
            description=description,
            cron_expression=cron_expression,
            task_prompt=task_prompt,
            output_config=output_config or {},
            enabled=enabled,
            timezone=timezone_str,
            next_run_at=next_run_at if enabled else None,
            max_retries=max_retries,
            retry_delay_minutes=retry_delay_minutes,
            timeout_minutes=timeout_minutes
        )
        
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        
        logger.info(f"Created schedule {schedule.id} for agent {agent_id}: {name}")
        return schedule
    
    async def update_schedule(
        self,
        schedule_id: uuid.UUID,
        db: AsyncSession,
        **updates
    ) -> AgentSchedule:
        """Update an existing schedule."""
        
        stmt = select(AgentSchedule).where(AgentSchedule.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")
        
        # Track if we need to recalculate next run time
        recalc_next_run = False
        
        for field, value in updates.items():
            if field == "cron_expression" and value != schedule.cron_expression:
                # Validate new cron expression
                try:
                    cron = croniter(value, datetime.now())
                    cron.get_next(datetime)
                    recalc_next_run = True
                except Exception as e:
                    raise ValueError(f"Invalid cron expression '{value}': {e}")
            
            if field == "timezone" and value != schedule.timezone:
                # Validate timezone
                try:
                    pytz.timezone(value)
                    recalc_next_run = True
                except Exception:
                    raise ValueError(f"Invalid timezone '{value}'")
            
            if field == "enabled" and value != schedule.enabled:
                recalc_next_run = True
            
            if hasattr(schedule, field):
                setattr(schedule, field, value)
        
        # Recalculate next run time if needed
        if recalc_next_run:
            if schedule.enabled:
                try:
                    tz = pytz.timezone(schedule.timezone)
                    now = datetime.now(tz)
                    cron = croniter(schedule.cron_expression, now)
                    schedule.next_run_at = cron.get_next(datetime)
                except Exception as e:
                    logger.warning(f"Failed to calculate next run time: {e}")
                    schedule.next_run_at = None
            else:
                schedule.next_run_at = None
        
        await db.commit()
        await db.refresh(schedule)
        
        logger.info(f"Updated schedule {schedule_id}")
        return schedule
    
    async def get_due_schedules(
        self,
        db: AsyncSession,
        limit: int = 100
    ) -> List[AgentSchedule]:
        """Get schedules that are due for execution."""
        
        now = datetime.now(timezone.utc)
        
        stmt = (
            select(AgentSchedule)
            .where(
                and_(
                    AgentSchedule.enabled == True,
                    AgentSchedule.next_run_at <= now,
                    AgentSchedule.next_run_at.isnot(None)
                )
            )
            .order_by(AgentSchedule.next_run_at)
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def execute_schedule(
        self,
        schedule: AgentSchedule,
        db: AsyncSession,
        redis: Redis,
        force_execution: bool = False
    ) -> ScheduledExecution:
        """Execute a scheduled task."""
        
        # Create execution record
        execution = ScheduledExecution(
            schedule_id=schedule.id,
            agent_id=schedule.agent_id,
            org_id=schedule.org_id,
            status="pending",
            scheduled_at=schedule.next_run_at or datetime.now(timezone.utc)
        )
        
        db.add(execution)
        await db.commit()
        await db.refresh(execution)
        
        try:
            # Update execution status to running
            execution.status = "running"
            execution.started_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Get agent
            stmt = select(Agent).where(Agent.id == schedule.agent_id)
            result = await db.execute(stmt)
            agent = result.scalar_one_or_none()
            
            if not agent:
                raise ValueError(f"Agent {schedule.agent_id} not found")
            
            if agent.status != "active" and not force_execution:
                raise ValueError(f"Agent {agent.id} is not active")
            
            # Execute agent with the scheduled prompt
            logger.info(f"Executing scheduled task {execution.id} for agent {agent.id}")
            
            # Set a timeout for the execution
            timeout_seconds = schedule.timeout_minutes * 60
            
            async def execute_with_timeout():
                return await self.agent_engine.execute(
                    agent=agent,
                    message=schedule.task_prompt,
                    db=db,
                    redis=redis,
                    session_id=None,  # Create new session for each scheduled execution
                    user_id=None  # System execution
                )
            
            try:
                result = await asyncio.wait_for(execute_with_timeout(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                raise ValueError(f"Execution timed out after {timeout_seconds} seconds")
            
            # Update execution with results
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.result_content = result.content
            execution.tokens_used = result.tokens
            execution.cost = result.cost
            
            # Get the session ID from the result if available
            if hasattr(result, 'session_id'):
                execution.session_id = result.session_id
            
            # Deliver output if configured
            await self._deliver_output(schedule, execution, result, db)
            
            # Update schedule statistics
            schedule.run_count += 1
            schedule.last_run_at = execution.completed_at
            schedule.failure_count = 0  # Reset failure count on success
            
            # Calculate next run time
            await self._calculate_next_run_time(schedule)
            
            await db.commit()
            
            logger.info(f"Successfully executed scheduled task {execution.id}")
            
        except Exception as e:
            # Update execution with error
            execution.status = "failed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.error_message = str(e)
            
            # Update schedule statistics
            schedule.failure_count += 1
            
            # If we've exceeded max retries, disable the schedule
            if schedule.failure_count >= schedule.max_retries:
                logger.warning(f"Schedule {schedule.id} disabled after {schedule.failure_count} failures")
                schedule.enabled = False
                schedule.next_run_at = None
            else:
                # Schedule retry
                retry_delay = timedelta(minutes=schedule.retry_delay_minutes)
                schedule.next_run_at = datetime.now(timezone.utc) + retry_delay
            
            await db.commit()
            
            logger.error(f"Failed to execute scheduled task {execution.id}: {e}")
            
            # Re-raise for logging purposes but don't fail the scheduler
            raise
        
        return execution
    
    async def _deliver_output(
        self,
        schedule: AgentSchedule,
        execution: ScheduledExecution,
        result: Any,
        db: AsyncSession
    ):
        """Deliver the execution output according to the schedule configuration."""
        
        output_config = schedule.output_config or {}
        delivery_log = []
        
        try:
            # Webhook delivery
            if output_config.get("webhook"):
                webhook_url = output_config["webhook"].get("url")
                if webhook_url:
                    await self._deliver_webhook(webhook_url, execution, result, delivery_log)
            
            # Email delivery
            if output_config.get("email"):
                email_config = output_config["email"]
                recipients = email_config.get("recipients", [])
                if recipients:
                    await self._deliver_email(recipients, execution, result, delivery_log)
            
            # Slack delivery
            if output_config.get("slack"):
                slack_config = output_config["slack"]
                channel = slack_config.get("channel")
                if channel:
                    await self._deliver_slack(channel, execution, result, delivery_log)
            
            # Dashboard storage (always enabled)
            delivery_log.append({
                "type": "dashboard",
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message": "Result stored in dashboard"
            })
            
            execution.output_delivered = len([log for log in delivery_log if log["status"] == "success"]) > 0
            execution.output_log = delivery_log
            
        except Exception as e:
            delivery_log.append({
                "type": "error",
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            })
            execution.output_log = delivery_log
            logger.error(f"Failed to deliver output for execution {execution.id}: {e}")
    
    async def _deliver_webhook(
        self,
        webhook_url: str,
        execution: ScheduledExecution,
        result: Any,
        delivery_log: List[Dict]
    ):
        """Deliver result via webhook."""
        import httpx
        
        payload = {
            "execution_id": str(execution.id),
            "schedule_id": str(execution.schedule_id),
            "agent_id": str(execution.agent_id),
            "timestamp": execution.completed_at.isoformat(),
            "status": execution.status,
            "content": execution.result_content,
            "tokens_used": execution.tokens_used,
            "cost": float(execution.cost) if execution.cost else None,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
            
            delivery_log.append({
                "type": "webhook",
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": webhook_url,
                "response_status": response.status_code
            })
        
        except Exception as e:
            delivery_log.append({
                "type": "webhook",
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": webhook_url,
                "error": str(e)
            })
    
    async def _deliver_email(
        self,
        recipients: List[str],
        execution: ScheduledExecution,
        result: Any,
        delivery_log: List[Dict]
    ):
        """Deliver result via email."""
        try:
            from app.services.email_service import EmailService
            
            email_service = EmailService()
            
            subject = f"Scheduled Agent Execution - {execution.schedule_id}"
            body = f"""
            Scheduled execution completed successfully.
            
            Execution ID: {execution.id}
            Agent ID: {execution.agent_id}
            Completed: {execution.completed_at}
            Tokens Used: {execution.tokens_used}
            Cost: ${execution.cost}
            
            Result:
            {execution.result_content}
            """
            
            await email_service.send_email(
                to_emails=recipients,
                subject=subject,
                body=body
            )
            
            delivery_log.append({
                "type": "email",
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recipients": recipients
            })
        
        except Exception as e:
            delivery_log.append({
                "type": "email",
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "recipients": recipients,
                "error": str(e)
            })
    
    async def _deliver_slack(
        self,
        channel: str,
        execution: ScheduledExecution,
        result: Any,
        delivery_log: List[Dict]
    ):
        """Deliver result via Slack."""
        try:
            # TODO: Implement Slack delivery
            # This would integrate with the existing message service
            delivery_log.append({
                "type": "slack",
                "status": "success",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": channel
            })
        
        except Exception as e:
            delivery_log.append({
                "type": "slack",
                "status": "failed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "channel": channel,
                "error": str(e)
            })
    
    async def _calculate_next_run_time(self, schedule: AgentSchedule):
        """Calculate the next run time for a schedule."""
        
        if not schedule.enabled:
            schedule.next_run_at = None
            return
        
        try:
            tz = pytz.timezone(schedule.timezone)
            now = datetime.now(tz)
            cron = croniter(schedule.cron_expression, now)
            schedule.next_run_at = cron.get_next(datetime)
        except Exception as e:
            logger.error(f"Failed to calculate next run time for schedule {schedule.id}: {e}")
            schedule.next_run_at = None
    
    async def get_schedule_executions(
        self,
        schedule_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[ScheduledExecution]:
        """Get execution history for a schedule."""
        
        conditions = [ScheduledExecution.schedule_id == schedule_id]
        
        if status:
            conditions.append(ScheduledExecution.status == status)
        
        stmt = (
            select(ScheduledExecution)
            .where(and_(*conditions))
            .order_by(desc(ScheduledExecution.scheduled_at))
            .limit(limit)
            .offset(offset)
        )
        
        result = await db.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_schedule(
        self,
        schedule_id: uuid.UUID,
        db: AsyncSession
    ) -> bool:
        """Delete a schedule and its execution history."""
        
        stmt = select(AgentSchedule).where(AgentSchedule.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return False
        
        # Delete executions first (due to foreign key constraints)
        delete_executions_stmt = (
            ScheduledExecution.__table__.delete()
            .where(ScheduledExecution.schedule_id == schedule_id)
        )
        await db.execute(delete_executions_stmt)
        
        # Delete schedule
        await db.delete(schedule)
        await db.commit()
        
        logger.info(f"Deleted schedule {schedule_id}")
        return True
    
    async def run_scheduler_loop(self, db: AsyncSession, redis: Redis):
        """Main scheduler loop that processes due schedules."""
        
        logger.info("Starting scheduler loop")
        
        while True:
            try:
                # Get due schedules
                due_schedules = await self.get_due_schedules(db)
                
                if due_schedules:
                    logger.info(f"Found {len(due_schedules)} due schedules")
                    
                    # Execute schedules concurrently (with some limit)
                    max_concurrent = 10
                    semaphore = asyncio.Semaphore(max_concurrent)
                    
                    async def execute_with_semaphore(schedule):
                        async with semaphore:
                            try:
                                await self.execute_schedule(schedule, db, redis)
                            except Exception as e:
                                logger.error(f"Error executing schedule {schedule.id}: {e}")
                    
                    await asyncio.gather(
                        *[execute_with_semaphore(schedule) for schedule in due_schedules],
                        return_exceptions=True
                    )
                
                # Sleep for 30 seconds before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error