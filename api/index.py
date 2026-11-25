import hmac
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from io import BytesIO

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .database import ensure_indexes, get_db
from .models import (
    IntegrationBatch,
    IntegrationEvent,
    LoginRequest,
    MonitorUpdate,
    RuleUpdate,
    SummaryRequest,
    SummaryValidation,
    UserCreate,
)
from .security import (
    SESSION_COOKIE,
    authenticate_user,
    current_user,
    integration_auth,
    issue_session,
)
from .services import (
    audit,
    children_list,
    child_detail,
    configure_rule,
    create_discharge_summary,
    dashboard,
    ensure_default_rules,
    hash_password,
    json_safe,
    list_summaries,
    process_event,
    refresh_child_monitorings,
    update_monitoring,
)


def _admin(user=Depends(current_user)):
    if user.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Ação exclusiva de administrador."})
    return user


def _professional(user=Depends(current_user)):
    if user.get("role") not in ("ADMIN", "PROFISSIONAL"):
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Ação não autorizada."})
    return user


def _seed_admin(db):
    username = os.environ.get("APP_ADMIN_USERNAME", "").strip()
    password = os.environ.get("APP_ADMIN_PASSWORD", "")
    if username and len(password) >= 12:
        db.usuarios.update_one({"username": username}, {"$setOnInsert": {
            "username": username,
            "password": hash_password(password),
            "role": "ADMIN",
            "active": True,
            "created_at": datetime.now(timezone.utc),
        }}, upsert=True)


@asynccontextmanager
async def lifespan(app):
    db = get_db()
    db.command("ping")
    ensure_indexes(db)
    ensure_default_rules(db)
    _seed_admin(db)
    yield


app = FastAPI(
    title="Caderneta Digital API",
    version="1.0.0",
    description="Integração complementar por eventos HTTP/JSON; não conecta ao SQL Server.",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    try:
        get_db().recebimentos_integracao.insert_one({
            "status": "REJEITADO_VALIDACAO",
            "path": request.url.path,
            "error_codes": [item.get("type", "invalid") for item in exc.errors()],
            "received_at": datetime.now(timezone.utc),
        })
    except Exception:
        pass
    return JSONResponse(status_code=422, content={"ok": False, "error": {
        "code": "validation_error",
        "message": "O registro não corresponde ao contrato de integração.",
        "fields": [{
            "field": ".".join(str(part) for part in item.get("loc", [])),
            "message": item.get("msg", "Inválido."),
        } for item in exc.errors()],
    }})


@app.get("/api/health")
def health():
    try:
        db = get_db()
        db.command("ping")
        return {"ok": True, "service": "caderneta-digital", "database": db.name}
    except Exception:
        raise HTTPException(status_code=503, detail={
            "code": "database_unavailable",
            "message": "Banco complementar indisponível.",
        })


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, response: Response):
    user = authenticate_user(get_db(), payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail={
            "code": "invalid_credentials", "message": "Usuário ou senha incorretos.",
        })
    response.set_cookie(
        SESSION_COOKIE,
        issue_session(user["username"], user["role"]),
        httponly=True,
        secure=os.environ.get("VERCEL", "") == "1",
        samesite="lax",
        max_age=8 * 60 * 60,
        path="/",
    )
    return {"ok": True, "user": user}


@app.post("/api/v1/auth/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax")
    return {"ok": True}


@app.get("/api/v1/auth/me")
def me(user=Depends(current_user)):
    return {"ok": True, "user": user}


