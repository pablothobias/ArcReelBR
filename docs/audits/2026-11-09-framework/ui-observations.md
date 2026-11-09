# Observações da interface executada

Data: 09/11/2026, America/Sao_Paulo. Observação direta da aplicação em `http://localhost:5173`, pela sessão previamente autenticada do Chrome, em uma aba nova de auditoria. Não houve login, criação de credencial, submissão de projeto, salvamento de configuração ou geração. O formulário novo foi preenchido apenas como rascunho para expor passos condicionais e encerrado com Cancel. Os identificadores numéricos abaixo são os índices de acessibilidade daquela captura, não IDs permanentes de produto.

O navegador isolado das ferramentas Chrome DevTools, em `http://127.0.0.1:5173`, mostrou apenas o formulário de login. Esse resultado não era ausência de sessão em todos os navegadores. A observação autenticada ocorreu depois no Chrome já utilizado pelo usuário. O CLI agent-browser não estava instalado; nenhuma dependência foi instalada. Usou-se CUA como alternativa disponível.

## Criação, formulário não submetido

| Tela observada | Campos e condições verificados |
|---|---|
| New Project, Basics | Project Title; Content Mode sem default (Drama, Narration/Commentary, Ad / Short Video); Aspect Ratio com Portrait 9:16 marcado; Generation Mode sem default (Storyboard to Video, Reference to Video). Mensagem Locked after creation. Next desabilitado enquanto os campos necessários estavam ausentes. |
| Generation, após selecionar ad/storyboard | Target Duration 15/30/60/90/Custom, 60 marcado; Pace optional; Video model, Image model e Text models separados. O texto esclarece que Agent chat e subagent reasoning são configurados no Agent provider. Resolução Default (unset) em imagem/vídeo. |
| Aviso de voz do modelo de vídeo | Style hint informa que a descrição de voz orienta timbre/tom suavemente e não garante consistência entre segmentos. O modelo exibido era MiniMax H3; a observação não substitui auditoria de configuração efetiva nem prova o que foi usado em cada chamada passada. |
| Narration delivery | Post-production voiceover marcado inicialmente. Ao selecionar TTS narration no rascunho, surgiram TTS model, Narration Voice ID e Voice speed optional. Velocidade estava desabilitada com aviso de que o modelo selecionado não a suporta. Cancel descartou o formulário inteiro. |
| Style | Live Action, Animation, Custom. Premium Drama estava marcado como default. O botão final Create Project não foi acionado. |

Há uma lacuna de copy: a ajuda de Pace no projeto novo sem idioma menciona chinês, inglês e vietnamita, sem listar pt-BR. Na tela do projeto brasileiro existente, a unidade exibida é words/sec. O suporte pt-BR deve ser estabelecido pelo contrato e helper, não pela enumeração incompleta da ajuda. Fontes de código: `lib/infra/content_language.py:7-19`; `lib/speech/speech_rate.py:27-56`. Nenhuma correção de copy foi executada.

## Projeto investigado

Base: `/app/projects/br-viral-reuniao-impossivel`.

| Tela | Observação direta e limite |
|---|---|
| Workspace | Título O Especialista: sete linhas vermelhas; Ad / Short Video; 9:16; Short film completed; 1 episode has outputs to update; cinco vídeos gerados; três artefatos mais antigos que o conteúdo atual. O estado completado coexiste com avisos. |
| Settings, Basics | Generation Mode bloqueado em Storyboard to Video; target custom 40 segundos; Pace optional vazio; Save e Discard changes desabilitados. Nenhum campo foi editado. |
| Settings, Voice | Post-production voiceover selecionado. Isso se refere à narração, não significa que o vídeo esteja sem áudio nativo. |
| Characters | Regina, Marcos e Júlio; descrições e imagens atuais. Cena e prop antigos aparecem como cadastros na navegação; existência não comprova uso. |
| Júlio, detalhe | Imagem de asset, regeneração, upload de reference image, Description, Voice Style, Aliases e Derivatives. Derivative é apresentado como outro visual durável, por exemplo troca de figurino, com sintaxe `@[character/derivative]`. |
| Júlio, Optional reference audio expandido | Aviso explícito: projeto usa prompt constraint, portanto áudio de referência não tem efeito; para habilitar, mudar Character voice binding em Settings. Upload WAV/MP3, 2–10 segundos, até 15 MB; botão Generate with TTS. Nenhum upload ou botão de geração acionado. |
| Episode, Shots | Ordem real dos IDs: E1S01, E1S02, E1S05, E1S03, E1S04. Duração total planejada 0:40. Campos Section, Voiceover, References, image/video prompt estruturado ou textual, Composition, Camera and ambient audio, speaker/line de Dialogue. |
| Storyboard e vídeo do shot | Upload, edição de região, versões, regeneração com estimativa; End frame recolhido e Not set. Esses controles foram observados, não executados. |
| Story setting | Synopsis, Genre, Theme e World vazios, com aviso de que a geração utiliza esses dados e alterações podem marcar roteiro antigo. O consumo real para ad/storyboard está demonstrado no anexo workflow-inputs.md; vazios não provam briefing ausente. |
| Edit | Timeline Versão completa; 5 clips; 41.4 segundos; legendas marcadas; trilhas vídeo, narração, legendas e BGM. Issues (0) e No issues. O preview mostrou Unable to play media; não se validou playback audiovisual nessa interface. Não foi acionado Render, Play, edição ou upload de BGM. |

## Cobertura e divergências

Foram observados criação ad/storyboard, condição TTS no rascunho, estilo, settings básicos/voz do projeto, personagem/referência de áudio, shot/prompts, Story setting e timeline. As variações de drama, narration, reference_video, grids, upload de mídia, exportação e revisão por versão foram rastreadas no código, sem simular sua execução na aplicação.

Não confundir essa cobertura com uma inspeção de todas as combinações de formulário. Os defaults observados no wizard pertencem à instância naquele momento; os contratos e heranças completos ficam no inventário de fontes, e a configuração efetiva completa pertence à auditoria paralela.

Issues (0) na edição é um resultado técnico da tela. A própria sessão entregue registra defeito de assentos e ausência de escuta. Logo, essa tela não certifica continuidade, compreensão, humor, atuação ou sincronismo labial.
