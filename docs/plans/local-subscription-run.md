# Execução local com assinatura do Claude Code

Status em 2026-11-07: **primeiro run verificado**. O ArcReel roda fora do Docker no Mac (M1 Pro) e o Agent embutido responde usando o login de assinatura do Claude Code, sem nenhuma chave de API Anthropic. Nenhuma mudança de código foi necessária para funcionar; uma mudança pequena (seção 5.1) zera o custo estimado do Agent no modo assinatura.

> Este plano está em português a pedido do usuário. Fica fora do fluxo de tradução da documentação pública.

## 1. Estado da `main`

- `main` local = `origin/main` = `e2e5dbfe5` (`chore(ci): make personal repository workflows manual`), após `git fetch`. Nenhum fast-forward foi necessário.
- A tradução está na `main`: `CLAUDE.md`, `agent_runtime_profile/` (prosa), código e comentários estão em inglês.
- Chinês restante é esperado pelo ADR 0121, não uma divergência:
  - `CONTRIBUTING.md` e `website/docs/dev/architecture.md` são documentação pública com fonte em chinês; a edição inglesa fica em `website/i18n/en/...`.
  - `agent_runtime_profile/` mantém literais funcionais (ex.: `projects/{项目名}`, `Avoid: BGM、文字字幕、水印`).
  - Mensagens de log e de erro do servidor ainda em chinês (ex.: `server/app.py:140`, health `视频项目管理 WebUI 运行正常`) são literais preservados/localizados.

## 2. Evidências no código

| Ponto | Evidência | Impacto |
|---|---|---|
| Injeção de env do Agent | `server/agent_runtime/options_assembler.py:73-92` (`load_provider_env_overrides`) → `lib/config/service.py:89-120` (`build_anthropic_env`) | Sem credencial ativa, `ANTHROPIC_*` vêm de `system_setting` (vazias). `CLAUDE_CODE_OAUTH_TOKEN` e `ANTHROPIC_AUTH_TOKEN` são forçadas a `""` (`lib/config/env_keys.py:20-25`). O CLI cai no login do Keychain. |
| Startup recusa segredos | `server/app.py:132-144` (`PROVIDER_SECRET_KEYS`) | Só falha se `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` (ou chaves de mídia) estiverem no ambiente. Variáveis vazias passam. |
| Sandbox macOS | `server/app.py:229-235` | Só exige `sandbox-exec` (nativo em `/usr/bin`). Aplica-se ao Bash do Agent, não à autenticação do CLI. |
| Binário do CLI | `options_assembler.py:376-412` não define `cli_path` | Usa o CLI empacotado em `.venv/.../claude_agent_sdk/_bundled/claude`; ele lê a credencial `Claude Code-credentials` do Keychain (presente). |
| `CLAUDE_CONFIG_DIR` / `ARCREEL_SDK_SESSION_STORE` | `lib/agent/agent_session_store/__init__.py:12-45` | Padrão `db`; transcrições ficam no SQLite. `~/.claude` só é lido para sessões locais legadas. Não interfere na autenticação. |
| Interface exige credencial? | `frontend/src/stores/config-status-store.ts:88,180-195` | Não bloqueia. `isEmbeddedAgentConfigured` (= `anthropic_api_key.is_set`) só mostra o aviso “embedded agent not configured” na seção ArcReel Agent das Settings. Nenhuma checagem no backend (`server/routers/assistant.py:153-196`). |

## 3. Decisão: só configuração (sem flag)

Basta configuração. Uma flag “usar login local do Claude Code” só serviria para esconder o aviso das Settings. Diff mínimo, se um dia quiser:

- backend: expor `agent_auth_mode: "local_login"` em `GET /api/v1/system/config` quando `ARCREEL_AGENT_LOCAL_LOGIN=1`;
- frontend: `isEmbeddedAgentConfigured = is_set || agent_auth_mode === "local_login"` (1 linha em `config-status-store.ts`).

