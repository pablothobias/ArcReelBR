# Fontes oficiais online: framework e limites dos modelos

Consulta: **2026-11-09**, somente leitura pública. Nenhuma inferência, geração ou chamada paga foi executada. Este anexo distingue documentação upstream de comportamento local. Não inspeciona a execução da rodada nem confirma quais referências foram efetivamente enviadas.

## Proveniência e versão

**Comprovado:** o upstream público é [ArcReel/ArcReel](https://github.com/ArcReel/ArcReel), cujo README aponta para `docs.arc-reel.com`. Seu `main` foi identificado pela API pública do GitHub como `9524340d476047385124a729fdc5a6d61279bf30`, commit de `2026-11-09T11:42:40Z`. [README inglês fixado nesse commit](https://github.com/ArcReel/ArcReel/blob/9524340d476047385124a729fdc5a6d61279bf30/README.en.md). As páginas do site e dos provedores são mutáveis e não foram atribuídas a esse SHA.

O `origin` local é `pablothobias/ArcReelBR`. A distinção também consta de `README.en.md:2` e `docs/independent-maintenance.md:3,30-37`. Uma capacidade ou recomendação upstream não prova presença, consumo ou uso na aplicação local.

## Fluxo e revisão documentados pelo upstream

**Comprovado documentalmente, não validado localmente:** [Workflows and Modes](https://docs.arc-reel.com/en/guide/workflows/), seções 1-8 e 10, separa modo de conteúdo de geração. Drama abrange narrativa dialogada e seriada; não há modo dedicado de humor nessa taxonomia. Roteiro pronto deve preservar falas sempre que possível. Storyboard-to-video usa uma imagem e limita principalmente o início; personagens podem mudar durante movimento. Reference-to-video fornece assets diretamente, dependendo do provedor. Multi-grid é etapa de imagem, posteriormente dividida em imagens individuais para vídeo. O fluxo recomenda metas, estrutura, assets, amostra, lote, controle e exportação. Revisão de drama inclui arco completo, relações espaciais, olhares e alinhamento fala/duração. Consistência exige orientação do ambiente e posições dos personagens. Revisões devem corrigir conteúdo e amostras antes de ampliar geração. Isso é orientação upstream, não evidência de que a rodada cumpriu essas verificações.

O [Complete Getting Started Guide](https://docs.arc-reel.com/en/guide/getting-started/), seções “Estimated Time and Cost” e “Agent Credentials”, recomenda uma primeira amostra de 2-4 planos e atribui ao Agent entendimento, planejamento, estruturação e orquestração. Não apresenta aprovação de resultado audiovisual como consequência automática de status concluído.

O [Provider and Model Configuration](https://docs.arc-reel.com/en/guide/providers/), seções 1, 3.2 e 7, distingue Agent de provedores de mídia. Parâmetros suportados pelo canal podem divergir do catálogo do modelo, inclusive duração, resolução e último quadro. A interface unificada não elimina essas diferenças. **Recomendação operacional:** auditar endpoint e payload efetivos, além do nome do modelo e dos campos visíveis.

O [Jianying Draft Export](https://docs.arc-reel.com/en/guide/jianying-export/), introdução e etapa 2, documenta que cortes e exportações usam a mesma timeline; renderizar não cria automaticamente essa timeline. Compatibilidade do draft com CapCut permanece não verificada pelo upstream.

## Exemplos, demonstrações e discussões

O [README upstream fixado](https://github.com/ArcReel/ArcReel/blob/9524340d476047385124a729fdc5a6d61279bf30/README.en.md), seção “Showcase”, publica três episódios da mesma obra chinesa. **Comprovado:** existem exemplos seriados apresentados pelo projeto. **Não verificado:** não reproduzi integralmente esses vídeos com áudio; nenhum benchmark de humor brasileiro, adaptação autossuficiente de sketch ou continuidade impecável pode ser inferido da vitrine.

Na [discussão upstream #2434](https://github.com/ArcReel/ArcReel/discussions/2434), aberta em 2026-09-11, um usuário pergunta como produzir prompts específicos para MiniMax H3. A consulta mostrou “Unanswered” e zero comentários. Isso registra uma pergunta pública, sem resposta oficial utilizável. A [listagem de discussões](https://github.com/ArcReel/ArcReel/discussions) carregou parcialmente com mensagens de erro; a pesquisa não pretende ser exaustiva.

## MiniMax H3: modelo e canal são contratos diferentes

**Comprovado para API direta MiniMax:** [Video Generation](https://platform.minimax.io/docs/guides/video-generation), seções “Supported Generation Modes” e “Input Requirements”, distingue texto, primeiro/último quadro e referência multimodal. A referência pode orientar personagem, movimento, câmera, estilo, voz e ritmo. Limites publicados incluem até nove imagens, três vídeos e três áudios, com máximo agregado de 12 arquivos. Vídeos e áudios somam até 15 segundos em cada modalidade. O H3 base oferece 768P/2K e duração inteira de 4-15 segundos.

O contrato de [Create Video Generation Task](https://platform.minimax.io/docs/api-reference/video-generation-v2-create), campos `content` e `ratio`, exige prompt e discrimina `first_frame`, `last_frame`, `reference_image`, `reference_video`, `reference_audio`. **Primeiro/último quadro e referências são mutuamente exclusivos nesse endpoint.** Em image-to-video, a proporção deriva da imagem e outro valor de `ratio` é ignorado. Em reference-to-video, pode ser explícita. Isso não prova que o adaptador ArcReelBR usa esse endpoint ou suporta todos esses papéis.

**Comprovado para a página pública Metaso:** [MiniMax H3](https://metaso.cn/minimax-h3), seções de materiais e especificações, anuncia até nove imagens e referências de vídeo/áudio; anuncia 480p, 768P e 1080p até 30 segundos, e 2K até 15 segundos. Portanto diverge da API MiniMax direta quanto às opções disponíveis. O botão API não forneceu contrato textual nesta leitura; o [tutorial Metaso](https://metaso.cn/minimax-h3/guide) retornou extração mínima e depois timeout. **Não verificado:** payload público completo Metaso e garantia de equivalência entre seus modos e os papéis MiniMax.

**Limite de inferência:** suporte a referência/voz e publicidade de sincronismo não certificam fidelidade de cada fala, atuação, sincronismo labial, humor ou continuidade do teste. As páginas consultadas não fornecem uma taxa aplicável de falha espacial ou de fala PT-BR para esta produção.

## Gemini 3.1 Flash Image

**Comprovado no contrato atual:** a [ficha do modelo](https://aistudio.google.com/docs/models/gemini-3.1-flash-image), seção do modelo, identifica `gemini-3.1-flash-image` como Nano Banana 2, com entrada texto/imagem/vídeo/PDF e saída imagem/texto. Nano Banana Pro designa Gemini 3 Pro Image, não esse identificador.

O [guia de geração de imagem](https://ai.google.dev/gemini-api/docs/image-generation), seções “Use up to 14 reference images”, “Best Practices” e “Limitations”, publica até 14 referências, com até quatro personagens e dez objetos nesse modelo. A geração de imagem não aceita áudio. Recomenda contexto, intenção, descrição específica, câmera e iteração; isso melhora controle, sem garantir resultado correto. **Não verificado localmente:** quantas referências e quais bytes chegaram ao modelo em cada storyboard.

O [model card oficial](https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-1-Flash-Image-Model-Card.pdf), página 6 do PDF, seção “Known Limitations”, admite consistência imperfeita entre personagem de entrada e saída, confusão ocasional de localização espacial como esquerda/direita, e limites de raciocínio 3D. **Hipótese parcial:** são mecanismos tecnicamente plausíveis para um keyframe errado. Não demonstram que o modelo causou o defeito específico de Júlio; é necessário localizar a primeira divergência entre referências, prompt, keyframe e clipe.

**Divergência documental:** a página 2 do mesmo PDF descreve multimodalidade incluindo áudio, mas sua lista de entradas é texto/imagens e diverge em limites de contexto da ficha atual. Para determinar entradas aceitas pelo endpoint, prevalece nesta análise o contrato atual da API, não uma descrição geral do modelo. Nenhum desses documentos certifica performance audiovisual de vídeo gerado por H3.

## Limites da coleta e uso na conclusão

O navegador de pesquisa não conseguiu interpretar algumas respostas Google com `Content-Type: text/markdown`. A leitura pública por `curl -L --fail --silent` recuperou a ficha em `aistudio.google.com` e o guia Google em Markdown, confirmando os trechos citados. O acesso inicial a `/en/guide/introduction` falhou; foram usadas páginas oficiais navegáveis ligadas pelo README. Não houve login nem criação de credenciais.

**Resposta limitada ao escopo online:** as fontes oficiais não permitem concluir que o insumo foi o principal gargalo. Sustentam investigar em paralelo estrutura narrativa, seleção/consumo das referências, limitações espaciais de imagem, drift no vídeo e abrangência da revisão. As causas e sua importância relativa dependem da evidência local da rodada. Nenhum teste pago é necessário para primeiro comparar esses artefatos existentes.
