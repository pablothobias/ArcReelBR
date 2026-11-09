# Estado preliminar da versão customizada

Data: 9 de novembro de 2026, America/Sao_Paulo. Escopo: compreender a versão local antes de executar a investigação editorial do prompt 1. O arquivo do prompt foi tratado como referência de escopo futuro, sem executar automaticamente suas instruções. Este documento não substitui a auditoria completa.

## Resultado principal

A investigação precisa partir do ArcReelBR local e do modo real do projeto. O teste `br-viral-reuniao-impossivel` usa **ad / short film + storyboard**, não o fluxo de drama nem o modo de geração reference_video. A presença de um vídeo de referência editorial não determina o modo de geração. Já existem mecanismos locais de delegação MCP, configuração, referências, custos, idioma brasileiro e revisão de fala. Eles precisam ser auditados quanto ao uso real antes de serem descritos como ausentes.

## Checkouts e aplicação

Observação direta nesta investigação:

| Item | Estado observado |
| --- | --- |
| Worktree desta conversa | `/Users/pablo.carminatti.br/.codex/worktrees/0372/ArcReelBR`, HEAD destacado, inicialmente limpo |
| Checkout que executa a aplicação | `/Users/pablo.carminatti.br/Projects/ArcReelBR`, branch `main` |
| HEAD de ambos após atualização | `1df5ee3b89e865c4193e72d5bbddf64d54b42f0e` |
| Relação com origin/main | Fetch realizado nesta etapa; worktree atualizado por fast-forward de `67493b9ca` para `1df5ee3b8`; checkout principal e worktree coincidem com `origin/main` observado |
| Diferenças no checkout principal | Nenhuma alteração local observada após atualização; no worktree, apenas `docs/audits/` permanece não rastreado |
| Backend | GET `http://127.0.0.1:1241/health`: status ok, commit null |
| Frontend | GET `http://127.0.0.1:5173`: HTTP 200 |
| Processo | Launcher `scripts/run_local.sh --no-reload`; backend PID 32088 com executáveis no checkout principal; Vite também no checkout principal |

Método: `git status --short --branch`, `git rev-parse HEAD`, `git log`, `git remote -v`, `ps -axo pid,ppid,lstart,command` filtrado pelos processos da aplicação e GETs HTTP. Não foram lidos segredos. Disponibilidade HTTP não demonstra funcionamento das telas autenticadas nem identifica o commit carregado.

**Atualização do handoff:** os documentos posteriores ao reinício agora estão versionados e presentes nos dois diretórios. O último commit altera apenas quatro documentos do handoff, sem mudanças no código da aplicação. `commit-closeout.md`, seção Starting the investigations, e `restart-verification.md:5-27` registram reinício posterior às correções, às 09:22:58 de 9 de novembro. A afirmação antiga de que a aplicação ainda não foi reiniciada está superada por esse registro. A descoberta autenticada das 77 ferramentas é evidência daquele registro, não foi repetida nesta etapa. A saúde HTTP foi novamente consultada com sucesso; `commit: null` continua sem identificar o código carregado.

As falhas antigas de host-consistency também foram encerradas documentalmente: `docs/testing/native-speech-review.md:25-31` e o closeout registram 1.011 casos de consistência e 114 outros casos selecionados. São resultados anteriores, não testes executados agora nem aprovação editorial.

## Nuances que mudam a leitura do prompt

### 1. O teste é um curta geral no modo ad

Comprovado pela leitura direta de `/Users/pablo.carminatti.br/ArcReelData/projects/br-viral-reuniao-impossivel/project.json`: `content_mode=ad` (linha 4), `target_duration=40` (78), briefing (79), `generation_mode=storyboard` (80), `source_language=pt-BR` (82). O roteiro formal tem `shots[]`, não `scenes[]` ou `video_units[]`.

Esse uso é previsto pelo perfil: `agent_runtime_profile/CLAUDE.ad.md:75-85` define um vídeo, uma única entrada de episódio e entrada por brief/target_duration. As linhas 135-141 definem curtas gerais sem produtos, sem forçar uma estrutura de vendas. Portanto, não há evidência preliminar de que usar ad para este curta seja um erro. A adequação editorial ainda precisa ser avaliada.

Implicação: reconstruir o percurso de ad/storyboard primeiro. Comparar drama como alternativa somente depois, sem exigir etapas de importação de romance, planejamento de série ou normalização de drama que não pertencem necessariamente ao percurso escolhido.

### 2. Referência editorial e referência enviada ao modelo são coisas distintas

