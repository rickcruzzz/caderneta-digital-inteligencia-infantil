import base64
import hashlib
import json
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from bson import ObjectId

from .database import ensure_indexes

FIELD_ALIASES = {
    "nome": ("nome", "name", "child_name"),
    "data_nascimento": ("data_nascimento", "birth_date"),
    "sexo": ("sexo", "sex"),
    "peso_nascimento": ("peso_nascimento", "peso_ao_nascer", "peso_g", "birth_weight"),
    "comprimento_nascimento": ("comprimento_nascimento", "comprimento_ao_nascer", "comprimento_cm", "birth_length"),
    "perimetro_cefalico": ("perimetro_cefalico", "perimetro_cefalico_nascimento", "perimetro_cefalico_cm", "head_circumference"),
    "idade_gestacional_semanas": ("idade_gestacional_semanas", "ig_semanas", "gestational_age_weeks"),
    "idade_gestacional_dias": ("idade_gestacional_dias", "ig_dias"),
    "apgar_1min": ("apgar_1min", "apgar_1_minuto"),
    "apgar_5min": ("apgar_5min", "apgar_5_minutos"),
    "hora_nascimento": ("hora_nascimento", "birth_time"),
    "tipo_sanguineo": ("tipo_sanguineo", "grupo_sanguineo"),
    "fator_rh": ("fator_rh",),
    "data_parto": ("data_parto", "delivery_date"),
    "local_tipo": ("local_tipo", "delivery_location_type"),
    "tipo_parto": ("tipo_parto", "birth_type"),
    "idade_gestacional_semanas": ("idade_gestacional_semanas", "ig_semanas", "gestational_age_weeks"),
    "tipo_parto": ("tipo_parto", "birth_type"),
    "data_alta": ("data_alta", "discharge_date"),
    "data_internacao": ("data_internacao", "data_inicio", "admission_date"),
    "motivo_internacao": ("motivo_internacao", "motivo", "admission_reason"),
    "tipo_triagem": ("tipo_triagem", "codigo", "triagem", "screening_type"),
    "realizada": ("realizada",),
    "status": ("status", "situacao", "state"),
    "resultado": ("resultado", "result"),
    "data_procedimento": ("data_procedimento", "data_realizacao", "performed_at"),
    "vacina": ("vacina", "vaccine"),
    "dose": ("dose", "dose_name"),
    "data_aplicacao": ("data_aplicacao", "application_date"),
    "data_consulta": ("data_consulta", "appointment_date"),
    "data_agendamento": ("data_agendamento", "data_hora", "scheduled_at"),
    "alimentacao": ("alimentacao", "aleitamento", "feeding"),
    "orientacoes": ("orientacoes", "resumo_alta", "conduta", "discharge_instructions"),
    "peso_alta_g": ("peso_alta_g",),
    "comprimento_alta_cm": ("comprimento_alta_cm",),
    "medicamentos": ("medicamentos", "medications", "prescricoes"),
    "encaminhamentos": ("encaminhamentos", "referrals"),
    "procedimentos_registrados": ("procedimentos_registrados", "procedures_recorded"),
    "evolucao_registrada": ("evolucao_registrada", "evolucao_clinica", "clinical_evolution"),
    "condicao_alta": ("condicao_alta", "discharge_condition"),
    "diagnosticos_registrados": ("diagnosticos_registrados", "diagnoses_recorded"),
    "unidade_hospitalar": ("unidade_hospitalar", "hospital_name"),
    "unidade_referencia": ("unidade_referencia", "reference_unit"),
    "profissional": ("profissional", "professional"),
}
SCREENINGS = {
    "pezinho": {"label": "Teste do pezinho", "aliases": {"pezinho", "teste_pezinho", "teste do pezinho", "newborn_blood_spot", "BIOLOGICA"}},
    "orelhinha": {"label": "Teste da orelhinha", "aliases": {"orelhinha", "teste_orelhinha", "teste da orelhinha", "hearing", "AUDITIVA"}},
    "olhinho": {"label": "Teste do olhinho", "aliases": {"olhinho", "teste_olhinho", "teste do olhinho", "eye", "REFLEXO_VERMELHO"}},
    "coracaozinho": {"label": "Teste do coraçãozinho", "aliases": {"coracaozinho", "coraçãozinho", "teste_coracaozinho", "teste do coraçãozinho", "pulse_oximetry", "OXIMETRIA"}},
}
DONE_STATES = {"realizado", "realizada", "concluido", "concluida", "done", "completed"}
PENDING_STATES = {"pendente", "pending", "agendado", "agendada"}
NOT_DONE_STATES = {"nao_realizado", "nao_realizada", "not_performed", "not_done"}
TEMPORAL_RULES = {
    "alta_sem_consulta": ("ALTA_SEM_CONSULTA", "Sem evento de consulta após o intervalo configurado para acompanhamento da alta."),
    "dados_desatualizados": ("DADOS_DESATUALIZADOS", "Nenhum evento de origem recebido dentro do intervalo configurado."),
}


