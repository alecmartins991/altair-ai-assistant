# Altair + ChatGPT — versão de testes Windows

## Instalação e primeiro login

1. Baixe e extraia o ZIP da branch altair-chatgpt-hybrid ou clone a branch com Git.
2. Instale Python 3.10 x64 se ainda não estiver instalado.
3. Execute instalar_hybrid.cmd. Instala dependências e baixa o modelo Whisper base para uso offline posterior. Precisa de internet nesta etapa. Para omitir o download, execute install_hybrid.ps1 -SkipVoice.
4. Execute iniciar_hybrid.cmd. O perfil de teste fica em %LOCALAPPDATA%\Altair-Hybrid; o Altair original fica separado.
5. Na primeira abertura o assistente oferece configuração guiada do ChatGPT. Autorize o envio de dados à OpenAI se desejar; a voz local não exige esta autorização.
6. Em API e modelos, clique Continue with ChatGPT. Confira que o uso de créditos extras está desabilitado na conta em https://chatgpt.com/settings/usage e, depois do registro, confira também os controles do agente. Autorize no navegador, consulte e selecione um modelo da conta. Use Testar resposta do ChatGPT para uma solicitação curta opcional e depois aplique.
7. Em Configurar Voz, selecione windows_local e reconhecimento local. Use o microfone do Altair e as vozes instaladas do Windows. Se necessário, adicione uma voz portuguesa nas configurações do Windows.
8. Abra o companheiro visual do ChatGPT nas configurações de IA. Pode abrir o ChatGPT oficial em janela separada e usar o modo de voz oficial, ou enviar comandos ao Altair local. O avatar reage ao volume de todos os sons do PC somente se habilitado.

Não precisa gerar API Key da OpenAI. O uso está sujeito à elegibilidade, permissões, franquia e configuração de créditos da conta; o código não compra créditos automaticamente nem pode verificar programaticamente a cobrança. Outros provedores são opcionais e podem cobrar.

## Recursos desta versão no código

- OAuth oficial de registro dinâmico com loopback, PKCE, state, nonce e validação do ID token.
- Sessão protegida localmente com DPAPI no Windows, renovação e tentativa de revogação ao desconectar. Um registro local de conta; não compartilhar tokens ou cookies.
- Modelos da conta e inferência via Responses pública com SSE. Sem fallback automático para outro provedor pago. Erros de franquia pausam novas inferências nesta instância; depois de verificar a franquia, reabra a configuração e aplique o provedor novamente. Revogação de refresh token exige novo login.
- Memória local opcional separada por registro; importação manual de resumo .txt/.md de até 12.000 caracteres, até seis pares de conversa, opção de apagar.
- Whisper local, sem fallback remoto quando modo local selecionado; voz local System.Speech do Windows. O modelo é baixado uma única vez pelo setup_voice.ps1.
- Avatar vetorial flutuante, olhos animados, boca por amplitude sonora, indicador de processamento, atalho para ChatGPT oficial, campo de comandos para o Altair e botão de parar fala.
- Captura da tela principal com prévia e envio confirmado pelo usuário ao modelo compatível; não grava imagem em disco nem captura continuamente.
- Diagnóstico de CPU, RAM e disco; inspeção local do Git somente leitura (status, log e diff --stat).
- Atalho para abrir o executável oficial Codex CLI já instalado no PATH, na pasta selecionada, em sandbox workspace-write e aprovação on-request. Codex usa sua própria sessão; não usa os tokens do Altair. Não faz push automaticamente.
- Instalador por script, configuração guiada no primeiro uso, launcher e receita de build do instalador EXE. O launcher Python impede duas instâncias do Altair no mesmo usuário Windows; feche o Altair antigo antes de testar.

## Testes e build

No Windows com as dependências instaladas, execute test_hybrid.ps1. O script verifica os testes mockados de OAuth, streaming, memória, reconhecimento local, imagens e Git, sem usar uma conta real.

