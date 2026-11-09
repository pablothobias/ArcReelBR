# Prompt 1: fluxo nativo, insumos e diagnóstico editorial

Investigue o uso correto do framework ArcReel e diagnostique os problemas da nossa última produção. Descubra, com evidências, quais entradas, configurações e etapas são necessárias para produzir conteúdo compreensível, coerente e fiel à história.

Leia primeiro `/Users/pablo.carminatti.br/Projects/ArcReelBR/docs/handoffs/2026-11-09-investigations/README.md`. Esta tarefa é de investigação e documentação, não de implementação ou produção.

## Contexto e limites

- Repositório: `/Users/pablo.carminatti.br/Projects/ArcReelBR`.
- Projeto: `/Users/pablo.carminatti.br/ArcReelData/projects/br-viral-reuniao-impossivel`.
- Vídeo: `renders/episode_1/tl-99ec13b6/final_cut.without_narration.burned_subtitles.mp4`, relativo ao projeto.
- Referência: https://www.youtube.com/watch?v=BKorP55Aqvg, The Expert, de Lauris Beinerts.
- Pesquisa local, a verificar: `/Users/pablo.carminatti.br/ArcReelData/editorial/viral-reference-the-expert`.

Feedback do usuário: Júlio muda de posição; o usuário não recebeu o roteiro em inglês para avaliar a compreensão; não entendeu o contexto nem achou graça; considera o resultado genérico e sem valor. Suspeita de problemas nos keyframes e, principalmente, no insumo/contexto/história fornecidos ao framework. Investigue essas hipóteses sem adotá-las como conclusões.

O Codex automatiza o framework nativo por MCP. O Agent integrado mantém planejamento, referências, prompts, geração, revisão e edição. Não proponha outro harness nem transfira a produção para scripts externos.

Faça somente leituras na aplicação, projetos e serviços. Escreva apenas relatório e anexos em `docs/audits/2026-11-09-framework/`, sem editar os arquivos desta passagem. Não altere configurações, código, produção, issues ou Git; não reinicie serviços, crie tokens, refaça login ou gere mídia. Não faça chamadas pagas. Aprovações anteriores não se aplicam. Não exponha credenciais. Não crie subagentes com GPT-6 Astra em esforço máximo sem autorização expressa.

## Método e evidência

Leia AGENTS.md. Registre commit, alterações locais relevantes e a instância executada. Consulte obrigatoriamente:

- Documentação local, arquitetura, guias, ADRs e exemplos.
- Instruções, skills e ferramentas de `agent_runtime_profile/`.
- Interface real, inclusive campos avançados/condicionais.
- Contratos e comportamento no código, API e MCP.
- Documentação oficial online, exemplos, demonstrações e discussões do upstream confirmado.
- Documentação oficial dos modelos/provedores utilizados quando necessária para formatos, referências e limites.

Diferencie upstream e versão local. Não faça suposições para preencher lacunas. Cite arquivo/linha, URL/seção/data, tela observada ou artefato para cada conclusão relevante. Classifique: comprovado, hipótese parcial, não verificado/inacessível, recomendação editorial/operacional. Exponha divergências entre documentação, UI e código.

Não confunda campo existente com campo consumido; ferramenta disponível com utilizada; render concluído com qualidade aprovada; transcrição com atuação/sincronismo; popularidade da fonte com eficácia da adaptação.

## 1. Fluxo nativo por caso de uso

Identifique todos os casos realmente suportados, incluindo séries, humor/memes e minidramas de um vídeo. Separe suporte direto, modo genérico, necessidade de adaptação e ausência de suporte.

Reconstrua o percurso esperado de uma pessoa na aplicação: entrada, entrevista, planejamento, roteiro, referências, keyframes, vídeo/voz, revisão, edição/legendas e exportação. Essa enumeração não presume a ordem. Mostre a ordem verdadeira, pré-requisitos, decisões, checkpoints, alternativas, critérios de avanço e responsáveis. Mapeie o percurso ao MCP e suas lacunas.

## 2. Inventário funcional das entradas

Mapeie telas, formulários e campos relevantes, inclusive condicionais, avançados e entradas só do Agent/API/MCP. Para cada campo, registre nome e identificador, localização, escopo/modos, tipo/formato/limites, default, efeito da ausência, obrigatoriedade técnica/condicional, benefício editorial, responsável, persistência, consumidor, disponibilidade MCP e exemplo válido.

