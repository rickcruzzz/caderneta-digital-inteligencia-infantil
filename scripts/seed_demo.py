import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from api.database import ensure_indexes, get_db
from api.services import process_event


def event(event_id, event_type, entity_id, child_id, occurred_at, data, unit="UBS-DEMO-01"):
    return {
        "event_id": event_id,
        "source_system": "demo_caderneta_digital",
        "schema_version": "1.0",
        "event_type": event_type,
        "entity_type": "crianca",
        "entity_external_id": entity_id,
        "child_external_id": child_id,
        "unit_external_id": unit,
        "occurred_at": occurred_at.isoformat(),
        "data": data,
    }


def synthetic_events(now=None):
    now = now or datetime.now(timezone.utc)
    birth_one = now - timedelta(days=8)
    birth_two = now - timedelta(days=4)
    return [
        event(
            "demo-rn-001-nascimento", "nascimento", "DEMO-RN-001", "DEMO-RN-001",
            birth_one,
            {"nome": "Recém-nascido Sintético 001", "data_nascimento": birth_one.date().isoformat(),
             "sexo": "F", "peso_g": 3020, "comprimento_cm": 49, "perimetro_cefalico_cm": 34,
             "ig_semanas": 39, "ig_dias": 1, "apgar_1min": 8, "apgar_5min": 9,
             "tipo_parto": "VAGINAL"},
        ),
        event(
            "demo-rn-001-alta", "alta_maternidade", "DEMO-RN-001", "DEMO-RN-001",
            now - timedelta(days=6),
            {"data_alta": (now - timedelta(days=6)).date().isoformat(), "peso_alta_g": 2940,
             "aleitamento": "LME", "resumo_alta": "Registro sintético para demonstração.",
             "unidade_hospitalar": "Maternidade Sintética", "unidade_referencia": "UBS-DEMO-01"},
        ),
        event(
            "demo-rn-001-triagem-biologica", "triagem", "DEMO-RN-001", "DEMO-RN-001",
            now - timedelta(days=7),
            {"codigo": "BIOLOGICA", "realizada": True,
             "data_realizacao": (now - timedelta(days=7)).date().isoformat(), "resultado": "NR"},
        ),
        event(
            "demo-rn-001-triagem-auditiva", "triagem", "DEMO-RN-001", "DEMO-RN-001",
            now - timedelta(days=7),
            {"codigo": "AUDITIVA", "realizada": False, "data_realizacao": None,
             "conduta": "Sem dado sintético de realização; verificar na origem."},
        ),
        event(
            "demo-rn-001-consulta", "consulta", "DEMO-RN-001", "DEMO-RN-001",
            now - timedelta(days=2),
            {"data_consulta": (now - timedelta(days=2)).isoformat(), "peso_g": 3150,
             "comprimento_cm": 50, "perimetro_cefalico_cm": 34.5,
             "tipo_atendimento": "PRIMEIRA_SEMANA", "aleitamento": "LME"},
        ),
        event(
            "demo-rn-002-nascimento", "nascimento", "DEMO-RN-002", "DEMO-RN-002",
            birth_two,
            {"nome": "Recém-nascido Sintético 002", "data_nascimento": birth_two.date().isoformat(),
             "sexo": "M", "peso_g": 2780, "comprimento_cm": 48, "perimetro_cefalico_cm": 33,
             "ig_semanas": 37, "ig_dias": 4, "apgar_1min": 8, "apgar_5min": 9},
            unit="UBS-DEMO-02",
        ),
        event(
            "demo-rn-002-alta", "alta_maternidade", "DEMO-RN-002", "DEMO-RN-002",
            now - timedelta(days=3),
            {"data_alta": (now - timedelta(days=3)).date().isoformat(), "peso_alta_g": 2700,
             "aleitamento": "LME", "resumo_alta": "Registro sintético para demonstração.",
             "unidade_hospitalar": "Maternidade Sintética", "unidade_referencia": "UBS-DEMO-02"},
            unit="UBS-DEMO-02",
        ),
        event(
            "demo-rn-002-agendamento", "agendamento", "DEMO-RN-002", "DEMO-RN-002",
            now + timedelta(days=1),
            {"data_hora": (now + timedelta(days=1)).isoformat(), "tipo_atendimento": "PUERICULTURA",
             "status": "AGENDADO", "observacao": "Evento sintético."},
            unit="UBS-DEMO-02",
        ),
    ]


def seed_demo(db, now=None):
    ensure_indexes(db)
    return [process_event(db, item) for item in synthetic_events(now)]


def main():
    parser = argparse.ArgumentParser(description="Criar dados sintéticos sem apagar coleções.")
    parser.add_argument("--confirmar-dados-sinteticos", action="store_true")
    args = parser.parse_args()
    if not args.confirmar_dados_sinteticos:
        parser.error("Confirme explicitamente com --confirmar-dados-sinteticos.")
    os.environ["MONGO_DATABASE"] = "caderneta_digital"
    db = get_db()
    db.command("ping")
    results = seed_demo(db)
    print(f"Base: {db.name}")
    print(f"Eventos sintéticos submetidos: {len(results)}")
    print("Execuções repetidas usam os mesmos IDs de evento e não duplicam dados.")


if __name__ == "__main__":
    main()