Para gerar o EXE execute build_hybrid_installer.ps1 em uma cópia limpa do repositório. Ele regenera o bundle de dependências e chama o empacotador original. Saída prevista: dist/AltairInstaller.exe. O download inicial do modelo de voz não está incluído no EXE; setup_voice.ps1 prepara o modelo. O método recomendado para esta primeira validação é instalar_hybrid.cmd seguido de iniciar_hybrid.cmd.

## Limites e validações pendentes

Esta branch experimental ainda não passou por execução de testes, instalação, compilação do EXE ou autenticação em Windows real; o ambiente remoto não consegue resolver github.com por DNS. O login e o catálogo dependem de disponibilidade do serviço e do modelo; não anunciar integração homologada antes de testar. Verificar também DPAPI, refresh, revogação, erros de limite, voz, áudio WASAPI, permissões e atalhos Codex.

A sessão oficial do ChatGPT não disponibiliza automaticamente seu histórico, memória, voz nativa ou comandos ao Altair. A janela complementar não lê o navegador nem sincroniza chats. O avatar é vetorial 2D estilizado, não um rosto 3D realista. A análise visual é sob demanda, não monitoramento contínuo. O controle operacional depende das automações existentes do Altair e do Codex instalado. Não existe ponte automática para a sessão oficial de voz controlar Windows via Altair. Não há controle irrestrito de mouse/teclado, execução automática de shell por texto retornado pelo modelo ou multi-conta completa; não confundir essas limitações com recursos implementados.

Confira a licença original antes de redistribuir.

Referências oficiais:
- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations

## Atualização de instalação existente: correção do login

Feche o Altair. Baixe a branch atualizada, extraia em uma pasta temporária e copie a pasta src e o arquivo reparar_login.cmd para a raiz da instalação anterior (onde estão iniciar_hybrid.cmd e .venv), substituindo os arquivos quando solicitado. Execute reparar_login.cmd, que verifica dependências JWT, certificados, DPAPI e sintaxe sem solicitar sua chave ou conta. Abra iniciar_hybrid.cmd e refaça o login. A janela de configuração agora mostra as etapas de falha da autenticação e os controles de confirmação visíveis. Nunca copie códigos da URL de retorno, tokens ou senhas em mensagens de suporte. Os novos testes de regressão foram adicionados, mas ainda não executados em Windows real.

## Correção de estabilidade de áudio

Feche o Altair, extraia o ZIP atualizado e copie a pasta src e o arquivo run_altair.py para a instalação Hybrid existente, substituindo os arquivos. Não substitua .venv, configs, data ou o perfil em %LOCALAPPDATA%. Não é necessário refazer o login. Abra iniciar_hybrid.cmd. Em Configurar Voz, selecione windows_local e local para evitar uso de APIs de voz pagas. Teste primeiro uma mensagem digitada com a voz ativada e depois o microfone. A captura e a transcrição rodam em um subprocesso descartável por trecho; a resposta por voz local roda em PowerShell e a reprodução ElevenLabs opcional em subprocesso Python separado. A captura é interrompida enquanto a fala usa o dispositivo. O fluxo de comandos de voz usa o mesmo serviço da conversa digitada. Falhas recuperáveis são informadas em texto. O medidor de intensidade do microfone não recebe amostras ao vivo nesta versão isolada e a inicialização do Whisper por trecho pode aumentar a latência. O modo isolado pressupõe a instalação Python Hybrid, não um executável congelado.

Diagnóstico: %LOCALAPPDATA%\\Altair-Hybrid\\logs\\audio-stability.log. Registra etapas, códigos de saída, categorias de falha e stack de falhas nativas, sem gravar texto das conversas ou amostras de áudio. Antes de enviar um trecho do log, confira se não contém caminhos privados. Os testes mockados em tests/test_audio_isolation.py não substituem o teste real no Windows. A causa nativa exata do fechamento original não foi comprovada.

## Atualização da qualidade de voz e transcrição

