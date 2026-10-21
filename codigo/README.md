# mcp-cad-server

Servidor **MCP** que desenha e lê plantas no AutoCAD. Quarenta ferramentas
(`entity_create_*`, `drawing_*`, `dimension_*`, `layer_*`, `block_*`, `arch_room`,
`quantitativo`), três motores intercambiáveis e um histórico de falhas que vira
verificação.

## O que ele faz

- **Desenha planta a partir de dados** (`modelo.json`): paredes, ambientes, portas e
  janelas hospedadas, móveis, cotas, selo → DWG, DXF, PDF e PNG.
- **Lê o desenho aberto**: entidades, camadas, blocos, extensão, quantitativos.
- **Funciona com ou sem AutoCAD**: `com` (desenho vivo, sem roubar foco), `file_ipc`
  (AutoCAD LT), `ezdxf` (headless; usa `accoreconsole` para DXF/PDF).
- **Mede o que saiu**: DXF lido de volta, abertura de arco, `INSUNITS`, `/MediaBox` do PDF.

## O que ele não faz (ainda)

Edição fina (`TRIM`, `EXTEND`, `FILLET`, `CHAMFER`, `JOIN`) — são comandos, não métodos
de API; o caminho é o plugin .NET em `plugin/` ou geometria própria. Também não faz
orçamento: `quantitativo` conta, não precifica.

## Requisitos

| | |
|---|---|
| Python | 3.10+ |
| AutoCAD | 2025 (opcional; sem ele roda headless) |
| Windows | necessário apenas para COM/`pywin32` |

## Instalar e rodar

```powershell
python -m pip install -e .
cad-mcp
```

Sem instalar:

```powershell
$env:PYTHONPATH="src"; python -m cad_mcp.server
```

O servidor fala **stdio** (MCP padrão). Configuração para um cliente:

```json
{
  "mcpServers": {
    "cad": {
      "command": "cad-mcp",
      "args": []
    }
  }
}
```

Para escolher o motor: variável `MCP_CAD_BACKEND` = `com` | `file_ipc` | `ezdxf`
(padrão: detecta). Temporários em `MCP_CAD_TEMP` (padrão `C:/temp/mcp_cad_com`,
**sem espaços** — o `SendCommand` trata espaço como ENTER).

## Testar

```powershell
python tests\validar_modelo_teste.py   # validador de modelo (sem AutoCAD)
python tests\test_arch.py              # aberturas hospedadas (sem AutoCAD)
python tests\test_bridge.py            # protocolo do plugin (sem AutoCAD)
```

## Onde está o conhecimento

O código é a menor parte. O que faz o desenho sair certo está em:

| caminho | conteúdo | portátil? |
|---|---|---|
| `SKILL` (`cad-planta-autocad`) | receita, armadilhas, falhas, mapa do AutoCAD | **sim** — copiar a pasta |
| `docs/` | mapas medidos (COM, cobertura, aliases), gerados | não, é build artifact |
| `historico/` | falhas reais com evidência | sim, é dado |
| `vendor/` | `autocad-mcp-pro` 1.6.0 (MIT) e afins, só leitura | com o aviso de licença |

## Licença

O código deste repositório ainda **não tem licença definida** — definir antes de
distribuir. `vendor/autocad-mcp-pro-1.6.0` é MIT (Umutcan Edizsalan) e o aviso
original deve acompanhar qualquer redistribuição.