@app.post("/api/v1/integracao/registros", status_code=202)
def receive_event(event: IntegrationEvent, _actor=Depends(integration_auth)):
    try:
        return {"ok": True, "data": process_event(get_db(), event)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_event", "message": str(exc)})


@app.post("/api/v1/integracao/registros/lote", status_code=202)
def receive_batch(batch: IntegrationBatch, _actor=Depends(integration_auth)):
    results = []
    for event in batch.events:
        try:
            results.append({"ok": True, "data": process_event(get_db(), event)})
        except Exception as exc:
            results.append({
                "ok": False,
                "event_id": event.event_id,
                "error": {"code": "processing_error", "message": type(exc).__name__},
            })
    return {"ok": all(item["ok"] for item in results), "received": len(results), "results": results}


@app.get("/api/v1/integracao/registros/{event_id}")
def read_event(event_id: str, source_system: str | None = None, _actor=Depends(integration_auth)):
    query = {"event_id": event_id}
    if source_system:
        query["source_system"] = source_system
    event = json_safe(get_db().eventos_integracao.find_one(query))
    if not event:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Evento não encontrado."})
    return {"ok": True, "data": event}


@app.get("/api/v1/eventos")
def read_events(
    event_type: str | None = None,
    unit: str | None = None,
    status: str | None = None,
    child_external_id: str | None = None,
    limit: int = 500,
    _user=Depends(current_user),
):
    query = {}
    if event_type:
        query["event_type"] = event_type
    if unit:
        query["unit_external_id"] = unit
    if status:
        query["data.status"] = status
    if child_external_id:
        query["child_external_id"] = child_external_id
    safe_limit = min(max(limit, 1), 1000)
    items = get_db().eventos_integracao.find(query).sort("occurred_at", -1).limit(safe_limit)
    return {"items": [json_safe(item) for item in items]}


@app.get("/api/v1/dashboard")
def read_dashboard(unit: str | None = None, _user=Depends(current_user)):
    return dashboard(get_db(), unit)


@app.get("/api/v1/criancas")
def read_children(unit: str | None = None, q: str | None = None, _user=Depends(current_user)):
    return {"items": children_list(get_db(), unit=unit, query=q)}


@app.get("/api/v1/criancas/{external_id}")
def read_child(external_id: str, source_system: str, _user=Depends(current_user)):
    result = child_detail(get_db(), source_system, external_id)
    if not result:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Criança não encontrada."})
    return result


@app.get("/api/v1/monitoramentos")
def read_monitorings(
    status: str | None = None,
    priority: str | None = None,
    unit: str | None = None,
    q: str | None = None,
    _user=Depends(current_user),
):
    query = {}
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if unit:
        query["unit_external_id"] = unit
    if q:
        query["child_external_id"] = {"$regex": q, "$options": "i"}
    items = get_db().monitoramentos.find(query).sort("updated_at", -1).limit(1000)
    return {"items": [json_safe(item) for item in items]}


@app.patch("/api/v1/monitoramentos/{monitor_id}")
def patch_monitoring(monitor_id: str, payload: MonitorUpdate, user=Depends(_professional)):
    try:
        result = update_monitoring(get_db(), monitor_id, payload, user["username"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_update", "message": str(exc)})
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Ocorrência não encontrada."})
    return {"ok": True, "data": result}


@app.get("/api/v1/resumos-alta")
def read_summaries(source_system: str | None = None, child_external_id: str | None = None, _user=Depends(current_user)):
    return {"items": list_summaries(get_db(), source_system, child_external_id)}


@app.post("/api/v1/resumos-alta", status_code=201)
def post_summary(payload: SummaryRequest, user=Depends(_professional)):
    result = create_discharge_summary(get_db(), payload.source_system, payload.child_external_id, user["username"])
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Criança não encontrada."})
    return {"ok": True, "data": result}


@app.patch("/api/v1/resumos-alta/{document_id}/validar")
def validate_summary(document_id: str, payload: SummaryValidation, user=Depends(_professional)):
    if user["role"] != "PROFISSIONAL":
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Somente profissional pode validar resumo."})
    db = get_db()
    summary = db.resumos_alta.find_one({"document_id": document_id})
    if not summary:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Resumo não encontrado."})
    if user["role"] != "ADMIN" and user["role"] != "PROFISSIONAL":
        raise HTTPException(status_code=403, detail={"code": "forbidden", "message": "Ação não autorizada."})
    now = datetime.now(timezone.utc)
    db.resumos_alta.update_one({"_id": summary["_id"]}, {"$set": {
                "status": "VALIDADO", "validated_by": user["username"], "validated_at": now,
        "validation_note": payload.note, "updated_at": now,
    }})
    audit(db, user["username"], "resumo_validado", "resumo_alta", document_id,
                    {"professional": user["username"], "validated_at": now.isoformat()})
    return {"ok": True, "data": json_safe(db.resumos_alta.find_one({"_id": summary["_id"]}))}


@app.get("/api/v1/resumos-alta/{document_id}/pdf")
def summary_pdf(document_id: str, _user=Depends(current_user)):
    summary = get_db().resumos_alta.find_one({"document_id": document_id})
    if not summary:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Resumo não encontrado."})
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, title="Caderneta Digital | Resumo de alta")
    styles = getSampleStyleSheet()
    story = [Paragraph("Caderneta Digital | Resumo de Alta", styles["Title"]), Spacer(1, 10)]
    story.append(Paragraph(f"Documento: {document_id}", styles["Normal"]))
    story.append(Paragraph(f"Gerado em: {summary.get('generated_at')}", styles["Normal"]))
    story.append(Paragraph("Dados recebidos do sistema de origem; campos ausentes não foram inferidos.", styles["Normal"]))
    for section, content in summary.get("sections", {}).items():
        story.extend([Spacer(1, 10), Paragraph(section.replace("_", " ").title(), styles["Heading2"])])
        rows = content.items() if isinstance(content, dict) else [("Registro", item) for item in content] if isinstance(content, list) else [("Informação", content)]
        table = Table([[str(key), str(value) if value not in (None, "") else "Sem informação disponível"] for key, value in rows], colWidths=[150, 350])
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 5)]))
        story.append(table)
    if summary.get("missing_fields"):
        story.append(Paragraph("Campos sem informação: " + ", ".join(summary["missing_fields"]), styles["Normal"]))
    story.append(Spacer(1, 14))
    story.append(Paragraph("Documento informativo. Não substitui prontuário ou avaliação profissional e não possui assinatura digital legal.", styles["Italic"]))
    document.build(story)
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="caderneta-alta-{document_id}.pdf"'
    })