Feche o Altair. Extraia o ZIP atualizado e copie para a instalação existente a pasta src, a pasta scripts, requirements-voice-local.txt e atualizar_voz.cmd, substituindo os arquivos. Preserve .venv, data, configs e o perfil LocalAppData. Execute atualizar_voz.cmd para instalar as bibliotecas e baixar Whisper Large V3 Turbo e Kokoro 1.0. O instalador faz um teste de síntese em português com as três vozes. Não usa conta ChatGPT nem API Key. Reserve alguns GB livres e conexão durante o download inicial. Depois, em Configurar Voz, selecione kokoro_local, local, large-v3-turbo, cpu, voz Alex/Santa/Dora, velocidade 1.0 e pausa 1.8s. Escolha CUDA somente se a GPU NVIDIA e as bibliotecas exigidas pelo CTranslate2 estiverem instaladas. Para baixar o modelo small, use scripts/setup_voice.ps1 -Whisper small. Base permanece disponível para hardware modesto.

O reconhecimento transcreve português sem traduzir para inglês, usa vocabulário personalizável, pré-captura, limiar adaptativo, normalização de volume e detecção de pausas. Os modelos permanecem carregados em processos isolados quando possível; cancelamentos ou falhas encerram somente o worker, que é recriado na próxima solicitação. O áudio neural é sintetizado e reproduzido em trechos de uma resposta já recebida; não há streaming simultâneo dos tokens do ChatGPT nem interrupção por voz enquanto o microfone está suspenso. O botão Parar fala continua disponível. As melhorias do avatar limitam-se ao medidor de áudio já existente, sem sincronização labial por fonemas. A qualidade real, os tempos de resposta, a instalação das dependências e os testes de regressão ainda precisam de validação no Windows. Nenhuma alteração no login ou no mecanismo de cobrança ChatGPT.

## Altair Live — ligação

Atualize a pasta src do ZIP da branch altair-chatgpt-hybrid na instalação existente, mantendo .venv, configs, data e o perfil LocalAppData. Não há nova API nem troca de voz; se os modelos locais já foram instalados, não é necessário baixá-los novamente. Abra iniciar_hybrid.cmd e clique no microfone (Iniciar ligação Altair Live). Fale normalmente, sem palavra de ativação. O painel mostra fases, transcrição provisória e resposta progressiva. O texto provisório pode mudar; somente o texto final é enviado. O botão Interromper cancela a resposta e a fala pendente; o microfone encerra a ligação. Com fones, marque a opção de interrupção pela voz; não use esse modo com alto-falantes. A captura permanece isolada em um processo Python residente e as respostas de conversa comum usam uma única requisição SSE do plano ChatGPT. Comandos explícitos continuam passando pelo serviço existente; solicitações indiretas podem ser interpretadas como conversa. O contexto da ligação existe em RAM mesmo com memória persistente desativada. Quando a memória local está ativada, respostas completas do ChatGPT também são salvas conforme as configurações existentes.

A captura usa o formato padrão do dispositivo se 16 kHz não for suportado, pré-rolagem de 300 ms, limiar adaptativo, janelas de transcrição sobrepostas e apenas uma decodificação pendente. O detector de fim de fala normalmente espera cerca de 0,7 s e prolonga a espera para alguns conectores de frases. Na CPU, prioriza Whisper Small ou Base já instalados, com Turbo como alternativa; CUDA é tentada se configurada. Não promete transcrição instantânea: a latência depende da máquina. O worker é aquecido antes da captura inicial e reutilizado entre turnos, salvo cancelamentos ou falhas. A fala é dividida em frases e começa assim que o streaming produz um trecho. O modo com fones abre uma captura paralela e tenta cancelar a geração ao detectar nova fala. O cancelamento de rede é cooperativo e pode aguardar o próximo evento SSE; ações locais já executadas não podem ser desfeitas. Não existe cancelamento acústico real de eco validado, por isso o modo padrão com alto-falantes é semiduplex. Não há supressão neural dedicada de ruído nem sincronização labial fonética nova. Falhas de microfone têm tentativas limitadas de recuperação; após falhas de rede, a próxima fala inicia uma nova requisição sem repetir silenciosamente o envio anterior. O log audio-stability.log registra categorias, tempos e falhas sem texto de conversa. As metas de latência e a qualidade do reconhecimento precisam ser verificadas no Windows; testes mockados estão em tests/test_live_conversation.py, ainda não executados no ambiente de edição.

