# Prompt 2: auditoria das configurações atuais

Audite as configurações atuais do ArcReelBR usando documentação, recursos oficiais online, aplicação em execução e implementação local. Leia primeiro `/Users/pablo.carminatti.br/Projects/ArcReelBR/docs/handoffs/2026-11-09-investigations/README.md`.

## Objetivo e escopo

Descubra quais configurações estão corretas; vazias com defaults/herança; ausentes e necessárias; preenchidas mas inativas/ignoradas/incompatíveis/sobrescritas; opcionais úteis; ou não aplicáveis. Campo vazio não prova erro; preenchido não prova funcionamento.

Esta auditoria é independente da investigação editorial do prompt 1. Não reescreva roteiro/briefing nem avalie humor. Consulte conteúdo apenas para determinar aplicabilidade e efeito de configurações.

- Repositório: `/Users/pablo.carminatti.br/Projects/ArcReelBR`.
- Projetos: `br-viral-reuniao-impossivel` e `br-framework-problema-resolvido`.
- Raiz de dados previamente usada: `/Users/pablo.carminatti.br/ArcReelData`.

Confirme a instância, checkout, banco e raiz efetivamente utilizados. Uso pretendido: produção local pelo framework nativo, Codex via MCP, Agent integrado decidindo a produção, conteúdo PT-BR e prompts/instruções de geração em inglês, séries/humor/minidramas, fidelidade e continuidade, entrega vertical 1080×1920.

Escolhas anteriores a comparar com o estado real: Claude Agent SDK com assinatura Claude Code; Opus 5.5 medium; MiniMax H3; Nano Banana 2; áudio nativo inicialmente e ElevenLabs quando necessário. Essas escolhas não provam disponibilidade, compatibilidade, configuração ou uso. Verifique IDs, rotas e parâmetros. Distinga Agent integrado e chamadas auxiliares de texto.

## Limites

Somente leitura na aplicação, código e dados. Escreva relatório/anexos em `docs/audits/2026-11-09-configuration/`, sem editar esta passagem ou o relatório da outra investigação.

Não altere configurações, banco, código ou produção; não reinicie serviços, refaça login ou crie tokens; não use salvar/sincronizar/importar/testar conexão sem verificar efeitos, e não execute a ação se houver mutação ou custo. Não faça inferência, geração, avaliação paga, downloads de modelos, publicação Git/issues ou mensagens externas. Aprovações financeiras anteriores não se aplicam. Não exponha segredos. Não use GPT-6 Astra em esforço máximo sem autorização expressa.

Para credenciais, registre somente presença, origem, seleção e evidência existente de funcionamento. Testes necessários com efeitos externos ficam propostos, não executados.

## 1. Instância e fontes de verdade

Leia AGENTS.md. Registre commit/branch e alterações relevantes; processos/portas/checkout/raiz; persistência; perfil Agent; catálogos/endpoints; diferenças locais versus upstream confirmado. Registre versão/data das fontes locais e online.

Pontos de partida, não lista exaustiva:
- `lib/config/resolver.py`, `service.py`, `system_config.py`, `registry.py`, `model_setting_keys.py`.
- `frontend/src/components/pages/SystemConfigPage.tsx`, `ProjectSettingsPage.tsx`, `project-settings/`.
- `server/media_tools/workflow_access.py`.
- `server/agent_runtime/options_assembler.py`.
- `agent_runtime_profile/` e `website/docs/guide/providers.md`.

## 2. Inventário completo da configuração relevante

Inspecione telas reais, campos condicionais/avançados e contratos API/MCP para opções fora da UI. Cubra:
- Provedores/credenciais/endpoints/catálogos.
- Modelos globais e overrides por projeto/tarefa.
- Agent: autenticação, modelos/esforço, instruções, ferramentas, permissões e sessões.
- Chamadas auxiliares de texto separadamente.
- MCP/acesso externo.
- Idioma, estilo, proporção, duração, resolução e modos de geração.
- Personagens, ambientes, objetos e referências de imagem.
- Referências de áudio, vínculo de voz, TTS/narração e áudio nativo.
- Templates de prompt e personalizações.
- Armazenamento, acesso a arquivos e referências pelo provedor.
- Revisão de fala, legendas, edição e exportação.
- Outras configurações que afetem esses fluxos.

