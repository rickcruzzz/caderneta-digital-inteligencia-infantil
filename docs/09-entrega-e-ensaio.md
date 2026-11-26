# Guia de apresentação e ensaio — MongoDB

## Mensagem pronta para a enquete

```text
📚 A3 | Qual parte você prefere apresentar?

🎯 1. Introdução e objetivo
☁️ 2. Arquitetura e MongoDB Atlas
🧩 3. Coleções e modelagem documental
🔐 4. API, integração e segurança
💻 5. Demonstração do sistema
✅ 6. Testes e conclusão
```

## Resumo para enviar ao grupo

📚 **A3 — CADERNETA DIGITAL DA CRIANÇA | VERSÃO MONGODB**

Cada integrante escolhe uma parte na enquete. A apresentação deve mostrar que esta versão é uma camada complementar de inteligência e acompanhamento. Os registros oficiais continuam no sistema de origem.

🎯 **1. Introdução:** explicar o problema da caderneta em papel e como a aplicação centraliza informações recebidas para apoiar o acompanhamento infantil.

☁️ **2. Arquitetura:** explicar Next.js, FastAPI, MongoDB Atlas e o fluxo de eventos entre o sistema de origem e a Caderneta Digital.

🧩 **3. Modelagem documental:** mostrar as coleções, projeções, histórico de eventos, índices e relacionamentos por identificadores.

🔐 **4. API e segurança:** explicar integração JSON, idempotência, autenticação, perfis de acesso, auditoria e proteção das credenciais.

💻 **5. Demonstração:** mostrar login, painel, crianças, monitoramentos, resumos de alta, integração e auditoria.

✅ **6. Testes e conclusão:** apresentar os testes automatizados, build, limites do protótipo e resultado final.

---

## 1. Introdução e objetivo

### Objetivo da fala

Apresentar o problema, a proposta e o limite do sistema em linguagem simples.

### Fala sugerida

> A caderneta em papel pode ficar desatualizada, ser perdida e dificultar a continuidade do acompanhamento. A Caderneta Digital reúne eventos enviados pelo sistema oficial e transforma esses dados em painéis, monitoramentos e resumos. Ela não substitui prontuário, diagnóstico ou avaliação profissional. O objetivo é organizar informação e apoiar a equipe de saúde.

### Mostrar

- Tela de login e identidade visual da Caderneta Digital.
- Objetivo descrito no [README](../README.md).
- Aviso de que a demonstração usa somente dados sintéticos.

### Evitar

- Dizer que o sistema faz diagnóstico.
- Dizer que o MongoDB substitui o banco oficial.
- Usar nomes ou informações reais de pacientes.

### Transição

> Agora veremos como a interface, a API e o MongoDB trabalham juntas.

---

## 2. Arquitetura e MongoDB Atlas

### Objetivo da fala

Explicar o fluxo técnico sem misturar a arquitetura documental com a versão SQL Server anterior.

### Fala sugerida

> A interface foi construída com Next.js. Ela chama uma API FastAPI no mesmo domínio. A API valida autenticação e regras, processa os eventos e acessa o MongoDB Atlas. O navegador nunca recebe a URI do banco. A base exclusiva da aplicação é `caderneta_digital`; outros bancos, como `sample_mflix`, permanecem intactos.

### Fluxo para mostrar

```text
Sistema de origem
      │ HTTPS + JSON + X-API-Key
      ▼
FastAPI /api/*
      │ valida, normaliza e projeta
      ▼
MongoDB Atlas / caderneta_digital
      ▲
      │ sessão HttpOnly
Next.js / interface profissional
```

### Pontos técnicos

- Next.js entrega a interface responsiva.
- FastAPI concentra acesso, integração, regras e relatórios.
- PyMongo mantém a conexão com Atlas.
- A API cria índices necessários sem apagar coleções.
- `MONGO_DATABASE=caderneta_digital` seleciona a base da aplicação.
- `MONGO_URI` é o nome oficial de deploy; `MONGODB_URI` também funciona no ambiente local.

### Transição

> Com a arquitetura definida, podemos entender como os documentos são organizados.

---

## 3. Coleções e modelagem documental

### Objetivo da fala

Explicar documentos, coleções e vínculos sem usar conceitos incorretos de chave estrangeira.

### Coleções principais

| Coleção | Responsabilidade |
| --- | --- |
| `eventos_integracao` | Evento consolidado e sua versão atual |
| `recebimentos_integracao` | Histórico de recebimentos, duplicidades e correções |
| `criancas` | Projeção atual da criança, organizada por tipo de evento |
| `monitoramentos` | Pendências e acompanhamentos operacionais |
| `resumos_alta` | Documentos de alta gerados e validados |
| `auditoria` | Registro de ações relevantes dos usuários |
| `usuarios` | Contas, perfis e senhas armazenadas como hash |
| `regras_monitoramento` | Configuração das regras e prazos aprovados |

### Relacionamentos

- `source_system` identifica o sistema de origem.
- `event_id` identifica um evento e impede duplicação.
- `child_external_id` liga eventos, criança, monitoramentos e resumos.
- `unit_external_id` permite filtros por unidade.
- Índices únicos preservam idempotência e consistência.
- Eventos antigos permanecem no histórico e não sobrescrevem projeções mais recentes.

