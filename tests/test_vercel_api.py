from datetime import datetime, timezone

import mongomock
import pytest
from fastapi.testclient import TestClient

import api.index as api


@pytest.fixture
def app_client(monkeypatch):
    database = mongomock.MongoClient().caderneta_digital_test
    monkeypatch.setenv("API_INTEGRATION_KEY", "test-integration-secret-32-bytes")
    monkeypatch.setenv("MONGO_DATABASE", "caderneta_digital_test")
    monkeypatch.setenv("APP_ADMIN_USERNAME", "admin-test")
    monkeypatch.setenv("APP_ADMIN_PASSWORD", "synthetic-test-password")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-with-at-least-32-bytes")
    monkeypatch.setattr(api, "get_db", lambda: database)
    with TestClient(api.app) as client:
        yield client, database


def evento(event_id="evt-test-1"):
    return {
        "event_id": event_id,
        "source_system": "sistema_relacional_teste",
        "schema_version": "1.0",
        "event_type": "nascimento",
        "entity_type": "crianca",
        "entity_external_id": "CRI-TEST-1",
        "child_external_id": "CRI-TEST-1",
        "unit_external_id": "UBS-TEST-1",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "data": {
            "nome": "Criança Sintética",
            "data_nascimento": "2026-11-20",
            "sexo": "F",
            "peso_nascimento": 3050,
        },
    }


def test_health_uses_dedicated_mongodb_database(app_client):
    client, _ = app_client
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "caderneta-digital", "database": "caderneta_digital_test"}


def test_integration_requires_api_key(app_client):
    client, _ = app_client
    response = client.post("/api/v1/integracao/registros", json=evento())
    assert response.status_code == 401


def test_replayed_event_is_idempotent(app_client):
    client, database = app_client
    payload = evento()
    headers = {"X-API-Key": "test-integration-secret-32-bytes"}
    first = client.post("/api/v1/integracao/registros", json=payload, headers=headers)
    replay = client.post("/api/v1/integracao/registros", json=payload, headers=headers)
    assert first.status_code == replay.status_code == 202
    assert first.json()["data"]["status"] == "PROCESSADO"
    assert replay.json()["data"]["duplicate"] is True
    assert database.eventos_integracao.count_documents({"event_id": payload["event_id"]}) == 1
    child = database.criancas.find_one({"external_id": "CRI-TEST-1"})
    assert child["projections"]["nascimento"]["data"]["peso_nascimento"] == 3050


def test_source_ddl_field_names_are_normalized(app_client):
    client, database = app_client
    payload = evento("evt-ddl-fields")
    payload["entity_external_id"] = payload["child_external_id"] = "CRI-TEST-DDL"
    payload["data"] = {
        "nome": "Criança Sintética DDL",
        "data_nascimento": "2026-11-20",
        "sexo": "F",
        "peso_g": 3050,
        "comprimento_cm": 49.5,
        "perimetro_cefalico_cm": 34.0,
        "ig_semanas": 38,
        "ig_dias": 2,
        "apgar_1min": 8,
        "apgar_5min": 9,
    }
    response = client.post("/api/v1/integracao/registros", json=payload, headers={
        "X-API-Key": "test-integration-secret-32-bytes",
    })
    assert response.status_code == 202
    projection = database.criancas.find_one({"external_id": "CRI-TEST-DDL"})["projections"]["nascimento"]["data"]
    assert projection["peso_nascimento"] == 3050
    assert projection["comprimento_nascimento"] == 49.5
    assert projection["perimetro_cefalico"] == 34.0
    assert projection["idade_gestacional_semanas"] == 38
    assert projection["apgar_5min"] == 9


def test_sql_triage_codes_and_realizada_flag_are_preserved(app_client):
    client, database = app_client
    headers = {"X-API-Key": "test-integration-secret-32-bytes"}
    birth = evento("evt-triagem-rn")
    birth["entity_external_id"] = birth["child_external_id"] = "CRI-TEST-TRIAGEM"
    client.post("/api/v1/integracao/registros", json=birth, headers=headers)
    triage = evento("evt-triagem-biologica")
    triage.update({"event_type": "triagem", "entity_external_id": "CRI-TEST-TRIAGEM", "child_external_id": "CRI-TEST-TRIAGEM"})
    triage["data"] = {"codigo": "BIOLOGICA", "realizada": False, "data_realizacao": None}
    response = client.post("/api/v1/integracao/registros", json=triage, headers=headers)
    assert response.status_code == 202
    occurrence = database.monitoramentos.find_one({
        "child_external_id": "CRI-TEST-TRIAGEM",
        "occurrence_key": "pezinho:nao_realizado",
    })
    assert occurrence["data_state"] == "NAO_REALIZADO_CONFIRMADO_PELA_ORIGEM"


