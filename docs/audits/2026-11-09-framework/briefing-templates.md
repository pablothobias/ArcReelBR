# Briefings adequados à entrada nativa

Classificação: **recomendação editorial/operacional** baseada nos contratos locais. São mensagens em prosa para o Agent integrado e conteúdo de `brief`, não um novo schema ou formulário obrigatório. Não foram enviados à aplicação. Nada aqui autoriza produção, custo ou regeneração.

Fontes de suporte: `agent_runtime_profile/CLAUDE.ad.md:17-23,118-141`; `agent_runtime_profile/.claude/skills/video-workflow/SKILL.ad.md:13-24,52-59`; inventário [workflow-inputs.md](workflow-inputs.md). O modo ad aceita um briefing criativo livre e retorna roteiro formal diretamente; o arquivo em source deve ser lido e transportado pelo Agent quando necessário.

## O que precisa vir de onde

| Informação | Entrada ou pergunta da entrevista | Consumidor real e responsável |
|---|---|---|
| Objetivo e público | Entrada mínima: o que queremos comunicar e para quem | `brief`; Agent e geração de roteiro. Não há campo audience específico obrigatório. |
| História ou referência | Entrada mínima: material fornecido ou autorização para Agent escolher; se fidelidade for requisito, explicar o que preservar | Conversa, `get_source_text` e depois conteúdo efetivo em `brief`/`instructions`; Agent seleciona e justifica trecho. Upload sozinho não basta. |
| Relação entre personagens, contexto e conflito | Entrada se já definidos; entrevista se vagos; criação pelo Agent quando delegada | `brief`/`overview`, descrições e roteiro. Não exigir ficha preenchida pelo usuário para cada personagem. |
| Preparação, escalada e desfecho | Resultado editorial a exigir; não precisa entregar roteiro pronto | Agent escreve em `shots[]` ou unidades; revisão compara compreensão e arco. |
| O que pode ser localizado e invariantes | Entrada quando fidelidade/continuidade forem essenciais | `brief`; depois descrições, listas de assets, image/video prompts. Notas isoladas não entram na geração. |
| Duração, proporção, língua e destino | Entrada ou preferências já autorizadas; perguntar apenas conflito relevante | `configure_project` e roteiro. Confirmar consumo por capabilities/requests; resolução de exportação é separada da nativa. |
| Referências visuais/vocais | Fornecer se existentes ou se obrigatórias pelo objetivo; deixar ao Agent plano de assets ficcionais quando delegado | `upload_reference` nos tipos suportados; sheets e listas de planos; capabilities e binding. Fotos e áudio humanos não são pré-requisitos universais. |
| Budget e limites da rodada | Autorização do usuário, separada de requisitos criativos | Codex mantém teto e escopo; Agent usa cotações/usage nativas. Este documento não concede autorização. |
| Apresentação PT-BR/inglês | Requisito de inspeção desta experiência, se desejado | Conversa do Agent com leitura do roteiro formal. Tradução fiel em artefato separado; não traduzir projeto canônico. |
| Plano espacial, prompts e escolhas de modelo | Decisões do Agent dentro dos requisitos e capacidades | Assets, storyboards, roteiro, chamadas de geração e revisão; usuário não precisa escrever prompt de câmera. |
| Timeline, legendas, relatório de revisão | Artefatos posteriores | Ferramentas de edição/review existentes. Distinguir medido, mecânico, observado e não avaliado. |

## Briefing mínimo

> Quero um curta [tipo/efeito] para [público], em [idioma], com duração aproximada de [alvo] e formato [destino/proporção]. A história é [situação, quem quer o quê, obstáculo]. Se usar a referência [arquivo/URL], preserve [núcleo], com liberdade para [adaptação]. O vídeo precisa se sustentar para quem não conhece a fonte e terminar em [tipo de resolução ou reação com função clara]. Use o fluxo nativo, complete as escolhas criativas delegadas e identifique lacunas que realmente impedem avançar. Antes dos custos de mídia, apresente o roteiro formal em PT-BR e tradução inglesa fiel, junto com duração estimada e riscos. A autorização de produção será tratada separadamente.