Conflito de merge: baixo (2 arquivos, poucas linhas), mas sem benefício funcional. **Não recomendado agora.**

Condições que precisam continuar verdadeiras:

1. Nenhuma credencial Anthropic ativa nas Settings (tabela `agent_anthropic_credentials` vazia; `anthropic_api_key` vazio em `system_setting`). Se adicionar uma, ela tem precedência e passa a cobrar API.
2. O servidor sobe com ambiente limpo (`env -i`, abaixo). Além de evitar `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN`, isso impede herdar variáveis do app Claude Desktop/terminal (`ANTHROPIC_BASE_URL`, `CLAUDE_CODE_*`, como `CLAUDE_CODE_SDK_HAS_HOST_AUTH_REFRESH`) que o subprocesso do SDK receberia por herança.
3. O Claude Code continua logado no Mac (`claude` → `/login`, se expirar).

## 4. Instalação executada (neste worktree)

| Item | Versão/estado |
|---|---|
| `uv` | 0.13.7; `uv sync` OK (venv com Python 3.12.16) |
| Node | sistema tinha v22.22.0 (< 24.12 exigido); instalado **v24.22.2 via nvm** |
| `pnpm` | `pnpm install` em `frontend/` OK (pnpm 10.33.2 via packageManager) |
| `ffmpeg`/`ffprobe` | 9.0.1 em `/opt/homebrew/bin` |
| Claude Code | 2.1.286, credencial no Keychain |
| `.env` | criado na raiz do worktree, `chmod 600`, ignorado pelo git (`.gitignore:38`) |
| Banco | `uv run alembic upgrade head` → `~/ArcReelData/arcreel.db` (SQLite) |

Conteúdo do `.env` (valores gerados com `openssl rand`, não registrados aqui):

```
AUTH_USERNAME=admin
AUTH_PASSWORD=<gerado>
AUTH_TOKEN_SECRET=<gerado>
ARCREEL_DATA_DIR=$HOME/ArcReelData
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
TZ=America/Sao_Paulo
```

`DATABASE_URL` não foi definido (padrão SQLite dentro de `ARCREEL_DATA_DIR`). `AUTH_ENABLED` fica no padrão `true`. A senha fica só no `.env`: `grep AUTH_PASSWORD .env`.

## 5. Primeiro run verificado

- Backend: `Application startup complete`, sem `SECURITY: ... provider 密钥`. `GET /health` → `{"status":"ok"}`.
- Frontend: `http://127.0.0.1:5173` → 200, tela de login renderiza.
- API: login `POST /api/v1/auth/token` OK; projeto `smoke-test` criado (`generation_mode=storyboard`).
- Agent: `POST /api/v1/projects/smoke-test/assistant/sessions/send` com “Reply with exactly the word PONG” → sessão `completed`, resposta `PONG` em ~7 s.
- Prova de assinatura: `agent_anthropic_credentials` com 0 linhas, nenhuma chave `anthropic*` em `system_setting`, servidor iniciado com `env -i` (só `HOME USER LOGNAME LANG TERM PATH`). A única credencial disponível para o CLI empacotado era o Keychain. O evento `init` (`apiKeySource`) não é persistido pelo ArcReel; o POC anterior já mostrou `apiKeySource='none'` nesse cenário.
- Agent completo (segundo teste, 2026-11-07 19:2x, no servidor iniciado pelo usuário, sem `ANTHROPIC_*`/`CLAUDE_CODE_*` no ambiente do processo): um turno pediu 5 capacidades sem gerar mídia. Todas funcionaram, com 7 chamadas de ferramenta e nenhum `tool_result` com erro, em 29 s:
  - ferramentas MCP do ArcReel `mcp__arcreel__get_project_content` e `mcp__arcreel__get_workflow_plan` (carregadas via `ToolSearch`);
  - `Bash` (`pwd && ls -la`, duas vezes) dentro do sandbox `sandbox-exec`;
  - `Read` de `project.json`;
  - subagente `Explore` via ferramenta `Agent`, que devolveu a contagem de arquivos.