def test_ui_requires_login_and_dashboard_works_with_empty_mongo(app_client):
    client, _ = app_client
    assert client.get("/api/v1/dashboard").status_code == 401
    login = client.post("/api/v1/auth/login", json={
        "username": "admin-test",
        "password": "synthetic-test-password",
    })
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "ADMIN"
    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["children_received"] == 0
    assert dashboard.json()["metrics"]["completeness_percent"] == 0


def test_authenticated_events_endpoint_supports_filters(app_client):
    client, database = app_client
    client.post("/api/v1/auth/login", json={
        "username": "admin-test",
        "password": "synthetic-test-password",
    })
    headers = {"X-API-Key": "test-integration-secret-32-bytes"}
    client.post("/api/v1/integracao/registros", json=evento(), headers=headers)
    response = client.get("/api/v1/eventos?event_type=nascimento&unit=UBS-TEST-1")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["event_id"] == "evt-test-1"


def test_admin_temporal_rule_requires_a_threshold(app_client):
    client, _ = app_client
    client.post("/api/v1/auth/login", json={
        "username": "admin-test",
        "password": "synthetic-test-password",
    })
    listing = client.get("/api/v1/admin/rules")
    assert listing.status_code == 200
    rule = next(item for item in listing.json()["items"] if item["rule_id"] == "alta_sem_consulta")
    assert rule["enabled"] is False and rule["threshold_days"] is None
    missing_threshold = client.patch("/api/v1/admin/rules/alta_sem_consulta", json={
        "enabled": True, "priority": "BAIXA",
    })
    assert missing_threshold.status_code == 422
    configured = client.patch("/api/v1/admin/rules/alta_sem_consulta", json={
        "enabled": True, "priority": "BAIXA", "threshold_days": 7,
    })
    assert configured.status_code == 200
    assert configured.json()["data"]["threshold_days"] == 7


def test_admin_creates_users_with_hashed_password_and_audit(app_client):
    client, database = app_client
    client.post("/api/v1/auth/login", json={
        "username": "admin-test",
        "password": "synthetic-test-password",
    })
    response = client.post("/api/v1/usuarios", json={
        "username": "profissional-test",
        "password": "temporary-synthetic-password",
        "role": "PROFISSIONAL",
    })
    assert response.status_code == 201
    assert "password" not in response.json()
    stored = database.usuarios.find_one({"username": "profissional-test"})
    assert stored["password"]["digest"]
    assert stored["password"]["digest"] != "temporary-synthetic-password"
    assert database.auditoria.count_documents({"action": "usuario_criado"}) == 1


def test_summary_validation_uses_authenticated_professional_identity(app_client):
    client, database = app_client
    from api.services import hash_password

    database.usuarios.insert_one({
        "username": "professional-test",
        "password": hash_password("professional-synthetic-password"),
        "role": "PROFISSIONAL",
        "active": True,
    })
    database.resumos_alta.insert_one({
        "document_id": "summary-test-1",
        "source_system": "synthetic",
        "child_external_id": "CHILD-TEST-1",
        "status": "PENDENTE_VALIDACAO",
    })

    client.post("/api/v1/auth/login", json={"username": "admin-test", "password": "synthetic-test-password"})
    forbidden = client.patch("/api/v1/resumos-alta/summary-test-1/validar", json={"professional": "forged-name"})
    assert forbidden.status_code == 403

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"username": "professional-test", "password": "professional-synthetic-password"})
    accepted = client.patch("/api/v1/resumos-alta/summary-test-1/validar", json={"professional": "forged-name"})
    assert accepted.status_code == 200
    assert database.resumos_alta.find_one({"document_id": "summary-test-1"})["validated_by"] == "professional-test"
