# ferramentas\ — os scripts que geram o mapa

Nenhum deles desenha. Todos leem e escrevem nos diretorios de entrega da pasta raiz:
`docs\` e `historico\` (a partir de `codigo	ools\`, isso e' `..\..\docs\`).

| script | precisa do AutoCAD aberto? | escreve |
|---|---|---|
| `mapear_com.py` | não — lê a type library `acax25enu.tlb` | `MAPA-COM.md`, `ALIASES.md`, `com-acad-2025.json` |
| `importar_acmpro.py` | não — lê o código vendorizado | `COBERTURA.md`, `catalogo-acmpro.json` |
| `sonda_autocad.py` | **sim**, com desenho | `MAPA-AUTOCAD.md`, `catalogo-autocad.json` |
| `mapear_entidades.py` | não — lê a tabela DXF do `ezdxf` | `MAPA-ENTIDADES.md`, `catalogo-entidades.json` |
| `MapaDotnet` (C#) | não — lê a metadata das DLLs | `catalogo-dotnet.json` |
| `resumir_dotnet.py` | não — organiza o JSON acima | `MAPA-DOTNET.md` |
| `mapear_comandos.py` | **sim**, duas fases | `historico/prompts.jsonl` |
| `sonda_cadbridge.py` | **sim** (o plugin próprio) | `MAPA-CADBRIDGE.md`, `catalogo-cadbridge.json` |

Aqui são **cópias para leitura**. Para rodar, use os originais em `..\codigo\tools\`,
porque os scripts calculam a raiz do projeto a partir do próprio caminho:

```powershell
cd "..\codigo"
$env:PYTHONUTF8=1

python tools\mapear_com.py
python tools\importar_acmpro.py
python tools\mapear_entidades.py
python tools\sonda_autocad.py            # AutoCAD aberto

# .NET (precisa do SDK 8; aqui ele está fora do PATH)
$dn = "$env:LOCALAPPDATA\Microsoft\dotnet\dotnet.exe"
& $dn build tools\MapaDotnet -c Release -v q
& "tools\MapaDotnet\bin\Release\net8.0\MapaDotnet.exe" docs\catalogo-dotnet.json `
    "C:\Program Files\Autodesk\AutoCAD 2025\acdbmgd.dll" `
    "C:\Program Files\Autodesk\AutoCAD 2025\acmgd.dll" `
    "C:\Program Files\Autodesk\AutoCAD 2025\accoremgd.dll"
python tools\resumir_dotnet.py
```

## O gravador de prompts (em duas fases)

Varrer comandos de uma vez trava o AutoCAD: ler variável de sistema enquanto um
comando espera seleção **para de responder** (está no `historico/`). Por isso:

```powershell
python tools\mapear_comandos.py --lista
python tools\mapear_comandos.py --iniciar TRIM    # manda TRIM e manda ESC
python tools\mapear_comandos.py --ler TRIM        # lê o prompt e grava
```

Se o `--ler` ficar parado, o comando não foi cancelado: aperte **ESC** no AutoCAD
e rode de novo. O resultado vai para `historico\prompts.jsonl`, sem sobrescrever.

> **Medido em 20/10/2026: a captura é intermitente.** `LASTPROMPT` só pode ser lido
> de dentro do processo (o COM recusa a chamada enquanto o comando espera seleção),
> e a thread principal ocupada faz a leitura dar timeout. Uma varredura longa
> **travou o AutoCAD**. Varra pouco por vez e salve o desenho antes.

## A sonda do plugin próprio

`sonda_cadbridge.py` mede o `CadMcpBridge` — a superfície MCP que existe **de fato**
nesta máquina, e não o MCP oficial da Autodesk (que é do AutoCAD 2027). É o par do
`sonda_autocad.py`: aquele mede o AutoCAD, este mede o plugin dentro dele.

Sem o AutoCAD aberto, ele reporta o plugin como não carregado e sai com 0 — ausência
medida é resultado, não falha. O que ele **não** prova está escrito em
`docs/MAPA-CADBRIDGE.md`.

## Como a sonda descobre as variáveis

O AutoCAD não tem API para listar variáveis de sistema. A sonda monta uma lista
de **candidatas** e pergunta o valor de cada uma com `(getvar "NOME")`:

1. `MsiKeyFile_<NOME>.dll` em `C:\Program Files\Autodesk\AutoCAD 2025\MsiKeyFile`
   — 603 nomes que a própria instalação declara;
2. as `$VARS` do cabeçalho do DXF de exemplo (o que o desenho salva);
3. uma lista curta das clássicas que o MsiKeyFile não lista.

Quem responde `nil` não existe nesta instalação e vai para o fim do arquivo.