- Interface web: login, painel do Agent do projeto `smoke-test`, mensagem enviada pela caixa do Copilot → o Agent chamou `get_workflow_plan` e a resposta apareceu por streaming.
- Idioma: a sessão fixa o idioma no primeiro turno pelo `Accept-Language` (`server/i18n.py:24`; prompt com `snapshot=True` em `options_assembler.py`). As sessões de teste criadas pela API sem esse cabeçalho ficaram em chinês (padrão). Sessões criadas pela interface seguem o idioma dela. Idiomas suportados: `zh`, `en`, `vi`, `ru` (`lib/i18n/__init__.py:48`); português não existe.
- Consumo medido (`api_calls`): o turno usou **claude-opus-5-5 com ~36 k tokens de entrada** (prompt de sistema + perfil) e um Haiku auxiliar. O `cost_amount` de US$ 0,175 é estimativa equivalente à API; com assinatura não há cobrança, mas consome a cota. O turno de 5 capacidades usou ~162 k tokens de entrada no Opus (114 k em cache), equivalente a US$ 0,40 na API.
- **Não há cobrança de API.** O binário que o Agent usa (`.venv/.../claude_agent_sdk/_bundled/claude`, 2.1.309), rodado com ambiente limpo e as quatro variáveis Anthropic vazias, informa em `auth status`: `"authMethod": "claude.ai"`, `"apiProvider": "firstParty"`, `"subscriptionType": "max"`. Ou seja, autentica pela assinatura (OAuth do claude.ai), não por chave de API. Não existe chave de API configurada em lugar nenhum (banco, `.env`, ambiente). Os valores em US$ do ArcReel (`api_calls.cost_amount` e o contador no topo do projeto) são estimativas locais: tokens × preço de catálogo × multiplicador (`lib/agent/credential_tiers.py:67`). Não são faturas. Depois da mudança da seção 5.1, o Agent entra com custo zero no modo assinatura.
- Nenhuma mídia foi gerada; nenhuma chave de provedor foi inserida.

### 5.1 Custo do Agent zerado no modo assinatura (mudança de código)

Pedido do usuário: o total em US$ deve refletir só o gasto real (provedores de mídia na nuvem), sem a estimativa do Agent.

- `lib/config/service.py` (`build_anthropic_env`, ramo sem credencial ativa): se `ANTHROPIC_API_KEY` também está vazia em `system_setting`, o pricing vira `AgentPricing(multiplier=0.0)`. O multiplicador 0 já é tratado pelo upstream como “preço zero” (`lib/billing/catalog_pricing.py:90`). Os tokens continuam registrados em `api_calls`; custos de imagem, vídeo e áudio não passam por aqui e seguem contados.
- Sem flag: a condição (nenhuma chave em lugar nenhum) é exatamente o caso em que o CLI só pode usar o login local. Com credencial ou chave legada, nada muda.
- Testes: `tests/unit/lib/config/test_anthropic_env_dict.py` atualizado (sem chave → multiplicador 0; chave legada → preço normal). Suítes `tests/unit/lib/{billing,config,agent}`, `tests/unit/server/agent_runtime`, `tests/integration/server/agent_runtime`: 1384 passaram. `ruff check`/`format --check` OK.
- Verificação ao vivo: sessão nova → linhas em `api_calls` com `cost_amount = 0.0` (Opus 36 085 tokens, Haiku 1 185).
- Dados antigos: as 5 linhas de teste do `smoke-test` gravadas antes da mudança foram zeradas manualmente (`UPDATE api_calls SET cost_amount = 0 WHERE provider='anthropic' AND id <= 5`). Total atual: US$ 0,00.
- Sessões já abertas guardam o pricing da conexão; a mudança vale para sessões novas ou retomadas após reiniciar o backend.
- Conflito de merge: uma função, 4 linhas. Se o upstream mexer em `build_anthropic_env`, reaplicar.
- Observação operacional: sem limite, o uvicorn esperava para sempre as conexões SSE abertas (aba do projeto aberta) antes de reiniciar ou parar. Resolvido em `scripts/run_local.sh` com `--timeout-graceful-shutdown 3` e reload desligado por padrão (seção 6).

