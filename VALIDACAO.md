# Validação da versão GPT-6

Verificado em 26/09/2026 com Windows e Python 3.12.

- `python -m unittest discover -s tests -v`: seis testes passaram; um teste
  de links simbólicos foi omitido porque o Windows não permitiu criar o link.
- Instalação pela CLI em `dist/verification-home`: prévia sem alterações,
  instalação, `doctor` e repetição sem novas gravações passaram.
- Validador da skill: `Skill is valid!`.
- Fluxo de pacote e recibo: criação, validação, resumo e rejeição de evidência
  de outro candidato passaram.
- Roteamento: escalada para Sol, ausência de capacidade, capacidade de um
  agente e ondas limitadas pelos slots disponíveis passaram.

O pacote não contém credenciais ou caminhos pessoais. Os agentes e a skill
foram adaptados da instalação local existente. A mudança substitui a escalada
Terra por Sol e acrescenta instalação portátil, documentação e testes.

Não foi iniciado um trabalho real de Sol/Luna no Codex de destino. Acesso aos
modelos, descoberta dos agentes e opções efetivas da nova sessão precisam ser
confirmados naquele ambiente. Não foram executados testes em macOS ou Linux
nesta sessão.
