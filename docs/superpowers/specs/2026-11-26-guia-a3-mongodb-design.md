# Guia A3 atualizado para MongoDB

## Intenção

Atualizar a entrega da Caderneta Digital para que o grupo apresente a versão atual baseada em Next.js, FastAPI e MongoDB Atlas. O material deve manter a linguagem curta, visual e dividida em seis partes do guia anterior.

## Objetivos

- Criar um roteiro de apresentação com seis partes equilibradas para a enquete do grupo.
- Explicar o modelo documental, coleções, eventos e relacionamento por identificadores sem chamar o MongoDB de banco relacional.
- Documentar demonstração, segurança, testes e limites clínicos da aplicação atual.
- Aceitar localmente a variável segura existente `MONGODB_URI`, mantendo `MONGO_URI` como nome oficial de deploy.
- Manter a base efetiva `caderneta_digital` e nunca alterar `sample_mflix` nem outros bancos.
- Atualizar o atalho local para abrir exatamente este projeto MongoDB no code-server da porta 8080.
- Validar testes, typecheck e build antes de publicar no GitHub.

## Fora do escopo

- Migrar ou apagar o projeto SQL Server anterior.
- Copiar dados reais de pacientes para demonstração.
- Liberar Atlas para `0.0.0.0/0` ou alterar controles de rede sem autorização específica.
- Versionar qualquer credencial do `.env.isolado`.

## Abordagens consideradas

1. **Repositório MongoDB independente — escolhida.** Preserva o histórico SQL e publica a aplicação atual sem misturar arquiteturas.
2. Substituir o conteúdo do repositório SQL. Rejeitada porque perderia o material acadêmico relacional e confundiria a apresentação.
3. Manter apenas instruções no chat. Rejeitada porque não produz documentação versionada, atalho corrigido nem evidência reproduzível.

## Desenho

O guia terá: introdução e objetivo; arquitetura MongoDB; modelagem documental; API e segurança; demonstração; testes e conclusão. Cada parte trará fala sugerida, pontos para mostrar e uma transição curta. O README apontará diretamente para o guia.

A configuração Mongo terá uma função única para resolver a URI. `MONGO_URI` terá precedência e `MONGODB_URI` funcionará como compatibilidade local. Mensagens de erro nunca incluirão credenciais. A base continuará vindo de `MONGO_DATABASE`, com padrão `caderneta_digital`.

O atalho instalado será renomeado para identificar a versão MongoDB e abrirá `/home/henrique/idevicerestore/ProjetoA3_Banco_de_dados/plataforma_saude_infantil` em `http://127.0.0.1:8080`.

## Aceite

- Guia completo e fiel ao sistema MongoDB atual.
- Teste prova a precedência e o fallback das variáveis de URI.
- Suite Python, typecheck e build passam.
- Nenhum segredo entra no Git.
- Repositório remoto recebe os commits e o link final é informado.

