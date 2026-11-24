# Altair + ChatGPT — versão de testes Windows

## Instalação e primeiro login

1. Baixe e extraia o ZIP da branch altair-chatgpt-hybrid ou clone a branch com Git.
2. Instale Python 3.10 x64 se ainda não estiver instalado.
3. Execute instalar_hybrid.cmd. Instala dependências e baixa o modelo Whisper base para uso offline posterior. Precisa de internet nesta etapa. Para omitir o download, execute install_hybrid.ps1 -SkipVoice.
4. Execute iniciar_hybrid.cmd. O perfil de teste fica em %LOCALAPPDATA%\Altair-Hybrid; o Altair original fica separado.
5. Em Menu > Privacidade e dados, autorize serviços externos se desejar usar ChatGPT.
6. Em API e modelos, clique Continue with ChatGPT. Confira que o uso de créditos extras está desabilitado na conta em https://chatgpt.com/settings/usage e, depois do registro, confira também os controles do agente. Autorize no navegador, consulte e selecione um modelo da conta e aplique.
7. Em Configurar Voz, selecione windows_local e reconhecimento local. Use o microfone do Altair e as vozes instaladas do Windows. Se necessário, adicione uma voz portuguesa nas configurações do Windows.
8. Abra o companheiro visual do ChatGPT nas configurações de IA. Pode abrir o ChatGPT oficial em janela separada e usar o modo de voz oficial, ou enviar comandos ao Altair local. O avatar reage ao volume de todos os sons do PC somente se habilitado.

Não precisa gerar API Key da OpenAI. O uso está sujeito à elegibilidade, permissões, franquia e configuração de créditos da conta; o código não compra créditos automaticamente nem pode verificar programaticamente a cobrança. Outros provedores são opcionais e podem cobrar.

## Recursos desta versão no código

- OAuth oficial de registro dinâmico com loopback, PKCE, state, nonce e validação do ID token.
- Sessão protegida localmente com DPAPI no Windows, renovação e tentativa de revogação ao desconectar. Um registro local de conta; não compartilhar tokens ou cookies.
- Modelos da conta e inferência via Responses pública com SSE. Sem fallback automático para outro provedor pago.
- Memória local opcional separada por registro; importação manual de resumo .txt/.md de até 12.000 caracteres, até seis pares de conversa, opção de apagar.
- Whisper local, sem fallback remoto quando modo local selecionado; voz local System.Speech do Windows. O modelo é baixado uma única vez pelo setup_voice.ps1.
- Avatar vetorial flutuante, olhos animados, boca por amplitude sonora, indicador de processamento, atalho para ChatGPT oficial, campo de comandos para o Altair e botão de parar fala.
- Captura da tela principal com prévia e envio confirmado pelo usuário ao modelo compatível; não grava imagem em disco nem captura continuamente.
- Diagnóstico de CPU, RAM e disco; inspeção local do Git somente leitura (status, log e diff --stat).
- Atalho para abrir o executável oficial Codex CLI já instalado no PATH, na pasta selecionada, em sandbox workspace-write e aprovação on-request. Codex usa sua própria sessão; não usa os tokens do Altair. Não faz push automaticamente.
- Instalador por script e launcher; receita de build do instalador EXE.

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
