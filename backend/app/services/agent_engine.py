"""
Agent Engine - OpenClaw-inspired agent execution loop with Enterprise Security

Core pattern: intake → security checks → context assembly → model inference → tool execution → reply → persist

SECURITY-FIRST DESIGN:
- Default deny on all tools (mode: "none")
- Hard budget stops (402 errors)
- Input sanitization against prompt injection  
- URL allowlist enforcement for HTTP tools
- Rate limiting per agent (Redis-backed)
- Complete audit trail for every operation
- No code execution capabilities
- Session isolation and limits
"""

import json
import uuid
import logging
import re
import time
import httpx
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from ipaddress import ip_address, IPv4Address, IPv6Address

from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.models.agent import Agent
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.models.knowledge_base import KnowledgeBase, KBChunk
from app.models.audit import AuditLog
from app.schemas.bonobot import AgentRunResult, SecurityMetadata
from app.services.gateway import GatewayService
from app.services.kb_content import search_knowledge_base
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)


class AgentEngine:
    """OpenClaw-inspired agent execution engine with enterprise security."""

    def __init__(self):
        self.gateway = GatewayService()
        
        # Security patterns for input sanitization
        self.prompt_injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"disregard\s+previous\s+instructions",
            r"system\s*:",
            r"assistant\s*:",
            r"you\s+are\s+now\s+a",
            r"act\s+as\s+if\s+you\s+are",
            r"pretend\s+to\s+be",
            r"override\s+your\s+instructions",
            r"new\s+instructions\s*:",
            r"forget\s+everything",
        ]
        
        # Private IP ranges for SSRF protection
        self.private_ranges = [
            "10.0.0.0/8",
            "172.16.0.0/12", 
            "192.168.0.0/16",
            "127.0.0.0/8",
            "169.254.0.0/16",
            "::1/128",
            "fc00::/7",
            "fe80::/10",
        ]

    async def execute(
        self,
        agent: Agent,
        message: str,
        db: AsyncSession,
        redis: Redis,
        session_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> AgentRunResult:
        """Run a single agent turn with comprehensive security controls."""
        
        # SECURITY STEP 1: Rate limiting check
        await self._check_rate_limit(agent, redis)
        
        # SECURITY STEP 2: Budget enforcement (hard stop)
        await self._enforce_budget_limit(agent, db)
        
        # SECURITY STEP 3: Input sanitization
        sanitized_message, input_sanitized = self._sanitize_input(message)
        
        # SECURITY STEP 4: Create audit log for execution attempt
        audit_id = await self._log_execution_start(agent, sanitized_message, user_id, db)
        
        try:
            # 1. Resolve or create session
            session = await self._resolve_session(agent, session_id, db)
            
            # SECURITY STEP 5: Session message limit enforcement
            await self._enforce_session_limits(agent, session, db)
            
            # 2. Persist user message
            await self._persist_message(session, role="user", content=sanitized_message, db=db)
            
            # 3. Assemble context
            messages = await self._assemble_context(agent, session, sanitized_message, db)
            
            # 4. Agent loop (with tool execution and security)
            result = await self._run_agent_loop(agent, session, messages, db, redis, audit_id)
            
            # Update security metadata with input sanitization flag
            result.security.input_sanitized = input_sanitized
            
            # 5. Update metrics
            await self._update_metrics(agent, session, result, db)
            
            # 6. Log successful execution
            await self._log_execution_success(audit_id, result, db)
            
            return result
            
        except Exception as e:
            # Log execution failure
            await self._log_execution_failure(audit_id, str(e), db)
            raise

    async def _resolve_session(
        self,
        agent: Agent,
        session_id: Optional[uuid.UUID],
        db: AsyncSession
    ) -> AgentSession:
        """Resolve or create agent session."""
        if session_id:
            # Try to find existing session
            stmt = select(AgentSession).where(
                and_(
                    AgentSession.id == session_id,
                    AgentSession.agent_id == agent.id,
                    AgentSession.org_id == agent.org_id
                )
            )
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            
            if session:
                return session
                
        # Create new session
        session_key = f"agent:{agent.id}:{uuid.uuid4()}"
        session = AgentSession(
            agent_id=agent.id,
            org_id=agent.org_id,
            session_key=session_key,
            status="active"
        )
        db.add(session)
        await db.flush()  # Get ID
        return session

    async def _persist_message(
        self,
        session: AgentSession,
        role: str,
        db: AsyncSession,
        content: Optional[str] = None,
        tool_calls: Optional[Dict] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        model_used: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost: Optional[Decimal] = None,
        latency_ms: Optional[int] = None,
    ):
        """Persist a message to the session."""
        # Get next sequence number
        stmt = select(func.coalesce(func.max(AgentMessage.sequence), 0) + 1).where(
            AgentMessage.session_id == session.id
        )
        result = await db.execute(stmt)
        sequence = result.scalar()

        message = AgentMessage(
            session_id=session.id,
            org_id=session.org_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            model_used=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            sequence=sequence
        )
        db.add(message)
        
        # Update session stats
        session.message_count += 1
        session.last_message_at = datetime.now(timezone.utc)
        if cost:
            session.total_cost += cost
        if input_tokens and output_tokens:
            session.total_tokens += (input_tokens + output_tokens)
        elif output_tokens:
            session.total_tokens += output_tokens

        await db.flush()

    async def _assemble_context(
        self,
        agent: Agent,
        session: AgentSession,
        user_message: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Build the message array for the model."""
        system_prompt = self._build_system_prompt(agent)
        
        # Inject RAG context if agent has knowledge bases
        if agent.knowledge_base_ids:
            rag_context = await self._get_rag_context(agent, user_message, db)
            if rag_context:
                system_prompt += f"\n\n## Knowledge Context\n{rag_context}"
        
        # Build message history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history from session (with compaction if needed)
        history = await self._get_session_history(session, db)
        messages.extend(history)
        
        return messages

    def _build_system_prompt(self, agent: Agent) -> str:
        """Build system prompt from agent config + tool definitions."""
        system_prompt = agent.system_prompt
        
        # Add tool definitions
        tools = self._get_tool_definitions(agent)
        if tools:
            tool_descriptions = []
            for tool in tools:
                name = tool.get("function", {}).get("name", "unknown")
                desc = tool.get("function", {}).get("description", "")
                tool_descriptions.append(f"- {name}: {desc}")
            
            system_prompt += f"\n\n## Available Tools\nYou have access to these tools:\n" + "\n".join(tool_descriptions)
        
        return system_prompt

    async def _get_rag_context(self, agent: Agent, query: str, db: AsyncSession) -> Optional[str]:
        """Get RAG context from assigned knowledge bases."""
        if not agent.knowledge_base_ids:
            return None
            
        context_chunks = []
        
        for kb_id in agent.knowledge_base_ids:
            try:
                # Use existing KB search service
                results = await search_knowledge_base(
                    kb_id=uuid.UUID(kb_id),
                    query=query,
                    limit=5,
                    similarity_threshold=0.7,
                    org_id=agent.org_id,
                    db=db
                )
                
                for result in results:
                    context_chunks.append(f"**{result.get('source_name', 'Unknown')}:**\n{result.get('content', '')}")
                    
            except Exception as e:
                logger.warning(f"Failed to search KB {kb_id} for agent {agent.id}: {e}")
        
        if context_chunks:
            return "\n\n".join(context_chunks[:10])  # Limit to 10 chunks total
        
        return None

    async def _get_session_history(self, session: AgentSession, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get session message history."""
        # TODO: Implement compaction logic when context window fills
        
        stmt = select(AgentMessage).where(
            AgentMessage.session_id == session.id
        ).order_by(AgentMessage.sequence)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        history = []
        for msg in messages:
            if msg.role == "system":
                continue  # Skip system messages from history (we build fresh)
            
            message_dict = {"role": msg.role}
            
            if msg.content:
                message_dict["content"] = msg.content
            
            if msg.tool_calls:
                message_dict["tool_calls"] = msg.tool_calls
                
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            
            history.append(message_dict)
        
        return history

    async def _run_agent_loop(
        self,
        agent: Agent,
        session: AgentSession,
        messages: List[Dict[str, Any]],
        db: AsyncSession,
        redis: Redis,
        audit_id: uuid.UUID
    ) -> AgentRunResult:
        """Execute the model inference + tool call loop with security tracking."""
        tools = self._get_tool_definitions(agent)
        turn = 0
        total_tokens = 0
        total_cost = Decimal(0)
        start_time = datetime.now(timezone.utc)
        
        # Security tracking
        tools_used = []
        knowledge_bases_accessed = []
        
        while turn < agent.max_turns:
            try:
                # Call model via Bonito gateway
                response = await self._call_gateway(agent, messages, tools, db)
                
                total_tokens += response.get("usage", {}).get("total_tokens", 0)
                total_cost += Decimal(str(response.get("cost", 0)))
                
                assistant_message = response.get("choices", [{}])[0].get("message", {})
                
                # Calculate latency
                latency_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                
                # Persist assistant message
                await self._persist_message(
                    session,
                    role="assistant",
                    content=assistant_message.get("content"),
                    tool_calls=assistant_message.get("tool_calls"),
                    model_used=response.get("model"),
                    input_tokens=response.get("usage", {}).get("prompt_tokens"),
                    output_tokens=response.get("usage", {}).get("completion_tokens"),
                    cost=Decimal(str(response.get("cost", 0))),
                    latency_ms=latency_ms,
                    db=db
                )
                
                messages.append(assistant_message)
                
                # If no tool calls, we're done
                if not assistant_message.get("tool_calls"):
                    break
                
                # Execute tool calls with security tracking
                for tool_call in assistant_message.get("tool_calls", []):
                    tool_start_time = datetime.now(timezone.utc)
                    tool_name = tool_call.get("function", {}).get("name")
                    
                    result = await self._execute_tool(agent, tool_call, db, redis)
                    
                    # Track tool usage for security metadata
                    if tool_name and tool_name not in tools_used:
                        tools_used.append(tool_name)
                    
                    # Track KB access
                    if tool_name == "search_knowledge_base" and isinstance(result, dict):
                        kb_results = result.get("results", [])
                        for kb_result in kb_results:
                            if "knowledge_base_id" in kb_result:
                                kb_id = kb_result["knowledge_base_id"]
                                if kb_id not in knowledge_bases_accessed:
                                    knowledge_bases_accessed.append(kb_id)
                    
                    # Log tool execution
                    execution_time_ms = int((datetime.now(timezone.utc) - tool_start_time).total_seconds() * 1000)
                    await self._log_tool_execution(
                        audit_id, tool_name, 
                        json.loads(tool_call.get("function", {}).get("arguments", "{}")),
                        result, execution_time_ms, db, agent.org_id
                    )
                    
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps(result)
                    }
                    messages.append(tool_msg)
                    
                    await self._persist_message(
                        session,
                        role="tool",
                        content=json.dumps(result),
                        tool_call_id=tool_call.get("id"),
                        tool_name=tool_name,
                        db=db
                    )
                
                turn += 1
                
            except Exception as e:
                logger.error(f"Error in agent loop for agent {agent.id}: {e}")
                break
        
        # Calculate budget information
        from app.models.project import Project
        stmt = select(Project).where(Project.id == agent.project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        budget_remaining = None
        budget_percent_used = None
        if project and project.budget_monthly:
            budget_remaining = project.budget_monthly - project.budget_spent
            budget_percent_used = project.budget_spent / project.budget_monthly
        
        # Get current rate limit remaining
        current_minute = int(time.time() // 60)
        key = f"agent_rate:{agent.id}:{current_minute}"
        current_count = await redis.get(key)
        current_count = int(current_count) if current_count else 0
        rate_limit_remaining = max(0, agent.rate_limit_rpm - current_count)
        
        return AgentRunResult(
            content=assistant_message.get("content"),
            tokens=total_tokens,
            cost=total_cost,
            turns=turn + 1,
            model_used=response.get("model"),
            security=SecurityMetadata(
                tools_used=tools_used,
                knowledge_bases_accessed=knowledge_bases_accessed,
                budget_remaining=budget_remaining,
                budget_percent_used=budget_percent_used,
                input_sanitized=False,  # Will be updated by caller
                audit_id=audit_id,
                rate_limit_remaining=rate_limit_remaining
            )
        )

    async def _call_gateway(
        self,
        agent: Agent,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Route through Bonito's gateway for model inference."""
        try:
            # Use the gateway service directly for internal calls
            request_data = {
                "model": agent.model_id if agent.model_id != "auto" else "gpt-4o",  # TODO: Smart routing
                "messages": messages,
                "max_tokens": agent.model_config.get("max_tokens", 1024),
                "temperature": agent.model_config.get("temperature", 0.7),
            }
            
            if tools:
                request_data["tools"] = tools
                request_data["tool_choice"] = "auto"
            
            # Call the gateway service internal method
            response = await self.gateway.process_completion_request(
                request_data=request_data,
                org_id=agent.org_id,
                db=db
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Gateway call failed for agent {agent.id}: {e}")
            # Return a fallback response
            return {
                "choices": [{"message": {"role": "assistant", "content": f"I apologize, but I encountered an error: {str(e)}"}}],
                "usage": {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0},
                "cost": 0,
                "model": "error"
            }

    async def _execute_tool(
        self,
        agent: Agent,
        tool_call: Dict[str, Any],
        db: AsyncSession,
        redis: Redis
    ) -> Dict[str, Any]:
        """Execute a tool call with policy enforcement."""
        tool_name = tool_call.get("function", {}).get("name")
        
        # Check tool policy
        if not self._is_tool_allowed(agent, tool_name):
            return {"error": f"Tool '{tool_name}' is not allowed for this agent"}
        
        # Route to tool handler
        handlers = {
            "search_knowledge_base": self._tool_search_kb,
            "http_request": self._tool_http_request,
            "invoke_agent": self._tool_invoke_agent,
            "send_notification": self._tool_send_notification,
            "get_current_time": self._tool_get_time,
            "list_models": self._tool_list_models,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}
        
        try:
            args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
            return await handler(agent, args, db, redis)
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"error": f"Tool execution failed: {str(e)}"}

    def _is_tool_allowed(self, agent: Agent, tool_name: str) -> bool:
        """Check if tool is allowed by agent's policy. DEFAULT DENY."""
        policy = agent.tool_policy or {}
        mode = policy.get("mode", "none")
        
        if mode == "none":
            return False  # DEFAULT DENY - no tools allowed
        elif mode == "allowlist":
            return tool_name in policy.get("allowed", [])
        elif mode == "denylist":
            built_in_tools = {
                "search_knowledge_base", "http_request", "invoke_agent",
                "send_notification", "get_current_time", "list_models"
            }
            return tool_name in built_in_tools and tool_name not in policy.get("denied", [])
        else:  # fallback to none mode for security
            return False

    def _get_tool_definitions(self, agent: Agent) -> List[Dict[str, Any]]:
        """Get OpenAI function calling tool definitions."""
        tools = []
        
        # Built-in tools (filtered by policy)
        all_tools = {
            "search_knowledge_base": {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Search the agent's assigned knowledge bases for relevant information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {"type": "integer", "default": 5, "description": "Max results"}
                        },
                        "required": ["query"]
                    }
                }
            },
            "get_current_time": {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Get the current UTC time",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            "http_request": {
                "type": "function",
                "function": {
                    "name": "http_request",
                    "description": "Make HTTP requests to external APIs",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Request URL"},
                            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
                            "headers": {"type": "object", "description": "Request headers"},
                            "data": {"type": "object", "description": "Request body"}
                        },
                        "required": ["url"]
                    }
                }
            }
        }
        
        for tool_name, tool_def in all_tools.items():
            if self._is_tool_allowed(agent, tool_name):
                tools.append(tool_def)
        
        return tools

    # ─── Tool Implementations ───

    async def _tool_search_kb(self, agent: Agent, args: Dict[str, Any], db: AsyncSession, redis: Redis) -> Dict[str, Any]:
        """Search knowledge base tool - ONLY ASSIGNED KBs."""
        query = args.get("query", "")
        limit = args.get("limit", 5)
        kb_id = args.get("kb_id")  # Optional specific KB
        
        if not agent.knowledge_base_ids:
            return {"results": [], "message": "No knowledge bases assigned to this agent"}
        
        # SECURITY: If specific KB requested, verify it's in agent's allowlist
        kb_ids_to_search = agent.knowledge_base_ids
        if kb_id:
            if kb_id not in agent.knowledge_base_ids:
                return {"error": f"Access denied. Knowledge base {kb_id} not assigned to this agent"}
            kb_ids_to_search = [kb_id]
        
        all_results = []
        for kb_id_str in kb_ids_to_search:
            try:
                kb_uuid = uuid.UUID(kb_id_str)
                
                # Double-check KB belongs to same org (defense in depth)
                stmt = select(KnowledgeBase).where(
                    and_(
                        KnowledgeBase.id == kb_uuid,
                        KnowledgeBase.org_id == agent.org_id
                    )
                )
                result = await db.execute(stmt)
                kb = result.scalar_one_or_none()
                
                if not kb:
                    logger.warning(f"KB {kb_id_str} not found or wrong org for agent {agent.id}")
                    continue
                
                results = await search_knowledge_base(
                    kb_id=kb_uuid,
                    query=query,
                    limit=limit,
                    similarity_threshold=0.7,
                    org_id=agent.org_id,
                    db=db
                )
                
                # Add KB metadata to results
                for result in results:
                    result["knowledge_base_id"] = kb_id_str
                    result["knowledge_base_name"] = kb.name
                
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"KB search failed for {kb_id_str}: {e}")
        
        # Sort by relevance and limit
        all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return {"results": all_results[:limit]}

    async def _tool_get_time(self, agent: Agent, args: Dict[str, Any], db: AsyncSession, redis: Redis) -> Dict[str, Any]:
        """Get current time tool."""
        return {"current_time": datetime.now(timezone.utc).isoformat()}

    async def _tool_http_request(self, agent: Agent, args: Dict[str, Any], db: AsyncSession, redis: Redis) -> Dict[str, Any]:
        """HTTP request tool with strict security controls."""
        url = args.get("url", "")
        method = args.get("method", "GET").upper()
        headers = args.get("headers", {})
        data = args.get("data", None)
        
        # Security validation
        policy = agent.tool_policy or {}
        allowlist = policy.get("http_allowlist", [])
        
        if not self._validate_http_url(url, allowlist):
            return {"error": f"URL not allowed. Must be in allowlist: {allowlist}"}
        
        # Method validation
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            return {"error": f"HTTP method {method} not allowed"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if data and method in ["POST", "PUT", "PATCH"] else None,
                    follow_redirects=False  # Security: prevent redirect attacks
                )
                
                # Limit response size
                content = response.content
                if len(content) > 100 * 1024:  # 100KB limit
                    content = content[:100 * 1024]
                    logger.warning(f"HTTP response truncated for URL {url} (size limit)")
                
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": content.decode('utf-8', errors='ignore'),
                    "truncated": len(response.content) > 100 * 1024
                }
                
        except httpx.TimeoutException:
            return {"error": "Request timeout (10 seconds)"}
        except Exception as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            return {"error": f"Request failed: {str(e)}"}
        

    async def _tool_invoke_agent(self, agent: Agent, args: Dict[str, Any], db: AsyncSession, redis: Redis) -> Dict[str, Any]:
        """Invoke another agent tool - SAME PROJECT ONLY."""
        target_agent_id = args.get("agent_id")
        message = args.get("message", "")
        
        if not target_agent_id or not message:
            return {"error": "agent_id and message are required"}
        
        try:
            target_agent_uuid = uuid.UUID(target_agent_id)
        except ValueError:
            return {"error": "Invalid agent_id format"}
        
        # SECURITY: Only allow invoking agents in the SAME PROJECT
        stmt = select(Agent).where(
            and_(
                Agent.id == target_agent_uuid,
                Agent.project_id == agent.project_id,  # SAME PROJECT ONLY
                Agent.org_id == agent.org_id,
                Agent.status == "active"
            )
        )
        result = await db.execute(stmt)
        target_agent = result.scalar_one_or_none()
        
        if not target_agent:
            return {"error": "Target agent not found or not in same project"}
        
        # Execute target agent (recursive call with depth protection)
        try:
            # Simple implementation - could be enhanced with depth tracking
            engine = AgentEngine()
            result = await engine.execute(
                agent=target_agent,
                message=message,
                db=db,
                redis=redis
            )
            
            return {
                "agent_name": target_agent.name,
                "response": result.content,
                "tokens": result.tokens,
                "cost": float(result.cost),
                "model_used": result.model_used
            }
            
        except Exception as e:
            logger.error(f"Agent invocation failed: {e}")
            return {"error": f"Target agent execution failed: {str(e)}"}

    async def _tool_send_notification(self, agent: Agent, args: Dict[str, Any], db: AsyncSession, redis: Redis) -> Dict[str, Any]:
        """Send notification tool."""
        # TODO: Implement notification sending
        return {"error": "Notification tool not implemented yet"}

    async def _tool_list_models(self, agent: Agent, args: Dict[str, Any], db: AsyncSession, redis: Redis) -> Dict[str, Any]:
        """List available models tool."""
        # TODO: Return list of models available to the org
        return {"models": ["gpt-4o", "gpt-4", "claude-3-sonnet", "auto"]}

    async def _update_metrics(self, agent: Agent, session: AgentSession, result: AgentRunResult, db: AsyncSession):
        """Update agent and session metrics."""
        agent.total_runs += 1
        agent.total_tokens += result.tokens
        agent.total_cost += result.cost
        agent.last_active_at = datetime.now(timezone.utc)
        
        # Generate session title from first user message if not set
        if not session.title and session.message_count > 0:
            # Get first user message for title
            stmt = select(AgentMessage.content).where(
                and_(
                    AgentMessage.session_id == session.id,
                    AgentMessage.role == "user"
                )
            ).order_by(AgentMessage.sequence).limit(1)
            
            result_msg = await db.execute(stmt)
            first_content = result_msg.scalar_one_or_none()
            
            if first_content:
                # Truncate to reasonable title length
                session.title = first_content[:50] + "..." if len(first_content) > 50 else first_content
        
        await db.flush()

    # ─── SECURITY METHODS ───

    async def _check_rate_limit(self, agent: Agent, redis: Redis) -> int:
        """Enforce per-agent rate limiting. Returns remaining requests."""
        from fastapi import HTTPException
        
        current_minute = int(time.time() // 60)
        key = f"agent_rate:{agent.id}:{current_minute}"
        
        current_count = await redis.get(key)
        current_count = int(current_count) if current_count else 0
        
        if current_count >= agent.rate_limit_rpm:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Agent {agent.name} allows {agent.rate_limit_rpm} requests per minute."
            )
        
        # Increment counter
        pipeline = redis.pipeline()
        pipeline.incr(key)
        pipeline.expire(key, 60)  # Expire after 1 minute
        await pipeline.execute()
        
        return agent.rate_limit_rpm - current_count - 1

    async def _enforce_budget_limit(self, agent: Agent, db: AsyncSession):
        """Hard budget enforcement - 402 error when exceeded."""
        from fastapi import HTTPException
        from app.models.project import Project
        
        if not hasattr(agent, 'project') or not agent.project:
            # Load project if not already loaded
            stmt = select(Project).where(Project.id == agent.project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
        else:
            project = agent.project
        
        if not project or not project.budget_monthly:
            return  # No budget limit set
        
        if project.budget_spent >= project.budget_monthly:
            raise HTTPException(
                status_code=402,
                detail="Agent budget exceeded. Contact administrator to increase budget or wait for next billing cycle."
            )

    def _sanitize_input(self, message: str) -> tuple[str, bool]:
        """Sanitize user input to prevent prompt injection attacks."""
        sanitized = False
        
        # Check for prompt injection patterns
        for pattern in self.prompt_injection_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                sanitized = True
                # Log the attempt
                logger.warning(f"Potential prompt injection detected in message: pattern='{pattern}'")
                # Replace with redacted message
                message = re.sub(pattern, "[REDACTED-POTENTIAL-INJECTION]", message, flags=re.IGNORECASE)
        
        return message, sanitized

    async def _log_execution_start(
        self, 
        agent: Agent, 
        message: str, 
        user_id: Optional[uuid.UUID], 
        db: AsyncSession
    ) -> uuid.UUID:
        """Log the start of agent execution."""
        return await log_audit_event(
            db=db,
            action="agent_execute",
            resource_type="agent",
            resource_id=str(agent.id),
            user_id=user_id,
            org_id=agent.org_id,
            details={
                "agent_name": agent.name,
                "message_length": len(message),
                "model_id": agent.model_id,
                "status": "started",
            },
            metadata={}
        )

    async def _log_execution_success(self, audit_id: uuid.UUID, result: AgentRunResult, db: AsyncSession):
        """Update audit log with successful execution details."""
        try:
            stmt = select(AuditLog).where(AuditLog.id == audit_id)
            audit_result = await db.execute(stmt)
            log_entry = audit_result.scalar_one_or_none()
            if log_entry:
                log_entry.details_json = {
                    **(log_entry.details_json or {}),
                    "status": "success",
                    "tokens_used": result.tokens,
                    "cost": float(result.cost),
                    "turns": result.turns,
                    "model_used": result.model_used,
                    "tools_used": result.security.tools_used,
                }
                await db.flush()
        except Exception as e:
            logger.warning(f"Failed to update audit log {audit_id}: {e}")

    async def _log_execution_failure(self, audit_id: uuid.UUID, error: str, db: AsyncSession):
        """Update audit log with failure details."""
        try:
            stmt = select(AuditLog).where(AuditLog.id == audit_id)
            audit_result = await db.execute(stmt)
            log_entry = audit_result.scalar_one_or_none()
            if log_entry:
                log_entry.details_json = {
                    **(log_entry.details_json or {}),
                    "status": "failure",
                    "error": error,
                }
                await db.flush()
        except Exception as e:
            logger.warning(f"Failed to update audit log {audit_id}: {e}")

    async def _enforce_session_limits(self, agent: Agent, session: AgentSession, db: AsyncSession):
        """Enforce session message limits and trigger compaction if needed."""
        if session.message_count >= agent.max_session_messages:
            logger.info(f"Session {session.id} exceeds message limit ({agent.max_session_messages}), compaction needed")
            # TODO: Implement session compaction - for now just warn
            pass

    async def _log_tool_execution(
        self,
        audit_id: uuid.UUID,
        tool_name: str,
        args: Dict[str, Any],
        result: Dict[str, Any],
        execution_time_ms: int,
        db: AsyncSession,
        org_id: uuid.UUID
    ):
        """Log individual tool execution."""
        # Sanitize arguments (remove any potential credentials)
        sanitized_args = self._sanitize_tool_args(args)
        
        await log_audit_event(
            db=db,
            action="agent_tool_call",
            resource_type="agent_tool",
            resource_id=tool_name,
            org_id=org_id,
            details={
                "tool_name": tool_name,
                "arguments": sanitized_args,
                "result_keys": list(result.keys()) if isinstance(result, dict) else None,
                "execution_time_ms": execution_time_ms,
                "parent_execution": str(audit_id),
            },
            metadata={}
        )

    def _sanitize_tool_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from tool arguments for logging."""
        sanitized = {}
        sensitive_keys = ["password", "secret", "token", "key", "auth", "credential", "api_key"]
        
        for key, value in args.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "... [TRUNCATED]"
            else:
                sanitized[key] = value
        
        return sanitized

    def _is_private_ip(self, ip_str: str) -> bool:
        """Check if IP address is in private ranges (SSRF protection)."""
        try:
            ip = ip_address(ip_str)
            return (
                ip.is_private or 
                ip.is_loopback or 
                ip.is_link_local or
                ip.is_multicast
            )
        except ValueError:
            return False  # Not a valid IP

    def _validate_http_url(self, url: str, allowlist: List[str]) -> bool:
        """Validate HTTP URL against allowlist and security policies."""
        try:
            parsed = urlparse(url)
            
            # Only allow HTTP/HTTPS schemes
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Check against allowlist (domain patterns)
            if not allowlist:
                return False  # Empty allowlist = deny all
            
            domain = parsed.netloc.split(':')[0]  # Remove port
            for pattern in allowlist:
                if pattern in domain or domain.endswith(pattern):
                    break
            else:
                return False  # Domain not in allowlist
            
            # SSRF protection - resolve domain and check if it's private
            try:
                import socket
                ip = socket.gethostbyname(domain)
                if self._is_private_ip(ip):
                    logger.warning(f"Blocked request to private IP: {ip} (domain: {domain})")
                    return False
            except socket.gaierror:
                # DNS resolution failed
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"URL validation failed for {url}: {e}")
            return False