Cubra briefing/fontes/roteiro/episódios/duração; idiomas; personagens/figurino/objetos/ambientes; referências e continuidade; voz/TTS; modelos/resolução/proporção/áudio; revisões/versões/edição/legendas/exportação.

Comprove se referências chegam ao modelo escolhido. Upload visível não prova envio. Diferencie requisitos de boas práticas propostas; não torne tudo obrigatório. Faça apenas a comparação de configuração necessária para explicar o fluxo: a auditoria exaustiva do estado atual pertence ao prompt 2.

## 3. Reconstrução da rodada

Trace referência → material enviado → entrevista/briefing → roteiro → revisões → prompts → referências utilizadas → imagens → clipes → montagem. Use históricos, versões, chamadas e arquivos, não só o vídeo final.

Continuidade espacial:
- Identifique com timestamps onde Júlio muda de posição.
- Compare fichas, keyframes, prompts, clipes e cortes.
- Verifique mesa, posições, eixo de câmera, olhares e relações espaciais.
- Localize a primeira etapa em que o defeito surge.
- Distinga mudança legítima de câmera de posição contraditória.
- Investigue o que o revisor detectou e por que aceitou.

Compreensão e humor:
- Compare a referência completa, o trecho escolhido e a adaptação.
- Identifique premissa, contexto, conflito, preparação, escalada e desfecho.
- Avalie se o trecho funciona sozinho para quem não conhece o original.
- Mostre o que foi removido, alterado ou presumido e o possível efeito.
- Verifique se houve tradução de falas sem história autossuficiente.
- Examine tempos de fala, pausas, interrupções, atuação prevista, edição e legendas.
- Apresente o roteiro realmente produzido em PT-BR e uma tradução fiel para inglês, separando texto planejado, fala reconhecida e tradução.
- Audite o que as revisões avaliaram e quais evidências sustentaram a aprovação.

Examine áudio/vídeo diretamente se suas ferramentas permitirem. Se houver apenas quadros/transcrições, declare o limite; não afirme ter ouvido ou validado performance/timing audiovisual.

## 4. Hipóteses concorrentes

Compare referência inadequada; recorte inadequado de boa referência; briefing incompleto; roteiro sem contexto/desfecho; uso incompleto do framework; configuração/limitação de modelo; continuidade; revisão permissiva/sem evidência; edição/voz/atuação/legendas; lacuna MCP.

Para cada hipótese: evidências favoráveis e contrárias, confiança e verificação faltante. Não force causa única. Se causalidade não puder ser atribuída, proponha a menor verificação que distingue as hipóteses; não execute testes com custo ou mutação.

## 5. Briefing adequado à entrada real

Após investigar, proponha briefing mínimo, briefing completo, variações por caso e exemplo preenchido deste teste. Use o formato realmente aceito: conversa estruturada, arquivo ou schema comprovado. Não invente JSON/formulário sem suporte.

Separe informações necessárias na entrada, perguntas da entrevista nativa, decisões do Agent e artefatos preenchidos depois. Inclua objetivo, audiência, premissa, fonte/trecho, contexto, mecanismo de humor, invariantes, liberdade de localização, personagens, continuidade espacial, referências, restrições técnicas e critérios observáveis. Mapeie cada item ao campo/etapa consumidor.

Prepare apresentação do roteiro em português e inglês para inspeção do usuário sem inventar aprovação humana obrigatória no fluxo autônomo. Não prometa prompt perfeito ou garantia de humor; delimite controle do briefing e dependência da geração/avaliação.

## Entregáveis e revisão final

Entregue em português: diagnóstico executivo; fluxo por caso; inventário funcional com cobertura; configuração relevante ao fluxo; análise da rodada com timestamps; templates/exemplo; mudanças priorizadas reaproveitando o existente; lacunas e proposta de próximo teste sem executá-lo. Inclua fontes e versões.

Revise antes de entregar: conclusões com evidência ou rótulo de hipótese; recomendações ligadas a problemas; nenhuma capacidade existente apresentada como nova; nenhuma inferência audiovisual baseada só em quadros; nenhuma configuração modificada. O relatório deve permitir rastrear onde o material mudou e onde a qualidade se perdeu.

Responda explicitamente: “O insumo foi realmente o principal gargalo? Que evidências sustentam essa conclusão e quais outras causas contribuíram?”
