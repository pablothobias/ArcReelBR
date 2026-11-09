# Roteiro produzido: português, inglês e reconhecimento de fala

Tradução preparada nesta auditoria, não entregue nem aprovada durante a produção. Fonte canônica: `scripts/episode_1.json`, na versão preservada pelo manifesto artifact-baseline.json. As frases em inglês traduzem o roteiro brasileiro, não transcrevem a atuação e não substituem as legendas da obra original. Contexto em cada plano é orientação de leitura da auditoria, não nova fala ou modificação do roteiro.

O texto de ASR abaixo foi reconhecido na rodada anterior, com faster-whisper local e sem prompt de transcrição. Não foi ouvido ou revalidado nesta auditoria. Pontuação/capitalização podem variar sem mudança de palavras. Identidade vocal, atuação e sincronismo labial continuam não avaliados.

## Plano 1: E1S01 (12 s planejados)

Regina, cliente, expõe o pedido absurdo seriamente; espera resposta. / Regina, the client, seriously states the absurd request and waits for an answer.

**Planejado PT-BR:** Para o nosso projeto novo, a gente precisa que vocês desenhem sete linhas vermelhas. Todas estritamente perpendiculares. Algumas com tinta verde, outras com tinta transparente. Dá para fazer?

**English, faithful translation of planned dialogue:** For our new project, we need you to draw seven red lines. All strictly perpendicular. Some with green ink, others with transparent ink. Can you do that?

**Reconhecido PT-BR:** Para o nosso projeto novo, a gente precisa que vocês desenhem sete linhas vermelhas, todas estritamente perpendiculares, algumas com tinta verde e outras com tinta transparente. Dá para fazer?

**Proveniência do ASR:** raiz:433, 2026-11-09T10:13:58.546Z. Texto coincide: False; timing elegível: False; bloqueio: `transcript_differs_from_canonical_speech`.

## Plano 2: E1S02 (4 s planejados)

Júlio, técnico, hesita e inicia uma negativa inacabada. / Júlio, the technical expert, hesitates and starts an unfinished refusal.

**Planejado PT-BR:** Não. Infelizmente, a gente...

**English, faithful translation of planned dialogue:** No. Unfortunately, we...

**Reconhecido PT-BR:** Não. Infelizmente, a gente...

**Proveniência do ASR:** raiz:395, 2026-11-09T10:08:42.161Z. Texto coincide: True; timing elegível: False; bloqueio: `missing_or_uncertain_word_boundaries`.

## Plano 3: E1S05 (8 s planejados)

Marcos, gerente e chefe de Júlio, impede a negativa e promete cumprir a tarefa. / Marcos, the manager and Júlio’s boss, cuts off the refusal and insists on completing the task.

**Planejado PT-BR:** Calma, Júlio! Nada de resposta precipitada. A tarefa foi passada e tem que ser cumprida. Afinal, você é o especialista.

**English, faithful translation of planned dialogue:** Hold on, Júlio! No hasty answers. The task has been assigned and it has to be carried out. After all, you are the expert.

**Reconhecido PT-BR:** Calma, Júlio. Nada de resposta precipitada. A tarefa foi passada e tem que ser cumprida. Afinal, você é o especialista.

**Proveniência do ASR:** raiz:405, 2026-11-09T10:08:55.557Z. Texto coincide: True; timing elegível: True; bloqueio: `None`.

## Plano 4: E1S03 (10 s planejados)

Júlio explica o conflito entre cor da linha e tinta. / Júlio explains the conflict between the line colour and the ink.

**Planejado PT-BR:** "Linha vermelha" quer dizer que a linha é vermelha. Desenhar uma linha vermelha com tinta verde... se não é impossível, é praticamente impossível.

**English, faithful translation of planned dialogue:** “Red line” means that the line is red. Drawing a red line with green ink... if it is not impossible, it is practically impossible.

**Reconhecido PT-BR:** linha vermelha quer dizer que a linha é vermelha desenhar uma linha vermelha com tinta verde se não é impossível é praticamente impossível

**Proveniência do ASR:** raiz:401, 2026-11-09T10:08:46.236Z. Texto coincide: True; timing elegível: False; bloqueio: `missing_or_uncertain_word_boundaries`.

## Plano 5: E1S04 (6 s planejados)

Regina questiona a impossibilidade; reação silenciosa encerra o curta, sem resposta. / Regina questions impossibility; a silent reaction ends the short without an answer.

**Planejado PT-BR:** Mas o que quer dizer "impossível", afinal?

**English, faithful translation of planned dialogue:** But what does “impossible” mean, after all?

**Reconhecido PT-BR:** Mas o que quer dizer impossível, afinal?

**Proveniência do ASR:** raiz:402, 2026-11-09T10:08:47.820Z. Texto coincide: True; timing elegível: False; bloqueio: `missing_or_uncertain_word_boundaries`.

## Diferença de texto que merece escuta

Na abertura atual, ASR reconheceu um “e” adicional entre verde e outras. Esta diferença impediu aplicação automática do timing. Não é possível atribuí-la com segurança à geração ou ao reconhecedor sem escutar. A tradução inglesa acima preserva o texto planejado. Nos demais planos a comparação nativa de palavras coincide, mas só Marcos teve timing aplicado.

Na última fala, a pergunta termina a 2,62 s segundo ASR, enquanto a legenda mecânica permanece 6,583333 s no plano inteiro. São bases de tempo diferentes; o reconhecimento não prova a pausa nem sua eficácia cômica.