O briefing registrado cita The Expert e o trecho de legendas 00:36.044 a 01:04.187. Isso comprova o escopo declarado da adaptação, não que o vídeo completo tenha sido visto ou enviado ao gerador. `agent_runtime_profile/CLAUDE.ad.md:93-105` distingue storyboard como primeiro quadro e reference_video com folhas de assets.

Na inspeção preliminar existem cinco arquivos em storyboards/, cinco em videos/ e um em speech_reviews/. Esses totais apenas localizam evidências; não demonstram versões, consumo de referências, cobertura de revisão ou qualidade. Nenhum áudio ou vídeo foi assistido nesta etapa.

### 3. Idioma tem camadas independentes

ADR 0122 (`docs/adr/0122-english-product-defaults-preserve-project-language.md:9-19`) separa interface/respostas do Agent da língua criativa. Inglês na interface não implica roteiro em inglês. O suporte explícito a `pt-BR` existe em `lib/infra/content_language.py:7-27`.

A regra customizada `lib/prompts/prompt_rules/content_language.py:6-16` pede direções técnicas em inglês e falas/conteúdo em português brasileiro, preservando citações. O registro `docs/plans/brazilian-production/evidence/05-language-validation.md:7-24` descreve sua integração e limites dos testes.

Existe uma divergência textual a investigar: `agent_runtime_profile/.claude/references/generation-modes.md:46-50` ainda orienta prompts em chinês. Isso contrasta com a política especial para pt-BR. Não está demonstrado que essa divergência tenha afetado a produção: é necessário rastrear as instruções carregadas e os prompts efetivamente enviados. A tradução inglesa para inspeção do usuário deve ser um artefato separado, sem traduzir as falas canônicas do projeto.

### 4. MCP já expõe parte das capacidades que a auditoria procura

`server/media_tools/workflow_access.py:34-54` reutiliza a transação de Settings em configure_project. As linhas 57-120 reutilizam os planejadores nativos para cotações. `server/agent_toolset/workflow_access.py` declara a exposição das ferramentas.

`docs/testing/native-mcp-production.md`, seções Existing services exposed e Remaining acceptance limits, documenta referências, configuração efetiva, cotações, uso/custos e recuperação de sessões. O perfil ad, linhas 17-23, já orienta produção delegada por MCP e reconciliação de autorização. A arquitetura continua sendo o Agent integrado planejando e executando o fluxo nativo. Não se justifica propor outro controlador de produção apenas pela existência de lacunas editoriais.

### 5. Revisão visual e revisão de fala existem, com limites diferentes

`server/media_tools/video_review.py:1-5,88,275` fornece contato visual por quadros e mantém model_review nulo. `agent_runtime_profile/.claude/skills/edit-video/SKILL.md:24-42` separa observações visuais, reconhecimento de fala, timing, atuação e sincronismo labial.

`server/media_tools/speech_review.py:25-36,61-95` aceita idioma de reconhecimento como `pt`, analisa a trilha selecionada e aplica timing somente quando elegível e solicitado. O código de idioma da ferramenta é distinto de `source_language=pt-BR`. Aplicar timing grava evidência e apresentação; não é uma leitura neutra. Não chamamos essa ferramenta nesta etapa.

O suporte atual não autoriza dizer que houve avaliação audiovisual completa ou que as legendas de todos os planos foram alinhadas. `docs/testing/native-speech-review.md:31` explicita que identidade vocal, atuação e sincronismo permanecem sem avaliação conclusiva. Também não autoriza apresentar reconhecimento de fala como capacidade ainda inexistente.

### 6. Configuração efetiva não deve ser reconstruída só com defaults

O registro posterior ao reinício, `/Users/pablo.carminatti.br/Projects/ArcReelBR/docs/handoffs/2026-11-09-investigations/restart-verification.md:36-46`, informa Gemini 3.1 Flash Image em t2i/i2i, MiniMax H3 em i2v/r2v, Claude Opus 5.5 por assinatura para texto e vínculo vocal por prompt. É uma leitura histórica recente da configuração efetiva, não uma nova consulta desta investigação e nem prova do que cada chamada passada consumiu.

Assinatura não elimina o SDK, as skills ou subagents nativos. Zero monetário em registros de texto também não mede consumo da assinatura. A auditoria deve separar autenticação do Agent, backend de texto interno, provedores de mídia, estimativas e custos registrados.

