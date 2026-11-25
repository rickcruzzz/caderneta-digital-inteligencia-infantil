import os
from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    uri = os.environ.get("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI não configurada.")
    return MongoClient(
        uri,
        appname="CadernetaDigitalVercel",
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
        maxPoolSize=10,
    )


def get_db():
    return get_client()[os.environ.get("MONGO_DATABASE", "caderneta_digital")]


def ensure_indexes(db=None) -> None:
    if db is None:
        db = get_db()
    db.eventos_integracao.create_index(
        [("source_system", ASCENDING), ("event_id", ASCENDING)], unique=True
    )
    db.eventos_integracao.create_index(
        [("child_external_id", ASCENDING), ("occurred_at", DESCENDING)]
    )
    db.recebimentos_integracao.create_index(
        [("event_id", ASCENDING), ("received_at", DESCENDING)]
    )
    db.criancas.create_index(
        [("source_system", ASCENDING), ("external_id", ASCENDING)], unique=True
    )
    db.criancas.create_index(
        [("unit_external_id", ASCENDING), ("updated_at", DESCENDING)]
    )
    db.monitoramentos.create_index(
        [
            ("source_system", ASCENDING),
            ("child_external_id", ASCENDING),
            ("rule_id", ASCENDING),
            ("occurrence_key", ASCENDING),
        ],
        unique=True,
    )
    db.monitoramentos.create_index(
        [("status", ASCENDING), ("priority", ASCENDING), ("updated_at", DESCENDING)]
    )
    db.resumos_alta.create_index([("document_id", ASCENDING)], unique=True)
    db.resumos_alta.create_index(
        [
            ("source_system", ASCENDING),
            ("child_external_id", ASCENDING),
            ("generated_at", DESCENDING),
        ]
    )
    db.auditoria.create_index(
        [("entity_id", ASCENDING), ("created_at", DESCENDING)]
    )
    db.usuarios.create_index([("username", ASCENDING)], unique=True)
    db.regras_monitoramento.create_index([("rule_id", ASCENDING)], unique=True)


def close_client() -> None:
    client = get_client.cache_info()
    if client.currsize:
        get_client().close()
        get_client.cache_clear()
