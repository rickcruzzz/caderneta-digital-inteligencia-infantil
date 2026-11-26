# Caderneta Digital

Aplicação complementar ao sistema relacional existente. A origem mantém os registros oficiais e envia eventos JSON por HTTP; a Caderneta Digital mantém projeções mínimas no MongoDB para inteligência, monitoramento e resumo de alta. Ela não acessa nem substitui o SQL Server.

## Apresentação A3

O [guia de apresentação e ensaio](docs/09-entrega-e-ensaio.md) divide a versão MongoDB em seis partes para a enquete do grupo, com falas sugeridas, demonstração e checklist final.

## Deploy Vercel

O deploy usa Next.js para a interface e FastAPI como funções Python em `/api/*`, no mesmo domínio. MongoDB Atlas é a persistência única da aplicação, na base `caderneta_digital`. Configure no projeto Vercel estas variáveis em **Production** e **Preview**:

```text
MONGO_URI=<URI do Atlas>
MONGO_DATABASE=caderneta_digital
API_INTEGRATION_KEY=<chave aleatória com pelo menos 24 caracteres>
SESSION_SECRET=<segredo aleatório com pelo menos 32 caracteres>
APP_ADMIN_USERNAME=<usuário inicial>
APP_ADMIN_PASSWORD=<senha inicial com pelo menos 12 caracteres>
CRON_SECRET=<segredo aleatório do cron>
```

Configure os mesmos valores a partir de um ambiente local seguro com `vercel env add`; nunca crie `.env` versionado nem cole segredos no notebook. O ambiente local também aceita `MONGODB_URI` como alias de `MONGO_URI`. `sample_mflix` e o SQL Server não são alterados. O Mongo cria as coleções ao receber dados e a API inicializa os índices.

## Executar localmente

Requer Node.js 22+, Python 3.11+ e MongoDB Atlas ou MongoDB local.

```bash
npm ci
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm run dev
```

`npm run build` compila a interface Next.js. Testes da API: `python -m pytest -q tests`. A rota de saúde é `/api/health`; a documentação OpenAPI fica disponível em `/api/docs`.

## Dados de demonstração

Com `MONGO_URI` e `SESSION_SECRET` no ambiente, a criação da base exclusiva e o seed de dados **fictícios** são explícitos:

```bash
MONGO_DATABASE=caderneta_digital python scripts/seed_demo.py --confirmar-dados-sinteticos
```

O seed é repetível, preserva coleções já existentes e não escreve em `sample_mflix`. Ele usa somente IDs e informações sintéticas. Para dados oficiais, a origem deve enviar registros pela API; não há importação direta do SQL Server.

## Integração

- `GET /api/health`
- `POST /api/v1/integracao/registros`
- `POST /api/v1/integracao/registros/lote`
- `GET /api/v1/integracao/registros/{event_id}`

Integração exige `X-API-Key`; login da interface usa sessão HttpOnly separada. Reenvios são idempotentes, correções preservam notas e eventos antigos não substituem projeções mais recentes. Consulte [CONTRATO_INTEGRACAO.md](CONTRATO_INTEGRACAO.md). O adaptador reconhece colunas reais da Caderneta, incluindo `peso_g`, `comprimento_cm`, `perimetro_cefalico_cm`, `ig_semanas`, `data_alta`, `realizada` e os códigos de triagem `BIOLOGICA`, `AUDITIVA`, `REFLEXO_VERMELHO`, `OXIMETRIA`.

## Notebook Colab

`Caderneta_Digital_Colab.ipynb` mantém uma demonstração Streamlit + FastAPI com túnel Cloudflare. Esse modo é efêmero e destinado a dados sintéticos; não é a hospedagem de produção Vercel.

## Segurança e limites

Ausência de evento é **sem informação recebida**, nunca confirmação de não realização. Regras com prazo começam desligadas e exigem intervalos aprovados por profissionais. Prioridades são operacionais, não diagnósticos. Não use dados reais em demonstrações/Colab; valide LGPD, retenção, controle de acesso e protocolos antes de qualquer uso clínico.
