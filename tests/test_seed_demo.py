from datetime import datetime, timezone

import mongomock

from scripts.seed_demo import seed_demo


def test_seed_is_synthetic_idempotent_and_limited_to_caderneta_database():
    client = mongomock.MongoClient()
    database = client["caderneta_digital"]
    fixed_now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)

    first = seed_demo(database, fixed_now)
    second = seed_demo(database, fixed_now)

    assert database.name == "caderneta_digital"
    assert len(first) == len(second) == 8
    assert database.eventos_integracao.count_documents({}) == 8
    assert database.criancas.count_documents({}) == 2
    assert all(result["status"] == "DUPLICADO" for result in second)
    assert client["sample_mflix"].list_collection_names() == []
    assert database.eventos_integracao.count_documents({"source_system": "demo_caderneta_digital"}) == 8