Não exige roteiro, decupagem ou todos os arquivos na entrada. A entrevista serve para resolver objetivo/fidelidade ambíguos; opções técnicas e criação de assets podem permanecer com o Agent.

## Briefing completo

Usar apenas itens relevantes, em conversa ou no texto de `brief`:

1. **Objetivo e público:** emoção/ideia que deve ficar; familiaridade do público com a situação; onde será exibido.
2. **Premissa autossuficiente:** quem participa, o que precisa conseguir, por que importa, qual obstáculo impede e como o conflito termina.
3. **Fonte e fidelidade:** arquivo/URL, trecho candidato, resumo fiel, partes indispensáveis, liberdade de condensação e localização. Dizer se buscamos adaptação fiel de história, premissa inspiradora ou reprodução audiovisual; não misturar esses objetivos.
4. **Mecanismo cômico:** preparação, informação que muda a expectativa, escalada, desfecho e reação; o que precisa ser entendido antes da piada. Humor continua uma hipótese até avaliação.
5. **Personagens e continuidade:** papéis, relações e vozes desejadas; figurino durável; relação física entre assentos, mesa e ambiente; mudanças permitidas. O Agent transforma isso em fichas e prompts.
6. **Referências:** arquivos existentes e sua finalidade: identidade, estilo, ambiente, voz ou movimento. Pedir comprovação do consumo em vez de presumir que upload entra no vídeo.
7. **Restrições técnicas:** língua canônica, proporção, duração flexível ou rígida, áudio nativo/TTS/narração, resolução nativa e final, texto na imagem, legendas e exportação. Não escolher referência de áudio incompatível com a rota.
8. **Critérios observáveis:** o espectador consegue explicar a situação sem consultar a fonte; desfecho responde à preparação; não muda relação física entre personagens; fala possui locutor claro; legendas não antecipam reação; qualidade declarada corresponde à evidência.
9. **Autonomia e entrega:** quais escolhas estão delegadas, orçamento e exclusões autorizados separadamente, roteiro PT-BR/inglês, versões, relatório de limites e arquivos finais.

## Exemplo preenchido para um próximo teste desta história

**Proposta para discussão, não instrução já enviada, roteiro aprovado ou orçamento concedido:**

> Queremos testar uma comédia curta sobre um especialista que é pressionado por cliente e gerente a aceitar especificações contraditórias. Público: pessoas brasileiras que reconhecem reuniões de trabalho, sem pressupor conhecimento de The Expert ou termos geométricos. Objetivo: entender a frustração do técnico e reconhecer a inversão de autoridade, sem confundir absurdo intencional com falha de roteiro.
>
> Fonte: The Expert, Lauris Beinerts, vídeo oficial https://www.youtube.com/watch?v=BKorP55Aqvg, com fonte integral já registrada em source/the-expert-reference.txt. O trecho 00:36.044–01:04.187 é ponto de partida, mas o teste anterior cortou a resposta seguinte. Leia a fonte e proponha um recorte com preparação e fechamento próprios, explicando o que foi retirado. Considere a continuação como candidata, sem assumir que apenas acrescentar sua tradução resolverá o humor brasileiro. Não recrie os atores nem todo o sketch.
>
> Preserve a exigência das linhas vermelhas com condições incompatíveis, a pressão do gerente e a racionalidade contida do técnico. Localize nomes, registro de fala e ambiente. Se abandonar algum elemento anunciado, como perpendicularidade, evite deixá-lo como preparação que promete desenvolvimento inexistente. Pode condensar personagens e estrutura, desde que a relação cliente/gerente/técnico permaneça compreensível. Um encerramento silencioso precisa produzir uma consequência legível; não basta parar numa pergunta.
>
> Personagens ficcionais: Regina é cliente, Marcos é o gerente que promete entregar, Júlio é o técnico. Como invariante espacial proposta, Júlio e Marcos permanecem no mesmo lado comprido da mesa, lado a lado; Regina fica no lado oposto. A ordem física das cadeiras não muda entre planos. Estabeleça uma vista geral ou mapa simples antes dos closes. Não use somente esquerda/direita de tela como definição de assento, pois muda com a câmera. O Agent decide enquadramentos e documenta eixo, olhares e finalidade de cada referência.
>
> Conteúdo canônico, falas e legendas em PT-BR natural; direções técnicas em inglês. Proporção 9:16. Alvo de duração a propor após acomodar fala e reação; 40 segundos do teste anterior é uma referência de escala, não limite rígido para esmagar diálogo. Entrega 1080×1920 deve informar a resolução nativa dos clipes. Vozes por prompt só podem ser declaradas como orientação suave; não alegar clonagem ou consistência comprovada.
>
> Antes de propor mídia, devolva roteiro formal PT-BR, tradução inglesa fiel de todas as falas e contexto, lista de beats e duração estimada. Faça a revisão independente avaliar se um espectador novo sabe quem quer o quê e reconhece um fechamento. Revise todos os keyframes em conjunto para assentos, mesa, câmera, olhares e locutor. Na etapa audiovisual, se vier a ser autorizada, compare as falas efetivas, reporte timing medido versus mecânico e mantenha atuação/sincronismo não avaliados onde não houver evidência. Todo custo depende de autorização nova; nenhuma geração está autorizada por este briefing.