Registre todas as seções encontradas e justifique exclusões. Para cada item: nome/chave; tela/endpoint/ferramenta; escopo; tipo/valores/limites/dependências; valor salvo sem segredos; valor efetivo e origem; ausência/default; obrigatoriedade/aplicabilidade; consumidor; efeito e evidência; momento de aplicação; classificação/recomendação.

## 3. Precedência e consumo reais

Reconstrua por família, sem presumir uma ordem universal: defaults embutidos; catálogo; global; projeto; personagem/episódio/tomada; chamada; snapshots de tarefas/sessões; ambiente/credenciais injetadas; legado/migrações. Explique por que cada valor efetivo é aquele.

Separe placeholder, default exibido, valor salvo, valor resolvido, valor enviado historicamente e valor esperado numa próxima chamada. Examine o contrato de `get_effective_configuration`; ele não prova cobertura total sozinho.

## 4. Diagnóstico do estado atual

Compare global e projetos com o uso pretendido. Investigue:
- Vazio com fallback válido; override que impede o default global.
- Opção exclusiva de outro modo/modelo.
- Referência cadastrada, mas ausente da requisição.
- Modelo registrado, mas não selecionado para a tarefa.
- Texto simples/complexo versus Agent; assinatura versus API.
- Login reportado versus autenticação realmente observada.
- Esforço selecionado versus suportado/enviado.
- Áudio de referência versus descrição textual da voz.
- Resolução solicitada versus gerada versus exportada.
- Mudanças posteriores à produção e snapshots antigos.
- Arquivos inacessíveis por caminho/permissões.
- Capacidade existente sem exposição MCP.

Para referências, distinga inexistência, arquivo não vinculado, vínculo inaplicável, uso efetivo e evidência insuficiente. Não recomende preencher tudo. Identifique o mínimo por modo e benefícios adicionais comprovados ou apenas plausíveis.

## 5. Efeitos nos resultados e limites causais

Use registros existentes para verificar possíveis relações com posição/identidade, ambiente, voz, legendas, resolução e uso de referências. Separe erro demonstrado, comportamento normal, limitação de integração, decisão de produção, problema editorial fora do escopo e hipótese.

Não atribua falta de humor/compreensão a campo vazio sem mecanismo e evidência. Não presuma que configuração atual era a mesma da rodada. Se não houver histórico, declare que não pode reconstruí-la.

## 6. Pesquisa local e online

Consulte fontes oficiais do ArcReel e dos provedores/modelos relevantes. Demonstrações, exemplos e discussões são complementares e devem ser identificados como tais. Descubra o upstream real; compare versões.

Cada afirmação importante precisa de arquivo/linha, tela ou URL/seção/data, o que comprova e suas limitações. Exponha conflitos entre documentação, UI e código. Escreva “não verificado” quando necessário; não preencha lacunas com conhecimento genérico sobre vídeo.

## Entregáveis

Em português:
1. Diagnóstico: o que falta, o que funciona por herança e o que não se aplica.
2. Matriz: campo | escopo | salvo | efetivo | origem | aplicabilidade | evidência | diagnóstico | ação.
3. Lista de vazios: prejudicial, fallback válido, opcional, não aplicável, não verificável.
4. Configuração mínima e opções adicionais por modo suportado.
5. Plano priorizado, sem execução: valor proposto, justificativa, efeito, dependências, impacto em projetos existentes, necessidade de sessão/reinício, validação e reversão.
6. Decisões do usuário apenas onde fontes e decisões existentes não determinarem o valor; apresente alternativas e efeitos.
7. Lacunas de acesso/evidência e testes futuros necessários.

## Revisão antes de entregar

Cada vazio teve herança/aplicabilidade examinadas? As recomendações têm utilidade demonstrada? Salvo/efetivo/histórico estão separados? Presença de chave não virou prova de conexão? Hipóteses não viraram causas? Opções são compatíveis com modo/modelo? Capacidades existentes não foram tratadas como novas? Segredos foram omitidos? O escopo continua configuração, sem duplicar a investigação editorial?

Responda: “Quais configurações ausentes ou incorretas demonstravelmente prejudicam nosso fluxo hoje, e quais campos vazios podemos manter como estão?”
