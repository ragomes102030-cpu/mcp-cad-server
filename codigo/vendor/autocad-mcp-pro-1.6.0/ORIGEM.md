# ORIGEM — vendor/autocad-mcp-pro-1.6.0

Cópia **não modificada** de `autocad-mcp-pro` 1.6.0, só para leitura de referência.

| | |
|---|---|
| pacote | `autocad-mcp-pro` |
| versão | 1.6.0 |
| fonte | wheel do PyPI (`https://pypi.org/project/autocad-mcp-pro/`) |
| repositório | https://github.com/U-C4N/Autocad-MCP |
| autor | Umutcan Edizsalan |
| licença | MIT (ver `LICENSE`) |
| baixado em | 2026-10-16 |
| arquivos | 138 `.py`, ~3,0 MB |

## Por que está aqui

Não é dependência: o `mcp-cad-server` **não importa** nada daqui, nem em runtime nem
em teste. O pacote pede Python >= 3.11 e o nosso ambiente é 3.10. A cópia existe
para responder três perguntas com **código**, não com opinião:

1. que operações um servidor MCP de AutoCAD maduro expõe (catálogo);
2. como ele resolve o que nos custou rodadas: aberturas hospedadas em parede,
   junções L/T/X, page setup validado contra o `/MediaBox` do PDF;
3. quais comandos ele manda para o AutoCAD e em que variante (com ou sem `-`).

O que extraímos vira nosso, com crédito e sem copiar texto: as ideias e as regras.
O código deles é MIT, então cópia com atribuição é legal — mas código copiado não
traz evidência de que funciona **neste** AutoCAD, e é isso que o nosso histórico
resolve.

## Caminhos úteis (espelham a raiz do wheel)

| caminho | o que tem |
|---|---|
| `server.py` | ~247 ferramentas MCP, 10,6 mil linhas |
| `backends/com_backend.py` | engine COM (311 KB) |
| `backends/ezdxf_backend.py` | engine alternativa sem AutoCAD |
| `backends/contracts/` | contratos por família (drawing, layers, layouts, pagesetup...) |
| `engineering/arch/` | paredes, aberturas, ambientes, esquadrias, materiais, quantitativos |
| `engineering/understand/takeoff.py` | levantamento de quantitativos (49 KB) |
| `engineering/standards/sysvars.py` | variáveis de sistema por padrão |
| `engineering/standards/plot.py`, `pdfinfo.py` | plot e leitura do PDF gerado |
| `discovery/aliases.py` | apelidos/nomes que o agente vê (84 KB) |

## Como atualizar

```powershell
$j = Invoke-RestMethod https://pypi.org/pypi/autocad-mcp-pro/json
$u = ($j.urls | Where-Object { $_.filename -like '*.whl' }).url
Invoke-WebRequest $u -OutFile C:\temp\acmpro.whl
Copy-Item C:\temp\acmpro.whl C:\temp\acmpro.zip
Expand-Archive C:\temp\acmpro.zip C:\temp\acmpro\pkg -Force
```

Depois: `python tools/importar_acmpro.py` para regerar `docs/COBERTURA.md` e
`docs/catalogo-acmpro.json`.