## 6. Uso diário

Pré-requisito: Claude Code logado (`claude`, depois `/login` se pedir).

**Comando único** (na raiz do repositório): sobe backend e frontend com ambiente limpo, espera o `/health`, prefixa os logs com `[api]`/`[web]` e para os dois com um `Ctrl+C`:

```bash
scripts/run_local.sh
```

- `--setup`: roda `uv sync` e `pnpm install` antes (use depois de `git pull`).
- Por padrão o backend roda sem auto-reload (uso normal e futuro autopilot): editar código, `git pull` ou trocar de branch não reinicia o backend no meio de um turno do Agent ou de uma geração. Depois de `git pull`, pare e suba de novo com `--setup`.
- `--reload`: reinicia o backend quando um `.py` em `server/` ou `lib/` muda (para editar código). As conexões SSE abertas são derrubadas após 3 s (`--timeout-graceful-shutdown 3`, também usado no `Ctrl+C`) e o frontend reconecta sozinho, sem erro na tela. Um turno do Agent em andamento é perdido (a sessão volta como interrompida; reenvie a mensagem). Se houver geração de imagem/vídeo em andamento, a API fica parada até ela terminar. O log mostra `ERROR: Cancel N running task(s)...` a cada reload com aba aberta: é esperado.
- `--no-reload`: o padrão, explícito.
- Recusa iniciar se as portas 1241/5173 estiverem ocupadas, e mostra os PIDs. As migrações rodam sozinhas no startup do backend (`lib/db/__init__.py:64`).
- Encontra o Node >= 24.12 sozinho (o do `PATH` ou o mais novo do nvm).
- Testado: subida, `/health`, proxy `/api` do Vite, turno do Agent pela assinatura com custo 0, `Ctrl+C` real no terminal liberando as portas sem processos órfãos. Com o timeout de 3 s: no modo padrão, tocar `lib/__init__.py` não reinicia o backend (stream SSE continua aberto); com `--reload` e stream SSE aberto, o `/health` volta em ~5-8 s (também durante um turno do Agent, que fica como interrompido, sem processo `claude` sobrando); parar via `SIGTERM` leva ~4 s com stream aberto, portas livres e nenhum processo nos grupos da API/web.

Comandos equivalentes, separados (para depurar um servidor só):

Backend (terminal 1, na raiz do repositório):

```bash
env -i HOME="$HOME" USER="$USER" LOGNAME="$USER" LANG=en_US.UTF-8 TERM=xterm-256color PATH="$HOME/.nvm/versions/node/v24.22.2/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" uv run uvicorn server.app:app --timeout-graceful-shutdown 3 --host 127.0.0.1 --port 1241
```

Para editar código com reload, acrescente `--reload --reload-dir server --reload-dir lib`.

Frontend (terminal 2, em `frontend/`; `--host 127.0.0.1` porque `vite.config` usa `0.0.0.0`, o que exporia na rede local):

```bash
env -i HOME="$HOME" USER="$USER" LANG=en_US.UTF-8 TERM=xterm-256color PATH="$HOME/.nvm/versions/node/v24.22.2/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" pnpm dev --host 127.0.0.1
```

Abrir `http://127.0.0.1:5173`. Parar: `Ctrl+C` em cada terminal (ou `lsof -ti :1241 -ti :5173 | xargs kill`).

Após `git pull`: `uv sync`, `pnpm install` em `frontend/`, e as migrações:

```bash
env -i HOME="$HOME" USER="$USER" LANG=en_US.UTF-8 PATH="/opt/homebrew/bin:/usr/bin:/bin" uv run alembic upgrade head
```

Sugestão: guardar os dois comandos num script fora do repositório (ex.: `~/bin/arcreel-up`) para não precisar de mudanças versionadas.