@app.get("/api/v1/relatorios")
def reports(_user=Depends(current_user)):
    db = get_db()
    events = list(db.eventos_integracao.find({}, {"event_type": 1, "unit_external_id": 1, "occurred_at": 1}))
    monitorings = list(db.monitoramentos.find({}, {"status": 1, "priority": 1, "unit_external_id": 1}))
    return {
        "events_by_type": _count_by(events, "event_type"),
        "events_by_unit": _count_by(events, "unit_external_id"),
        "monitorings_by_status": _count_by(monitorings, "status"),
        "monitorings_by_priority": _count_by(monitorings, "priority"),
    }


@app.get("/api/v1/admin/rules")
def read_rules(_user=Depends(_admin)):
    db = get_db()
    ensure_default_rules(db)
    items = db.regras_monitoramento.find().sort("rule_id", 1)
    return {"items": [json_safe(item) for item in items]}


@app.patch("/api/v1/admin/rules/{rule_id}")
def patch_rule(rule_id: str, payload: RuleUpdate, user=Depends(_admin)):
    try:
        result = configure_rule(get_db(), rule_id, payload, user["username"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_rule", "message": str(exc)})
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": "Regra não encontrada."})
    return {"ok": True, "data": result}


@app.get("/api/v1/admin/users")
def read_users(_user=Depends(_admin)):
    items = get_db().usuarios.find({}, {"password": 0}).sort("username", 1)
    return {"items": [json_safe(item) for item in items]}


@app.get("/api/v1/auditoria")
def read_audit(limit: int = 100, _admin_user=Depends(_admin)):
    safe_limit = min(max(limit, 1), 500)
    items = get_db().auditoria.find().sort("created_at", -1).limit(safe_limit)
    return {"items": [json_safe(item) for item in items]}


@app.post("/api/v1/usuarios", status_code=201)
def create_user(payload: UserCreate, user=Depends(_admin)):
    db = get_db()
    if db.usuarios.find_one({"username": payload.username}):
        raise HTTPException(status_code=409, detail={"code": "already_exists", "message": "Usuário já existe."})
    db.usuarios.insert_one({
        "username": payload.username, "password": hash_password(payload.password),
        "role": payload.role, "active": True, "created_at": datetime.now(timezone.utc),
    })
    audit(db, user["username"], "usuario_criado", "usuario", payload.username, {"role": payload.role})
    return {"ok": True, "username": payload.username, "role": payload.role}


@app.get("/api/cron/monitoramentos")
def cron_monitorings(authorization: str | None = Header(default=None)):
    secret = os.environ.get("CRON_SECRET", "")
    if not secret or not authorization or not hmac.compare_digest(authorization, f"Bearer {secret}"):
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Chave de cron inválida."})
    db = get_db()
    checked = 0
    for child in db.criancas.find({}, {"source_system": 1, "external_id": 1}):
        if child.get("source_system") and child.get("external_id"):
            refresh_child_monitorings(db, child["source_system"], child["external_id"], actor="cron")
            checked += 1
    return {"ok": True, "children_checked": checked}