### Revisão de estabilidade do Altair Live — 24/11/2026

A captura agora aceita cancelamento cooperativo pelo protocolo do worker e mantém o Whisper aquecido quando o cancelamento termina normalmente; se não terminar em 1 s, o supervisor encerra somente o worker. A seleção do reconhecedor considera primeiro o modelo configurado e um benchmark local sintético antes de tentar modelos menores. A transcrição final usa VAD e busca um pouco mais cuidadosa quando uma nova decodificação final é necessária. A leitura SSE Live é isolada em thread com fila limitada; o turno pode ser liberado ao cancelar, enquanto a conexão antiga se encerra no próximo evento ou timeout. Não há retry automático de solicitações faturáveis. Desligar a voz interrompe a reprodução, e o fechamento da janela solicita parada de áudio. A inicialização preserva o arquivo de diagnóstico de falhas nativas.

Validação executada em ambiente Linux sem acesso DNS ao GitHub, usando cópias locais dos arquivos recuperados pelo conector: live_conversation.py (blob 11d4b6c1c8b41b2e2b8ba7a6ecf3bf00775d584a) e live_capture.py (blob 54bb3ddd79376cfe9291991fb9d1661797b33a71), ambos conferidos por git hash-object e py_compile. Cinco cenários de conversação e quatro de captura simulada passaram; três testes adicionais do método _live_request copiado isoladamente, com rede simulada, também passaram (12 cenários ao todo). Não foi executada a suíte integral, nem renderizada a interface Qt, nem usado microfone físico, modelos Whisper/Kokoro ou a conta do proprietário. Testes de captura e rede adicionados à suíte test_hybrid.ps1. Cancelamento acústico de eco com alto-falantes e supressão neural de ruído não foram validados/implementados como recursos dedicados; use modo fones para interrupção por fala. Não afirmar equivalência ou latência real do ChatGPT Voice antes do teste de ponta a ponta no Windows.


### Fechamento da revisão de áudio

A entrada Live remove componente DC para detectar fala, aprende ruído de fundo de baixa amplitude e aplica atenuação espectral conservadora por sobreposição de janelas, sem serviço externo ou novo pacote. Não é um denoiser neural nem cancelador acústico de eco. A pausa é adaptada ao texto provisório e ao ajuste local; o limite de uma única fala passa a 60 segundos, não um limite da ligação. A captura também aceita a entrada padrão estéreo quando mono não é suportado, exibe o nome do dispositivo e sinaliza interrupções de entrega de frames. Durante o raciocínio, mesmo com alto-falantes, pode ouvir uma correção antes da reprodução; ao começar a falar, suspende a captura, evitando realimentação. Durante a reprodução, a interrupção falada continua disponível somente no modo com fones. Cancelamento da fala verifica o estado do turno novamente antes de tocar cada trecho.

Atualização: feche o programa, copie a pasta src e, opcionalmente, verificar_live.cmd do ZIP para a instalação Hybrid existente. Não sobrescreva a .venv nem os dados/configurações. verificar_live.cmd compila o código local, confere modelos/dependências e formato da entrada padrão, sem gravar áudio ou consultar o ChatGPT. Abra iniciar_hybrid.cmd como antes. Não é necessário reinstalar os modelos existentes ou renovar o login.

Validação desta revisão: 18 cenários locais aprovados via pytest, incluindo os 12 cenários isolados anteriores, 5 testes de redução de ruído/limiar/pausa e 1 captura estéreo simulada. Os blobs live_capture.py 3573c5160891c454193b2cd5d215fb507bc26202, live_dsp.py e31e0e97b2ccf9b71bef8be8719991637db547ec e test_live_dsp.py 331d6e3ecda59c75476edc056217d448ad7d3303 foram conferidos por hash com as cópias executadas. A compilação desses dois módulos também passou. Não foi possível clonar o repositório por DNS neste ambiente, executar a suíte integral ou testar a UI, microfone e modelos reais em Windows. A pré-checagem Windows foi adicionada, não executada. Não declarar AEC, supressão neural ou latência real como concluídos sem validação.