## 7. Atualizar o upstream sem conflito

- Esta abordagem não altera nenhum arquivo versionado: `.env` é ignorado e os dados ficam em `~/ArcReelData`. Merges do upstream não conflitam.
- Fluxo: `git fetch upstream && git merge upstream/main` na `main` (ou rebase do fork), depois `uv sync`, `pnpm install`, `alembic upgrade head`.
- Pontos a revisar a cada atualização (podem quebrar a premissa):
  - `lib/config/env_keys.py` e `lib/config/service.py::build_anthropic_env` (se passarem a exigir credencial ou injetar outro token);
  - `server/app.py::assert_no_provider_secrets_in_environ`;
  - a mudança local de `build_anthropic_env` (seção 5.1), único ponto de possível conflito;
  - `frontend/src/stores/config-status-store.ts` (se o aviso virar bloqueio);
  - versão do `claude-agent-sdk` em `uv.lock` (o CLI empacotado muda junto).
- Teste rápido após atualizar: repetir o “PONG” do item 5.

## 8. Riscos

- **Cota da assinatura**: cada turno do Copilot custa ~36 k tokens de entrada no Opus. O autopilot pode esgotar a janela de uso rapidamente. Mitigação: definir modelo mais barato sem criar credencial (`anthropic_model` / `anthropic_default_*_model` em `system_setting`, via `PATCH /api/v1/system/config`; endpoint marcado como deprecated, remoção prevista na 0.14.0), e limitar `max_turns`.
- **Termos de uso**: uso pessoal, local, um único usuário, binário original do Claude Code. Não expor as portas 1241/5173 fora de `127.0.0.1`, não compartilhar o acesso. Referências: https://code.claude.com/docs/en/authentication e https://code.claude.com/docs/en/legal-and-compliance.
- **Expiração do login**: se o OAuth expirar, o Agent falha no início da sessão (HTTP 502 `agent_startup_failed`). Solução: `claude` → `/login`.
- **Variáveis herdadas**: iniciar o servidor a partir de um terminal do Claude Desktop sem `env -i` herda `ANTHROPIC_BASE_URL` e `CLAUDE_CODE_*`. O ArcReel zera `ANTHROPIC_BASE_URL` em `options.env`, mas não as `CLAUDE_CODE_*` fora da lista.
- **Credencial adicionada por engano** nas Settings → ArcReel Agent passa a ter precedência e cobra API.
- **Node**: o shell padrão ainda usa Node 22; sem o PATH do nvm 24, `pnpm` falha no `engines`.

## 9. Checklist

- [x] `main` sincronizada e tradução confirmada
- [x] Pré-requisitos (Node 24 instalado via nvm)
- [x] `uv sync`, `pnpm install`, `.env`, migrações
- [x] Backend e frontend no ar; `/health` OK
- [x] Agent respondeu via assinatura (projeto `smoke-test`)
- [x] Agent usou ferramentas MCP do ArcReel, Bash no sandbox, Read e subagente; Copilot funciona pela interface
- [ ] Teste de produção real: enviar um texto-fonte e deixar o Agent planejar episódios e roteiro (gasta cota; mídia só depois de configurar provedores)
- [ ] Opcional: localidade `pt` para o Agent responder em português (mudança de código; hoje só `zh`/`en`/`vi`/`ru`)
- [ ] Usuário: entrar na interface com `admin` + senha do `.env` e conferir o Copilot no projeto `smoke-test` (apagar depois, se quiser)
- [ ] Usuário: configurar provedores de mídia em Settings → Providers (ex.: Gemini/Ark) para imagem, vídeo e texto; o aviso de Agent não configurado pode ser ignorado
- [ ] Decidir o modelo padrão do Agent (Opus vs Sonnet) por causa da cota
- [ ] Criar script `arcreel-up` fora do repositório (opcional)
- [ ] Próxima fase: automação do fluxo de produção (“autopilot”)