Esse exemplo contém mais contexto do que o mínimo técnico, porque responde aos defeitos encontrados. Não precisa cadastrar novos campos: texto vai para `brief`/conversa, contexto durável pode entrar em `overview`, papéis em descrições, relação espacial em cenário/prompts, e critérios em revisão nativa. Não colocar exigências essenciais só em `note`.

## Variações por caso

| Caso | Acrescentar ao briefing | Fluxo a aproveitar |
|---|---|---|
| Meme/sketch de um vídeo | Situação reconhecível imediatamente, contraste e resposta final, contexto que pode ser omitido sem quebrar compreensão, tempo de reação | Ad sem produtos; uma história completa. Não existe modo meme separado. |
| Minidrama de um vídeo | Desejo, obstáculo, virada, consequência e relações entre personagens | Ad genérico para criação livre; drama com fonte de episódio quando preservar roteiro pronto for prioridade. |
| Série | Arco da obra e de cada episódio, fronteiras, continuidade persistente, entradas/saídas e cliffhanger com função | Drama, fonte completa e plano de episódios; não tentar forçar séries em ad. |
| Narração/documentário | Tese factual, fontes, público, voz fora de cena, o que imagens devem demonstrar | Narration; não inventar diálogo de personagens em substituição à narração. |
| Anúncio | Produto, originais e fidelidade indispensável; promessa, público e chamada final | Ad com produtos e checkpoints comerciais existentes. Não exigir esses itens para sketch. |
| Adaptação de referência audiovisual | Qual aspecto da referência importa, obra completa versus recorte, acesso e limites de análise, invariantes narrativos versus estilo | Agent lê a fonte e a transpõe; reference_video não é um importador automático de YouTube. |

## Apresentação bilíngue sem gate inventado

Formato sugerido por plano: papel/contexto; ação relevante; fala canônica PT-BR; tradução inglesa fiel; duração planejada; pausa pretendida; risco ou mudança da fonte. Após gerar, acrescentar fala reconhecida separada da planejada e indicar se houve escuta.

Uma autorização autônoma pode permitir ao Agent avançar após revisão nativa, sem esperar aceite humano obrigatório. Se a rodada for de inspeção de roteiro, a parada antes da mídia deriva do escopo autorizado daquela rodada. Exibir PT-BR e inglês não equivale a obter aprovação humana, nem garante compreensão ou humor. O arquivo [script-pt-en.md](script-pt-en.md) demonstra o formato usando o roteiro realmente produzido, sem reescrevê-lo.
