# Altair + ChatGPT — integração híbrida experimental

## Executar no Windows

Esta branch preserva a main e os provedores atuais. Use uma cópia local de teste:

```powershell
git clone --branch altair-chatgpt-hybrid https://github.com/alecmartins991/altair-ai-assistant.git altair-hybrid
cd altair-hybrid
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_altair.py
```

1. Em Menu > Privacidade e dados, permita serviços externos se desejar usar o modelo.
2. Abra a configuração de API e modelos e selecione Continue with ChatGPT.
3. Confira em https://chatgpt.com/settings/usage que créditos adicionais estão desativados para o app. A confirmação local não controla nem verifica a cobrança na conta. Depois de registrar o app, confira de novo as permissões específicas dele antes de realizar inferência.
4. Autorize no navegador, escolha um modelo do catálogo da conta e aplique. Não cole tokens ou cookies.
5. Opcional: habilite memória local e importe um resumo .txt/.md de até 12.000 caracteres. O contexto é enviado ao modelo somente quando a memória estiver habilitada. Até seis pares recentes de conversa são mantidos, com limite por mensagem. Desative ou apague nas configurações.
6. Para a experiência visual com o ChatGPT oficial, abra o companheiro visual e clique em Abrir ChatGPT oficial. Inicie a conversa de voz no ChatGPT, se disponível na conta. Habilite opcionalmente o medidor de áudio do computador.

## O que está implementado no código

- OAuth de registro dinâmico, callback de loopback, PKCE, state, nonce e validação OIDC/JWKS.
- Credenciais fora do repositório, protegidas por DPAPI no Windows; arquivos com permissão restrita em Unix. Um registro local nesta versão experimental, renovação de sessão e tentativa de revogação ao desconectar.
- Catálogo de modelos da conta e inferência via Responses SSE pública, sem API key e sem fallback automático para outro provedor pago.
- Integração com o roteamento existente do Altair.
- Memória local opt-in separada por registro, com importação manual.
- Companheiro flutuante com rosto simples, atalho para ChatGPT oficial e animação por nível de áudio do sistema. O áudio não é gravado em disco, transcrito ou enviado pelo medidor. Não identifica especificamente áudio do ChatGPT.
- Testes offline com mocks em tests/test_chatgpt_plan.py.

## Limites e validação pendente

Não há sincronização de conversas, histórico, memórias, voz nativa ou comandos entre a sessão oficial do ChatGPT e o Altair. O companheiro é visual e não lê a sessão do navegador. Para conversar dentro do Altair é usado o provedor de plano; o reconhecimento de fala existente ainda depende de serviço remoto. Piper pode gerar fala local quando configurado. O reconhecimento de voz offline, integração de ferramentas externas com a sessão ChatGPT, avatar avançado, múltiplas contas, bloqueio de múltiplos processos para rotação de token e instalador atualizado ainda não estão implementados.

O uso do plano está sujeito à elegibilidade, autorização, limites e configuração de créditos da conta. Não é possível garantir ausência de cobranças se o usuário permitir créditos pagos. Nenhuma compra de créditos é realizada pelo código. Não há verificação programática do estado da cobrança.

Os testes foram adicionados, mas não executados no ambiente de desenvolvimento remoto. Antes de mesclar, executar testes, verificar instalação/Qt/DPAPI no Windows, login real, autorização negada, revogação, expiração, limite de uso, privacidade e áudio WASAPI. O bundle offline do instalador ainda precisa incluir as novas dependências. Verificar licença do projeto original antes de redistribuir.

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest tests/test_chatgpt_plan.py -q
```

Documentação oficial:
- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