### Fala sugerida

> No MongoDB trabalhamos com coleções de documentos BSON. Em vez de repetir consultas complexas, a aplicação mantém uma projeção atual da criança e preserva o histórico dos eventos recebidos. Os vínculos são feitos por identificadores estáveis e protegidos por índices. Um reenvio igual é tratado como duplicado; uma correção cria histórico sem apagar notas da equipe.

### Transição

> Esses documentos entram por uma API controlada, com validação e segurança separadas para integração e usuários.

---

## 4. API, integração e segurança

### Objetivo da fala

Mostrar como os dados chegam, como são validados e quem pode acessá-los.

### Rotas para citar

- `GET /api/health`: verifica API e conexão com MongoDB.
- `POST /api/v1/integracao/registros`: recebe um evento.
- `POST /api/v1/integracao/registros/lote`: recebe até 500 eventos.
- `GET /api/v1/dashboard`: retorna indicadores para usuário autenticado.
- `GET /api/v1/criancas`: lista projeções recebidas.
- `PATCH /api/v1/monitoramentos/{id}`: atualiza acompanhamento.
- `POST /api/v1/resumos-alta`: gera resumo digital.

### Controles implementados

- Integração protegida por `X-API-Key`.
- Interface protegida por sessão assinada em cookie HttpOnly.
- Perfis `ADMIN`, `PROFISSIONAL` e `LEITURA`.
- Senhas armazenadas com salt e hash, nunca em texto puro no banco.
- Payloads validados por modelos Pydantic.
- Auditoria de ações administrativas e profissionais.
- Credenciais somente em variáveis de ambiente ignoradas pelo Git.

### Fala sugerida

> A chave usada pelo sistema de origem não é a mesma credencial de login. Cada evento segue um contrato JSON e passa por validação. A API rejeita chave inválida, esquema incorreto e ações sem permissão. A sessão do usuário fica em cookie HttpOnly, e os segredos não aparecem no frontend nem no repositório.

Leia também o [contrato de integração](../CONTRATO_INTEGRACAO.md).

### Transição

> Agora vamos acompanhar esse fluxo funcionando pela interface.

---

## 5. Demonstração do sistema

### Ordem recomendada

1. Abrir a página de login e entrar com uma conta de demonstração.
2. Mostrar a **Visão geral** e explicar os indicadores.
3. Abrir **Inteligência de dados** e aplicar filtros de unidade e evento.
4. Abrir **Crianças** e consultar a linha do tempo de uma criança sintética.
5. Abrir a **Central de monitoramento** e atualizar uma pendência.
6. Gerar um **Resumo digital de alta** e mostrar o PDF.
7. Mostrar **Integração** e o formato do evento JSON.
8. Entrar em **Auditoria** com perfil administrador.

### Fala sugerida

> O painel é calculado com os documentos recebidos. Ausência de evento significa “sem informação recebida”; não significa que um procedimento não foi realizado. As prioridades são operacionais. Uma regra temporal só pode ser ativada depois de receber um prazo aprovado.

### Plano de contingência

- Antes da apresentação, validar `GET /api/health` no ambiente autorizado pelo Atlas.
- Executar o seed apenas com `--confirmar-dados-sinteticos`.
- Não alterar a lista de acesso do Atlas durante a apresentação.
- Manter o notebook Colab como demonstração alternativa efêmera.
- Nunca abrir o arquivo de credenciais na tela compartilhada.

---

## 6. Testes e conclusão

### Evidências técnicas

- Testes FastAPI e MongoDB simulado cobrem autenticação, idempotência, aliases do banco anterior, triagens, filtros, regras, usuários, resumos e seed.
- O seed é repetível e testa que `sample_mflix` permanece vazio e intocado.
- `npm run typecheck` valida o TypeScript.
- `npm run build` valida a compilação de produção do Next.js.
- A conexão real deve ser confirmada por `/api/health` a partir de IP autorizado no Atlas.

### Fala sugerida

> Os testes verificam os fluxos críticos sem usar pacientes reais. Confirmamos que eventos repetidos não duplicam dados, correções preservam histórico, usuários sem permissão são bloqueados e o seed não escreve em outros bancos. A aplicação compila para produção e está preparada para usar a base exclusiva `caderneta_digital`.

### Conclusão sugerida

> O projeto demonstra uma arquitetura moderna para complementar a Caderneta Digital da Criança. Next.js oferece a interface, FastAPI protege e processa a integração, e MongoDB mantém projeções e histórico flexíveis. O resultado apoia acompanhamento e qualidade dos dados, preservando o sistema oficial, a segurança e os limites de uso clínico.

---

## Checklist antes da apresentação

- [ ] Cada integrante escolheu uma das seis partes.
- [ ] Todos ensaiaram a própria fala e a transição.
- [ ] Somente dados sintéticos estão carregados.
- [ ] `/api/health` responde com `database: caderneta_digital`.
- [ ] Login, painel, crianças, monitoramentos, resumo e auditoria foram testados.
- [ ] Testes Python, typecheck e build foram executados.
- [ ] Nenhuma credencial aparece em slide, terminal, navegador ou GitHub.
- [ ] Existe um plano alternativo caso a internet ou o Atlas falhe.
