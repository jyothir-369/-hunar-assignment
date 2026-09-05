"""Agent CRUD endpoints — backed by Hunar Voice API + local DB."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.agent import Agent
from src.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from src.services.hunar_client import HunarAPIError, HunarClient

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("/", response_model=AgentListResponse)
def list_agents(
    page: int = 1,
    page_size: int = 20,
    language: Optional[str] = None,
    agent_status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> AgentListResponse:
    """List locally-stored agents, paginated."""
    stmt = select(Agent)
    if language:
        stmt = stmt.where(Agent.language == language)
    if agent_status:
        stmt = stmt.where(Agent.status == agent_status)

    total = len(db.execute(stmt).scalars().all())
    rows = (
        db.execute(stmt.offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return AgentListResponse(count=total, results=rows)


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(agent_data: AgentCreate, db: Session = Depends(get_db)) -> Agent:
    """Create the agent on the Hunar API, then store the local reference."""
    hunar = HunarClient()
    hunar_payload = {
        "name": agent_data.name,
        "language": agent_data.language,
        "voice_persona": agent_data.voice_persona,
        "persona_name": agent_data.persona_name,
        "agent_prompt": agent_data.agent_prompt,
        "introduction": agent_data.introduction,
        "objective": agent_data.objective,
        "result_prompt": agent_data.result_prompt,
        "result_schema": agent_data.result_schema,
    }
    try:
        hunar_response = hunar.create_agent(hunar_payload)
    except HunarAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    hunar_agent_id = hunar_response.get("id")
    if not hunar_agent_id:
        raise HTTPException(
            status_code=502,
            detail="Hunar API did not return an agent id",
        )

    agent = Agent(
        name=agent_data.name,
        hunar_agent_id=hunar_agent_id,
        voice_persona=agent_data.voice_persona,
        persona_name=agent_data.persona_name,
        language=agent_data.language,
        agent_prompt=agent_data.agent_prompt,
        introduction=agent_data.introduction,
        objective=agent_data.objective,
        result_prompt=agent_data.result_prompt,
        result_schema=agent_data.result_schema,
        status="ACTIVE",
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str, agent_data: AgentUpdate, db: Session = Depends(get_db)
) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    hunar_update = agent_data.model_dump(exclude_unset=True, exclude_none=True)
    if hunar_update:
        hunar = HunarClient()
        try:
            hunar.update_agent(agent.hunar_agent_id, hunar_update)
        except HunarAPIError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    for field, value in agent_data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, db: Session = Depends(get_db)) -> None:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.delete(agent)
    db.commit()
    return None
