# Plataforma de Inteligência da Saúde Infantil

Aplicação complementar ao sistema relacional existente. O sistema de origem continua sendo a fonte oficial dos registros e envia eventos JSON por HTTP; esta plataforma mantém projeções mínimas no MongoDB e disponibiliza indicadores operacionais, monitoramento e resumos digitais de alta. Não acessa nem substitui o SQL Server.

## Executar no Google Colab

Abra `Plataforma_Inteligencia_Saude_Infantil_Colab.ipynb` no Colab e execute as células em ordem. A célula de credenciais solicita separadamente a URI do MongoDB Atlas, a chave da API de integração e a senha inicial do administrador por entrada sem eco. Nenhuma credencial deve ser colocada no notebook ou nos arquivos gerados.

A célula de conexão verifica o MongoDB e prepara índices no banco `inteligencia_saude_infantil`. API e Streamlit executam no runtime. A célula de túneis Cloudflare exibe URLs públicas efêmeras para demonstração; elas mudam ao reiniciar e não são adequadas a dados reais. Use apenas eventos sintéticos no Colab.

## Executar localmente

Requer Python 3.11 ou superior e uma instância MongoDB (por exemplo, Atlas). Crie um ambiente virtual e instale as dependências:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure variáveis no ambiente, sem gravá-las no Git:

```text
MONGO_URI=<URI MongoDB Atlas>
MONGO_DATABASE=inteligencia_saude_infantil
API_INTEGRATION_KEY=<chave aleatória independente>
APP_ADMIN_USERNAME=<usuário inicial>
APP_ADMIN_PASSWORD=<senha inicial com pelo menos 12 caracteres>
```

Gere os módulos com as células 4 a 9 do notebook (ou execute o notebook completo), depois inicie em terminais separados:

```bash
uvicorn api:app --host 127.0.0.1 --port 8000
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Documentação OpenAPI: `http://127.0.0.1:8000/docs`. Interface: `http://127.0.0.1:8501`.

## Integração

Endpoints:

- `GET /health`
- `POST /api/v1/integracao/registros`
- `POST /api/v1/integracao/registros/lote`
- `GET /api/v1/integracao/registros/{event_id}`

Endpoints de integração exigem `X-API-Key`. Eventos repetidos com o mesmo `source_system` e `event_id` são idempotentes; reenvio igual registra duplicidade, conteúdo corrigido atualiza a versão e preserva observações de profissionais. Eventos antigos ficam no histórico e não substituem projeções mais recentes.

Exemplo de evento (campos ilustrativos, não pressupõem colunas do banco de origem):

```json
{
  "event_id": "evt-001",
  "source_system": "sistema_relacional",
  "schema_version": "1.0",
  "event_type": "alta_maternidade",
  "entity_type": "crianca",
  "entity_external_id": "CRI-001",
  "child_external_id": "CRI-001",
  "unit_external_id": "UBS-001",
  "occurred_at": "2026-11-20T14:30:00-03:00",
  "data": {
    "data_alta": "2026-11-20",
    "unidade_hospitalar": "Maternidade Exemplo"
  }
}
```

Tipos aceitos: `gestacao`, `nascimento`, `internacao_neonatal`, `alta_maternidade`, `triagem`, `consulta`, `vacinacao` e `agendamento`. Identificadores de evento, sistema, entidade e data/hora com fuso são obrigatórios. `child_external_id`, `unit_external_id` e campos em `data` podem variar segundo o evento. O adaptador em `services.py` mapeia aliases comuns; ajuste `FIELD_ALIASES` conforme o contrato real da origem. `data` mantém somente a projeção necessária e o evento de origem recebe controle de versão.

## Dados e regras

Coleções: `criancas`, `gestacoes`, `eventos_integracao`, `recebimentos_integracao`, `monitoramentos`, `resumos_alta`, `auditoria`, `usuarios` e `regras_monitoramento`.

A ausência de evento de triagem é exibida como **sem informação recebida**, nunca como confirmação de não realização. Regras de prazo após alta e desatualização começam desativadas até configuração e validação por profissionais do serviço. Prioridade é classificação operacional, não diagnóstico nem protocolo clínico. O resumo só exibe conteúdo recebido e destaca campos ausentes.

## Testes e limites

A última célula executa testes com `mongomock`; ela não grava no Atlas. Inclui autenticação, idempotência, correções, eventos fora de ordem, preservação de notas, pendências sem informação e geração de PDF. Não usa dados reais.

Este projeto é um protótipo de integração e demonstração, não um sistema clínico de produção. Antes de qualquer uso real, valide contrato, perfis, retenção, criptografia, controles de acesso, protocolos, requisitos legais e LGPD com as equipes responsáveis. O Colab e túneis públicos efêmeros não devem receber dados pessoais ou clínicos reais.
