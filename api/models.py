from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(str, Enum):
    GESTACAO = "gestacao"
    NASCIMENTO = "nascimento"
    INTERNACAO_NEONATAL = "internacao_neonatal"
    ALTA_MATERNIDADE = "alta_maternidade"
    TRIAGEM = "triagem"
    CONSULTA = "consulta"
    VACINACAO = "vacinacao"
    AGENDAMENTO = "agendamento"


class IntegrationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=160)
    source_system: str = Field(min_length=1, max_length=100)
    schema_version: str = Field(pattern=r"^\d+\.\d+$", max_length=20)
    event_type: EventType
    entity_type: str = Field(min_length=1, max_length=80)
    entity_external_id: str = Field(min_length=1, max_length=180)
    child_external_id: str | None = Field(default=None, max_length=180)
    unit_external_id: str | None = Field(default=None, max_length=180)
    occurred_at: datetime
    data: dict[str, Any]

    @field_validator(
        "event_id", "source_system", "entity_external_id", "child_external_id", "unit_external_id"
    )
    @classmethod
    def strip_identifiers(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Identificadores não podem ser vazios.")
        return value

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None:
            raise ValueError("occurred_at deve incluir fuso horário.")
        return value.astimezone(timezone.utc)


class IntegrationBatch(BaseModel):
    events: list[IntegrationEvent] = Field(min_length=1, max_length=500)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class SummaryRequest(BaseModel):
    source_system: str = Field(min_length=1, max_length=100)
    child_external_id: str = Field(min_length=1, max_length=180)


class MonitorUpdate(BaseModel):
    status: str = Field(pattern=r"^(NOVO|EM_ACOMPANHAMENTO|PENDENTE|RESOLVIDO|DESCARTADO)$")
    note: str | None = Field(default=None, max_length=2000)
    resolution_reason: str | None = Field(default=None, max_length=1000)
    responsible: str | None = Field(default=None, max_length=160)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=12, max_length=200)
    role: str = Field(pattern=r"^(PROFISSIONAL|LEITURA)$")


class SummaryValidation(BaseModel):
    professional: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=1000)


class RuleUpdate(BaseModel):
    enabled: bool
    priority: str = Field(pattern=r"^(BAIXA|MEDIA|ALTA|CRITICA)$")
    threshold_days: int | None = Field(default=None, ge=1, le=3650)