def utcnow():
    return datetime.now(timezone.utc)


def as_utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return as_utc(value).isoformat()
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items() if key != "_id"}
    return value


def normalized_projection(data):
    result = {}
    for target, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in data:
                result[target] = data[alias]
                break
    return result


def event_hash(event):
    canonical = json.dumps(event, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def canonical_screening(value):
    text = str(value or "").strip().casefold()
    for key, screening in SCREENINGS.items():
        if text in {alias.casefold() for alias in screening["aliases"]}:
            return key
    return None


def canonical_status(value):
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return "_".join(text.replace("-", " ").split())


def audit(db, actor, action, entity_type, entity_id, details=None):
    db.auditoria.insert_one({
        "actor": actor,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "details": details or {},
        "created_at": utcnow(),
    })


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return {"salt": base64.b64encode(salt).decode(), "digest": base64.b64encode(digest).decode()}


def verify_password(password, encoded):
    try:
        salt = base64.b64decode(encoded["salt"])
        expected = base64.b64decode(encoded["digest"])
    except (KeyError, ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return hashlib.compare_digest(actual, expected) if hasattr(hashlib, "compare_digest") else secrets.compare_digest(actual, expected)


def ensure_default_rules(db):
    now = utcnow()
    for key, screening in SCREENINGS.items():
        db.regras_monitoramento.update_one({"rule_id": f"triagem_sem_informacao_{key}"}, {"$setOnInsert": {
            "rule_id": f"triagem_sem_informacao_{key}", "enabled": True,
            "priority": "BAIXA", "screening_key": key,
            "description": f"Sem evento de origem recebido para {screening['label']}; solicitar verificação da informação.",
            "clinical_protocol": False, "created_at": now,
        }}, upsert=True)
    for rule_id, description in [
        ("alta_sem_consulta", "Acompanhamento após alta; configure o prazo local aprovado antes de ativar."),
        ("dados_desatualizados", "Atualização de dados; configure o intervalo local aprovado antes de ativar."),
    ]:
        db.regras_monitoramento.update_one({"rule_id": rule_id}, {"$setOnInsert": {
            "rule_id": rule_id, "enabled": False, "priority": "BAIXA", "threshold_days": None,
            "description": description, "clinical_protocol": False, "created_at": now,
        }}, upsert=True)


def resolve_occurrence(db, key, actor, now, reason):
    existing = db.monitoramentos.find_one(key)
    if existing and existing.get("status") not in ("RESOLVIDO", "DESCARTADO"):
        db.monitoramentos.update_one({"_id": existing["_id"]}, {
            "$set": {"status": "RESOLVIDO", "updated_at": now, "resolution_reason": reason, "resolved_at": now},
            "$push": {"history": {"actor": actor, "from": existing.get("status"), "to": "RESOLVIDO", "at": now}},
        })


def record_occurrence(db, key, fields, actor, now):
    result = db.monitoramentos.update_one(key, {"$setOnInsert": {
        **key, **fields, "status": fields.get("initial_status", "NOVO"),
        "identified_at": now, "created_at": now, "updated_at": now,
        "responsible": None, "note": None,
        "history": [{"actor": actor, "from": None, "to": fields.get("initial_status", "NOVO"), "at": now}],
    }}, upsert=True)
    return str(result.upserted_id) if result.upserted_id else None


def refresh_temporal_rules(db, child, source_system, child_external_id, actor, now):
    changed = []
    for rule_id, (occurrence_type, default_description) in TEMPORAL_RULES.items():
        rule = db.regras_monitoramento.find_one({"rule_id": rule_id}) or {}
        threshold = rule.get("threshold_days")
        if not rule.get("enabled") or not isinstance(threshold, int) or threshold < 1:
            continue
        key = {"source_system": source_system, "child_external_id": child_external_id,
               "rule_id": rule_id, "occurrence_key": rule_id}
        trigger = False
        reason = rule.get("description", default_description)
        if rule_id == "alta_sem_consulta":
            discharge = child.get("projections", {}).get("alta_maternidade")
            if discharge and discharge.get("occurred_at"):
                discharge_time = as_utc(discharge["occurred_at"])
                due = now >= discharge_time + timedelta(days=threshold)
                consultations = list(db.eventos_integracao.find({
                    "source_system": source_system, "child_external_id": child_external_id,
                    "event_type": "consulta",
                }))
                follow_up = any(as_utc(item["occurred_at"]) > discharge_time for item in consultations)
                trigger = due and not follow_up
                reason = f"Nenhum evento de consulta foi recebido em {threshold} dias configurados após a alta."
        else:
            last_update = child.get("updated_at")
            if last_update:
                trigger = now >= as_utc(last_update) + timedelta(days=threshold)
                reason = f"Nenhum evento foi recebido em {threshold} dias configurados."

        if trigger:
            created = record_occurrence(db, key, {
                "unit_external_id": child.get("unit_external_id"), "type": occurrence_type,
                "description": reason, "rule_reason": rule.get("description", default_description),
                "data_state": "SEM_EVENTO_NO_INTERVALO_CONFIGURADO", "priority": rule.get("priority", "BAIXA"),
                "threshold_days": threshold, "initial_status": "PENDENTE",
            }, actor, now)
            if created:
                changed.append(created)
        else:
            resolve_occurrence(db, key, actor, now, "Evento posterior recebido ou intervalo configurado ainda não transcorrido.")
    return changed


def refresh_child_monitorings(db, source_system, child_external_id, actor="motor_regras"):
    ensure_default_rules(db)
    child = db.criancas.find_one({"source_system": source_system, "external_id": child_external_id})
    if not child:
        return []
    projections = child.get("projections", {})
    if not projections.get("nascimento") and not projections.get("alta_maternidade"):
        return []
    events = list(db.eventos_integracao.find({
        "source_system": source_system, "child_external_id": child_external_id, "event_type": "triagem",
    }).sort("occurred_at", -1))
    latest = {}
    for event in events:
        data = event.get("data", {})
        key = canonical_screening(data.get("tipo_triagem") or data.get("codigo") or data.get("triagem") or data.get("screening_type"))
        if key and key not in latest:
            latest[key] = event

    changed = []
    now = utcnow()
    for key, screening in SCREENINGS.items():
        rule = db.regras_monitoramento.find_one({"rule_id": f"triagem_sem_informacao_{key}"}) or {}
        if not rule.get("enabled", False):
            continue
        event = latest.get(key)
        base_key = {"source_system": source_system, "child_external_id": child_external_id, "rule_id": rule["rule_id"]}
        missing_key = {**base_key, "occurrence_key": key}
        if not event:
            description = f"Sem informação recebida sobre {screening['label']}. Verifique com a origem; ausência de evento não confirma não realização."
            created = record_occurrence(db, missing_key, {
                "unit_external_id": child.get("unit_external_id"), "type": "TRIAGEM_SEM_INFORMACAO",
                "description": description, "rule_reason": rule.get("description", description),
                "data_state": "SEM_INFORMACAO", "priority": rule.get("priority", "BAIXA"), "initial_status": "NOVO",
            }, actor, now)
            if created:
                changed.append(created)
            continue

        data = event.get("data", {})
        raw_status = data.get("status") or data.get("situacao") or data.get("state")
        if raw_status is None and isinstance(data.get("realizada"), bool):
            raw_status = "realizado" if data["realizada"] else "não realizado"
        state = canonical_status(raw_status)
        resolve_occurrence(db, missing_key, actor, now, "Evento de triagem recebido do sistema de origem.")
        if state in DONE_STATES:
            for suffix in ("pendente", "nao_realizado", "status_nao_mapeado"):
                resolve_occurrence(db, {**base_key, "occurrence_key": f"{key}:{suffix}"}, actor, now,
                    "A origem atualizou a triagem como realizada.")
            continue

        if state in PENDING_STATES:
            occurrence_type, suffix = "TRIAGEM_PENDENTE", "pendente"
            data_state, initial_status = "PENDENTE_INFORMADO_PELA_ORIGEM", "PENDENTE"
            description = f"A origem informou situação pendente para {screening['label']}. Confirme a atualização com a equipe responsável."
        elif state in NOT_DONE_STATES:
            occurrence_type, suffix = "TRIAGEM_NAO_REALIZADA", "nao_realizado"
            data_state, initial_status = "NAO_REALIZADO_CONFIRMADO_PELA_ORIGEM", "NOVO"
            description = f"A origem confirmou que {screening['label']} não foi realizado. Avaliação e encaminhamento cabem à equipe responsável."
        else:
            occurrence_type, suffix = "TRIAGEM_STATUS_NAO_MAPEADO", "status_nao_mapeado"
            data_state, initial_status = "STATUS_ORIGEM_NAO_INTERPRETADO", "PENDENTE"
            description = f"Há um registro de {screening['label']}, mas o status de origem não foi reconhecido. Confirme o mapeamento."
        occurrence_key = f"{key}:{suffix}"
        created = record_occurrence(db, {**base_key, "occurrence_key": occurrence_key}, {
            "unit_external_id": child.get("unit_external_id"), "type": occurrence_type,
            "description": description, "rule_reason": f"Status recebido da origem: {raw_status or 'sem status'}.",
            "data_state": data_state, "source_status": raw_status,
            "priority": rule.get("priority", "BAIXA"), "initial_status": initial_status,
        }, actor, now)
        if created:
            changed.append(created)

    changed.extend(refresh_temporal_rules(db, child, source_system, child_external_id, actor, now))
    return changed


def process_event(db, incoming):
    event = incoming.model_dump(mode="python") if hasattr(incoming, "model_dump") else dict(incoming)
    if len(json.dumps(event, ensure_ascii=False, default=str).encode()) > 256_000:
        raise ValueError("Evento excede o limite de 256 KB.")
    event_type_value = event["event_type"]
    event_type = event_type_value.value if hasattr(event_type_value, "value") else str(event_type_value)
    occurred_at = as_utc(event["occurred_at"])
    key = {"source_system": event["source_system"], "event_id": event["event_id"]}
    digest = event_hash(event)
    previous = db.eventos_integracao.find_one(key)
    now = utcnow()
    if previous and previous.get("payload_hash") == digest:
        db.recebimentos_integracao.insert_one({**key, "status": "DUPLICADO", "received_at": now})
        return {"event_id": event["event_id"], "status": "DUPLICADO", "duplicate": True}

    version = int(previous.get("version", 0)) + 1 if previous else 1
    history = list(previous.get("history", [])) if previous else []
    if previous:
        history.append({"version": previous["version"], "payload_hash": previous.get("payload_hash"), "updated_at": previous.get("updated_at")})
    event_document = {
        **event, **key, "event_type": event_type, "occurred_at": occurred_at,
        "payload_hash": digest, "version": version, "history": history,
        "received_at": previous.get("received_at", now) if previous else now,
        "updated_at": now, "processing_status": "RECEBIDO",
    }
    db.eventos_integracao.replace_one(key, event_document, upsert=True)

    child_id = event.get("child_external_id")
    projection_status = "SEM_PROJECAO"
    if child_id:
        child_key = {"source_system": event["source_system"], "external_id": child_id}
        child = db.criancas.find_one(child_key) or {}
        normalized = normalized_projection(event.get("data", {}))
        projection_key = event_type
        if event_type == "triagem":
            screening = canonical_screening(normalized.get("tipo_triagem"))
            projection_key = f"triagem:{screening or event['entity_external_id']}"
        current = (child.get("projections") or {}).get(projection_key)
        current_time = as_utc(current["occurred_at"]) if current else occurred_at
        if current is None or occurred_at >= current_time:
            projection = {
                "event_id": event["event_id"], "entity_external_id": event["entity_external_id"],
                "event_type": event_type, "occurred_at": occurred_at,
                "unit_external_id": event.get("unit_external_id"),
                "data": {**(current or {}).get("data", {}), **normalized},
            }
            update = {
                "source_system": event["source_system"], "external_id": child_id,
                "unit_external_id": event.get("unit_external_id") or child.get("unit_external_id"),
                "updated_at": now, f"projections.{projection_key}": projection,
            }
            if event_type == "nascimento":
                update["birth_event_received"] = True
            db.criancas.update_one(child_key, {"$setOnInsert": {"created_at": now}, "$set": update}, upsert=True)
            projection_status = "PROJETADO"
        else:
            projection_status = "FORA_DE_ORDEM"

    if str(event.get("entity_type", "")).casefold() in ("gestacao", "pregnancy"):
        pregnancy_key = {"source_system": event["source_system"], "external_id": event["entity_external_id"]}
        db.gestacoes.update_one(pregnancy_key, {"$set": {
            **pregnancy_key, "child_external_id": child_id,
            "occurred_at": occurred_at, "data": normalized_projection(event.get("data", {})),
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}}, upsert=True)

    db.eventos_integracao.update_one(key, {"$set": {"processing_status": projection_status}})
    receipt_status = "CORRIGIDO" if previous else "PROCESSADO"
    db.recebimentos_integracao.insert_one({**key, "status": receipt_status, "projection_status": projection_status, "received_at": now})
    if child_id:
        refresh_child_monitorings(db, event["source_system"], child_id, actor="integracao")
        db.resumos_alta.update_many({
            "source_system": event["source_system"], "child_external_id": child_id,
            "status": {"$in": ["RASCUNHO", "PENDENTE_VALIDACAO", "VALIDADO"]},
        }, {"$set": {"status": "ATUALIZADO", "source_update_received_at": now, "updated_at": now}})
    return {"event_id": event["event_id"], "status": receipt_status, "projection_status": projection_status, "version": version}


def children_list(db, unit=None, query=None):
    filters = {}
    if unit:
        filters["unit_external_id"] = unit
    if query:
        filters["external_id"] = {"$regex": query, "$options": "i"}
    return [json_safe(child) for child in db.criancas.find(filters).sort("updated_at", -1).limit(1000)]


def child_detail(db, source_system, external_id):
    child = db.criancas.find_one({"source_system": source_system, "external_id": external_id})
    if not child:
        return None
    events = list(db.eventos_integracao.find({"source_system": source_system, "child_external_id": external_id}).sort("occurred_at", -1))
    monitors = list(db.monitoramentos.find({"source_system": source_system, "child_external_id": external_id}).sort("updated_at", -1))
    return {"child": json_safe(child), "events": json_safe(events), "monitorings": json_safe(monitors)}


def dashboard(db, unit=None):
    children = list(db.criancas.find({"unit_external_id": unit} if unit else {}))
    events = list(db.eventos_integracao.find({"unit_external_id": unit} if unit else {}))
    monitors = list(db.monitoramentos.find({"unit_external_id": unit} if unit else {}))
    open_monitors = [item for item in monitors if item.get("status") not in ("RESOLVIDO", "DESCARTADO")]
    today = utcnow().date()
    newborns = 0
    complete = 0
    for child in children:
        birth = child.get("projections", {}).get("nascimento", {}).get("data", {})
        try:
            age = (today - datetime.fromisoformat(str(birth.get("data_nascimento"))[:10]).date()).days
            newborns += int(0 <= age <= 28)
        except (TypeError, ValueError):
            pass
        complete += sum(bool(value) for value in (
            child.get("unit_external_id"), birth.get("data_nascimento"), birth.get("sexo"),
            birth.get("peso_nascimento"), child.get("birth_event_received"),
        ))
    return {
        "metrics": {
            "children_received": len(children), "newborns_0_28_days": newborns,
            "open_monitorings": len(open_monitors),
            "high_or_critical": sum(item.get("priority") in ("ALTA", "CRITICA") for item in open_monitors),
            "discharges": sum("alta_maternidade" in child.get("projections", {}) for child in children),
            "triage_missing": sum(item.get("data_state") == "SEM_INFORMACAO" for item in open_monitors),
            "appointments_received": sum(item.get("event_type") == "agendamento" for item in events),
            "completeness_percent": round(100 * complete / (5 * len(children))) if children else 0,
        },
        "events_by_type": _count_by(events, "event_type"),
        "monitorings_by_unit": _count_by(open_monitors, "unit_external_id"),
        "monitorings_by_status": _count_by(monitors, "status"),
        "monitorings_by_priority": _count_by(monitors, "priority"),
    }


def _count_by(items, field):
    counts = {}
    for item in items:
        key = item.get(field) or "Sem informação"
        counts[key] = counts.get(key, 0) + 1
    return [{"name": key, "count": count} for key, count in sorted(counts.items())]


def update_monitoring(db, monitor_id, payload, actor):
    if payload.status in ("RESOLVIDO", "DESCARTADO") and not (payload.resolution_reason or "").strip():
        raise ValueError("Informe a justificativa para resolver ou descartar a ocorrência.")
    try:
        object_id = ObjectId(monitor_id)
    except Exception as exc:
        raise ValueError("Identificador de ocorrência inválido.") from exc
    item = db.monitoramentos.find_one({"_id": object_id})
    if not item:
        return None
    now = utcnow()
    change = {"status": payload.status, "updated_at": now}
    if payload.note is not None:
        change["note"] = payload.note
    if payload.responsible is not None:
        change["responsible"] = payload.responsible
    if payload.status in ("RESOLVIDO", "DESCARTADO"):
        change.update({"resolution_reason": payload.resolution_reason, "resolved_at": now})
    transition = {"actor": actor, "from": item.get("status"), "to": payload.status,
                  "note": payload.note, "at": now}
    db.monitoramentos.update_one({"_id": object_id}, {"$set": change, "$push": {"history": transition}})
    audit(db, actor, "monitoramento_atualizado", "monitoramento", monitor_id, transition)
    return json_safe(db.monitoramentos.find_one({"_id": object_id}))


def create_discharge_summary(db, source_system, child_external_id, actor):
    child = db.criancas.find_one({"source_system": source_system, "external_id": child_external_id})
    if not child:
        return None
    events = list(db.eventos_integracao.find({
        "source_system": source_system, "child_external_id": child_external_id,
    }).sort("occurred_at", 1))
    sections = {}
    repeated = {"triagem", "consulta", "vacinacao", "agendamento"}
    source_ids = []
    for event in events:
        kind = event.get("event_type")
        normalized = normalized_projection(event.get("data", {}))
        source_ids.append(event.get("event_id"))
        if kind in repeated:
            sections.setdefault(kind, []).append({"event_id": event.get("event_id"), "occurred_at": event.get("occurred_at"), **normalized})
        else:
            sections[kind] = {**sections.get(kind, {}), **normalized}
    birth = sections.get("nascimento", {})
    discharge = sections.get("alta_maternidade", {})
    sections["identificacao"] = {
        "nome": birth.get("nome"), "data_nascimento": birth.get("data_nascimento"),
        "sexo": birth.get("sexo"), "unidade_referencia": child.get("unit_external_id"),
    }
    missing = []
    for key, label, values in (
        ("nome", "identificação da criança", birth),
        ("data_nascimento", "data de nascimento", birth),
        ("sexo", "sexo registrado", birth),
        ("unidade_hospitalar", "unidade hospitalar", {**birth, **discharge}),
        ("data_alta", "data da alta", discharge),
    ):
        if not values.get(key):
            missing.append(label)
    if not child.get("unit_external_id"):
        missing.append("unidade de referência")
    summary_id = str(uuid4())
    summary = {
        "document_id": summary_id, "source_system": source_system,
        "child_external_id": child_external_id, "unit_external_id": child.get("unit_external_id"),
        "status": "RASCUNHO", "generated_at": utcnow(), "generated_by": actor,
        "source_event_ids": source_ids, "sections": sections, "missing_fields": sorted(set(missing)),
    }
    db.resumos_alta.insert_one(summary)
    audit(db, actor, "resumo_gerado", "resumo_alta", summary_id, {"child_external_id": child_external_id})
    return json_safe(summary)


def list_summaries(db, source_system=None, child_external_id=None):
    query = {}
    if source_system:
        query["source_system"] = source_system
    if child_external_id:
        query["child_external_id"] = child_external_id
    return [json_safe(item) for item in db.resumos_alta.find(query).sort("generated_at", -1).limit(500)]


def configure_rule(db, rule_id, payload, actor):
    rule = db.regras_monitoramento.find_one({"rule_id": rule_id})
    if not rule:
        return None
    threshold = payload.threshold_days
    if rule_id in TEMPORAL_RULES and payload.enabled and threshold is None:
        raise ValueError("Defina e valide o intervalo local antes de ativar esta regra.")
    now = utcnow()
    db.regras_monitoramento.update_one({"rule_id": rule_id}, {"$set": {
        "enabled": payload.enabled,
        "priority": payload.priority,
        "threshold_days": threshold if rule_id in TEMPORAL_RULES else None,
        "updated_at": now,
        "updated_by": actor,
    }})
    audit(db, actor, "regra_monitoramento_atualizada", "regra_monitoramento", rule_id, {
        "enabled": payload.enabled, "priority": payload.priority, "threshold_days": threshold,
    })
    return json_safe(db.regras_monitoramento.find_one({"rule_id": rule_id}))
