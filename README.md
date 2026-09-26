# Sol/Lunas com GPT-6 para Codex

Orquestração portátil: **GPT-6 Sol** coordena, integra e aceita o resultado;
**GPT-6 Luna** executa tarefas delimitadas de exploração, implementação,
revisão e testes. Casos ambíguos e correções que falham voltam ao Sol.

## Instalar no outro Codex

Requisitos: Python 3.11+, Git e Codex atualizado com acesso a `gpt-6-sol` e
`gpt-6-luna`. A instalação não concede acesso aos modelos nem troca o modelo
de uma conversa já aberta.

No terminal do outro computador (Windows, macOS ou Linux):

```sh
git clone https://github.com/educamosonline/codex-sol-luna-orchestrator.git
cd codex-sol-luna-orchestrator
python scripts/install.py
python scripts/install.py --apply
python scripts/install.py doctor
```

Use `python3` se esse for o nome do Python no seu sistema. O repositório é
privado: autentique o Git com uma conta que tenha acesso, ou transfira o ZIP,
extraia e execute os mesmos comandos a partir da pasta extraída.

O primeiro comando mostra a prévia sem alterar arquivos. Se houver arquivos
existentes diferentes, revise a prévia e use:

```sh
python scripts/install.py --apply --replace
python scripts/install.py doctor
```

As substituições criam backup em `backups/sol-luna-orchestrator/` dentro do
diretório do Codex. Um manifesto registra os hashes instalados. Repetir a
instalação sem mudanças não escreve novos arquivos.

O destino padrão é `~/.codex`, respeitando `CODEX_HOME` quando definido.
Para outro destino, passe `--codex-home CAMINHO` em **todos** os comandos.
O instalador copia apenas a skill e cinco agentes; não modifica `config.toml`,
`AGENTS.md`, autenticação, plugins ou outros agentes. O exemplo
[`config.example.toml`](config.example.toml) contém ajustes opcionais.

## Iniciar e usar

Abra uma nova conversa no Codex e selecione **GPT-6 Sol**, ou inicie o CLI:

```sh
codex -m gpt-6-sol
```

Cole este pedido:

```text
Use $sol-luna-orchestrator para executar esta tarefa com GPT-6 Sol na
coordenação e GPT-6 Luna nos agentes. Confira os modelos e a capacidade
disponíveis. Delegue escopos delimitados, preserve alterações existentes,
valide as evidências e integre o resultado antes da aceitação final.

Tarefa: [descreva aqui]
Critério de conclusão: [resultado verificável]
```

Se algum modelo não estiver disponível, pare a delegação e informe a limitação;
não substitua silenciosamente por GPT-5.6. Confira se os agentes abaixo aparecem
nas ferramentas da nova sessão. `doctor` valida arquivos e algumas opções
locais; não comprova acesso à conta, carregamento no app ou uma execução real
dos modelos. Configurações de projeto podem sobrepor as opções globais.

| Agente | Modelo | Esforço | Responsabilidade |
| --- | --- | --- | --- |
| Principal (selecionado no Codex) | `gpt-6-sol` | Conforme a tarefa | Planejar, integrar, escalar e aceitar |
| `luna_scout` | `gpt-6-luna` | medium | Mapear código sem editar |
| `luna_worker` | `gpt-6-luna` | max | Implementar dentro dos arquivos atribuídos |
| `luna_critic` | `gpt-6-luna` | high | Revisar sem editar |
| `luna_tester` | `gpt-6-luna` | medium | Testar e produzir evidências |
| `sol_reviewer` | `gpt-6-sol` | high | Revisão independente quando o risco justificar |

Use execução direta para tarefas pequenas, uma Luna para tarefas claras e
ondas paralelas somente com escopos independentes. O teto de sete agentes é
um limite da política; respeite uma capacidade menor no Codex de destino.
Cada Luna recebe no máximo uma correção focada. Sol conserva decisões de
arquitetura, segurança, produção e aceitação final.

## Atualizar ou restaurar

Execute `git pull --ff-only`, reveja `python scripts/install.py` e aplique a
atualização com `--apply --replace`. Para restaurar arquivos substituídos,
copie os arquivos do backup indicado pelo manifesto para os caminhos
correspondentes no diretório do Codex. Arquivos novos não têm versão anterior.
Reabra a sessão depois de instalar ou restaurar.

## Verificar o pacote

```sh
python -m unittest discover -s tests -v
python skills/sol-luna-orchestrator/scripts/workflow.py --help
```

A ferramenta `workflow.py` cria e valida pacotes e recibos com hashes,
limites de escopo e evidências; ela não chama modelos. Veja os contratos em
[`references/contracts.md`](skills/sol-luna-orchestrator/references/contracts.md).

Formato dos agentes e limites conferidos na
[documentação oficial de subagentes do Codex](https://developers.openai.com/codex/subagents)
em 26/09/2026. As permissões efetivas dos agentes dependem também das opções
da sessão principal, como explica essa documentação.