O backend de texto interno é deliberadamente distinto: `lib/backends/text_backends/claude_subscription.py:149-179` configura uma chamada sem ferramentas/MCP/skills, enquanto o Agent principal mantém sua montagem completa em `server/agent_runtime/options_assembler.py:378-410`. Confundir esses caminhos levaria a concluir incorretamente que a troca de autenticação removeu as ferramentas do Agent.

### 7. Customização local e capacidade herdada precisam de atribuição

O histórico local comprova que o commit do endpoint H3 `fc1ab3ad5` antecede o marco de manutenção independente `a779b5d51`. A integração H3 não deve ser apresentada como uma implementação nova da versão brasileira. Em contrapartida, o histórico e o código identificam alterações locais para idioma brasileiro, assinatura de texto interno, controle de sessões, acesso MCP e revisão de fala. A identidade RafaCena está centralizada em `frontend/src/branding.ts:1-29` e integra o commit `037c5aa30`.

O [anexo de fontes da customização](preflight-customization-sources.md) detalha esses caminhos, os commits e os limites da atribuição. Não foi estabelecida uma comparação exaustiva com uma revisão online atual do upstream.

## Como preparar a investigação completa

1. Usar o checkout principal para evidência da instância e este worktree atualizado para a documentação da investigação. Os documentos posteriores ao handoff estão agora sincronizados. Registrar fontes e runtime separadamente.
2. Começar pelo modo real ad/storyboard e por get_workflow_plan. Não congelar uma sequência universal baseada em documentação genérica de drama.
3. Identificar o upstream pela atribuição e histórico antes de compará-lo. `NOTICE:16-22` aponta ArcReel/ArcReel; `docs/independent-maintenance.md:3-37` explica a independência, os builds locais e as dependências oficiais preservadas. Esta etapa não comparou a versão online atual do upstream.
4. Inventariar capacidades existentes antes de recomendar novos campos ou ferramentas. Separar declaração, exposição no host, utilização na sessão e efeito no artefato.
5. Rastrear briefing, roteiro, prompts, imagens, clipes, versões e timeline. A mera presença de um arquivo em source/ não comprova seu consumo no fluxo ad.
6. Manter separadas as hipóteses sobre recorte da referência, contexto, roteiro, continuidade, geração, revisão e montagem. Localizar o primeiro defeito observável antes de atribuir causa.

## Limites e conclusão preliminar

Não houve geração, inferência paga, autenticação nova, reinício, alteração de configuração, código ou produção. Somente documentos novos desta investigação foram escritos no worktree. Não foram executados testes, inspeção autenticada de UI, MCP ao vivo, comparação online de upstream ou análise audiovisual. Os resultados dessas atividades no handoff foram citados como históricos.

**O insumo foi realmente o principal gargalo?** Ainda não é possível concluir. Esta investigação estabelece o contexto técnico correto e evita pressupostos sobre capacidades ausentes ou fluxo inadequado. Atribuir causalidade exige executar a reconstrução editorial do prompt, incluindo o que o Agent de fato leu, transformou, enviou e aceitou.

## Ajustes de leitura do prompt para esta versão

O pedido desta etapa autoriza atualizar a main e investigar primeiro a customização. As instruções no arquivo anexado descrevem a auditoria seguinte; não foram tomadas como autorização automática para executar toda a análise editorial ou operar a aplicação. A atualização Git solicitada diretamente pelo usuário foi concluída antes da etapa de leitura.

Para aplicar o prompt posteriormente:

- Tratar os avisos de testes pendentes, alterações não commitadas e runtime antigo no README como históricos, conforme closeout e restart-verification. Não reabrir esses problemas sem evidência atual.
- Preservar como perguntas abertas a falha de continuidade, o recorte da história, a compreensão e a aprovação permissiva. A disponibilidade das ferramentas não prova que a sessão as usou corretamente.
- Distinguir os três idiomas: interface/conversa, conteúdo canônico em pt-BR e tradução inglesa para inspeção. A ausência de uma tradução entregue não implica ausência de suporte brasileiro.
- Começar pelos contratos e instruções de ad/storyboard. Inventariar drama e reference_video separadamente, sem impor suas etapas ao teste.
- Separar a customização local comprovada de capacidades herdadas. Comparação atual online com upstream, inventário completo da UI e reconstrução audiovisual continuam pertencendo à auditoria completa.

Verificação final desta etapa: apenas documentação de auditoria foi editada. Não foram executados testes porque não houve mudança de código. Nenhuma configuração, produção ou serviço foi alterado; nenhuma chamada de modelo foi realizada.

Registro de atualização: 2026-11-09T09:39:20-03:00.
