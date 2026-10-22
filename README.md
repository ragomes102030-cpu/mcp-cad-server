# Mapeamento AutoCAD 2025 — registro e regeração dos mapas

Pasta original e única fonte de verdade do sistema de mapeamento deste repositório.

```
C:\Users\Correta Engenharia\Desktop\Mapeamento AutoCad
```

Tudo o que este sistema administra vive aqui:

- **Maps** de `docs\` (COBERTURA, MAPA-COM, MAPA-ENTIDADES, MAPA-AUTOCAD, MAPA-DOTNET, MAPA-OFICIAL-MCP, AUDITORIA) — o que o COM, o .NET, o DXF e o AutoCAD *verdadeiramente* fazem, com o que o COM têm fretes.
- **Skills** de `skill\` (cad-planta-autocad, laje-concreto-armado) — o que um agente lê e executa.
- **Ferramentas / instalacao / historico / plugin / saida / exemplos / codigo/** — scripts, instalação do mcp-cad-server, arquivo de ocorrências e bridge .NET.
- **Gerador único** `codigo/tools/regenerar_docs.py` (e `ferramentas/`) — rege a `docs\` a partir do código quando houver mudança.

## Como o Skills do Hermes vê (e liga) para a pasta original

O Skills (`AppData\Local\hermes\skills\`) não guarda cópia: usa ligação (symlink):

| Skill visível no Hermes | O que ele é | Origem real (git) |
|---|---|---|
| `cad-planta-autocad` | Pasta com `SKILL.md`, `assets`, `references`, `scripts` | `skill/cad-planta-autocad/` |
| `laje-concreto-armado` | Symlink → `...\skill\laje-concreto-armado` | `skill/laje-concreto-armado/` |

Regra prática: **edite e registe só em `Desktop\Mapeamento AutoCad` (master)**. O Skills é só o endereço da leitura.

## Como atualizar sempre

Geração dos mapas (do código para `docs\`):

```bat
cd C:\Users\Correta Engenharia\Desktop\Mapeamento AutoCad\codigo
python tools/regenerar_docs.py
```

Refere o estado atual de `docs\`, os JSONs de cobertura, o que há, o que falta e o que ignorar. O estado é validado por:

- `codigo/tools/auditar_cobertura_real.py` — mostra, para cada ferramenta, os métodos por backend (base / COM / ezdxf / file_ipc) e se o COM está disponível.
- `codigo/tools/bateria_ao_vivo.py` — bateria de passo a passo em AutoCAD vivo (pronto para regressão).
- `codigo/tools/sonda_lacuna.py` — sonda cada uma das 118 ferramentas. Falha = página aberta.

Se alguma ferramenta mudar, rode `regenerar_docs.py` e commit.

## Regras do repositório

- **Pull request sempre para `main`** (o `develop` é sincronizado automaticamente). O merge dispara o deploy.
- Antes de qualquer outra mudança, certifica-se que o deploy está **live**: `/healthz` devolve o SHA do `origin/main`.
- `README.md` em inglês no backend; o Português é usado nos maps, skills e reportes.

## O que exige revisão do engenheiro responsável

- Todos os dados de cargas e armaduras de planta baixa são de referência e **não** verificados estruturalmente. Use `CONTRIBUTING.md` e o referido engenheiro para conferência de planta.
- `MAPA-AUTOCAD.md` e `MAPA-COM.md` são baseados nas respostas do AutoCAD. Uma resposta diferente (sucesso de comando, mensagem de erro) altera o mapa.
- `historico/ocorrencias.jsonl` consta apenas falhas reais que aconteceram — não αύτοπαραδείγματα não referentes a eventos.

## Licença

MIT (veja `LICENSE`) e avisos de terceiros em `THIRD_PARTY_NOTICES.md`.
