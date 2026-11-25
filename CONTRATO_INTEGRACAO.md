# Contrato de Integração v1.0

Envie eventos por HTTPS com o cabeçalho `X-API-Key`. Campos obrigatórios: `event_id`, `source_system`, `schema_version` (`1.0`), `event_type`, `entity_type`, `entity_external_id`, `occurred_at` ISO-8601 com fuso e `data` objeto. `child_external_id` e `unit_external_id` são recomendados para projeção da criança e filtros; são opcionais quando o evento não possui esse vínculo.

Tipos aceitos: `gestacao`, `nascimento`, `internacao_neonatal`, `alta_maternidade`, `triagem`, `consulta`, `vacinacao` e `agendamento`. O adaptador aceita aliases em `services.py` (`FIELD_ALIASES`); adapte-os ao contrato real sem presumir nomes de colunas do banco relacional. Envie somente dados necessários à finalidade.

- `GET /health` verifica API e MongoDB.
- `POST /api/v1/integracao/registros` recebe um evento individual.
- `POST /api/v1/integracao/registros/lote` recebe `{ "events": [...] }`, máximo 500 eventos.
- `GET /api/v1/integracao/registros/{event_id}?source_system=...` consulta o histórico do evento.

Requisições de integração exigem `X-API-Key`. Um reenvio idêntico é idempotente. Mesmo identificador com conteúdo corrigido incrementa versão e mantém histórico; eventos anteriores não substituem projeções mais recentes. Respostas inválidas usam HTTP 422 e falha de chave usa HTTP 401. O payload individual está limitado a 256 KB.

Para triagens, aliases canônicos ficam em `monitoring.py`. Status reconhecidos: realizado, pendente e não realizado. Status desconhecidos permanecem como não mapeados; ausência de evento é `SEM_INFORMACAO`, não confirmação de não realização.
