from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class Agent(Base):
    __tablename__ = 'agents'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    intent = Column(Text)

class AgentLoop(Base):
    __tablename__ = 'agent_loops'

    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), primary_key=True)
    iteration = Column(Integer, primary_key=True)
    plan_result = Column(Text)
    execution_result = Column(Text)

    __table_args__ = (
        UniqueConstraint('agent_id', 'iteration', name='unique_agent_iteration'),
    )
