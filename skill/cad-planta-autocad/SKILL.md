---
name: cad-planta-autocad
description: Cria e entrega plantas baixas no AutoCAD de verdade (arquitetura, layout, quantitativos) usando o mcp-cad-server via COM/ActiveX, e valida o resultado antes de entregar DWG/DXF/PDF. Use quando o usuário pedir planta baixa, planta de casa/apartamento/sobrado, layout arquitetônico, "cria uma planta de X quartos com Y m²", redesenhar/alterar planta existente, extrair quantitativo de paredes/portas/janelas, ou gerar PDF/DWG/DXF de um desenho. Cobre também os erros silenciosos do AutoCAD (arcos girados, texto estourando a folha, DXF desatualizado) que fazem um desenho parecer certo estando errado.
---

# Plantas baixas no AutoCAD real (mcp-cad-server)

> **Regra de ouro desta skill: contagem de entidades e "0 erros" não provam nada.**
> O AutoCAD erra em silêncio. Todo render termina com conferência de **propriedade**
> (abertura de arco, unidades, extensão, folha), nunca só de existência.

## Onde as coisas estão

| | |
|---|---|
| Projeto do MCP | `C:\Users\Correta Engenharia\mcp-cad-server` (env `MCP_CAD_SERVER`) |
| Motor | `src/cad_mcp/com_backend.py` — COM/ActiveX no AutoCAD **aberto** (não rouba foco) |
| Renderizador | `src/cad_mcp/planta.py` — `desenhar_modelo(backend, modelo)` |
| MCP no AionUi | `mcp-cad-server` (stdio, 118 tools), id `mcp_01a1472d-f66b-7350-a159-a3d5cdea6ef7` |
| Área de trabalho | `C:\temp\mcp_cad_com` (**sem espaço no caminho** — env `MCP_CAD_TEMP`) |
| Motores alternativos | `file_ipc` (AutoCAD LT), `ezdxf` (headless, sem AutoCAD) via `MCP_CAD_BACKEND` |
| Camada oficial | `references/api-oficial-mcp.md` — o que a **Autodesk declara** (ObjectARX/.NET/AutoLISP/COM) e o **MCP oficial** do AutoCAD. Ler quando o pedido for sobre API oficial, suporte, MCP da Autodesk ou o que "não é suportado" |

## Receita: gerar uma planta

Escreva **só o JSON** (schema em `references/modelo-planta.md`) e rode:

```bash
python scripts/render_planta.py modelo.json --media A3
python scripts/render_planta.py modelo.json --nome planta_sobrado \
       --entrega "C:/caminho/da/pasta/da/conversa"
```

O script faz o pipeline inteiro e **se auto-confere**: conecta no AutoCAD vivo →
`drawing_create` → desenha → **salva o DWG** → exporta DXF (`accoreconsole`) →
plota PDF → screenshot → copia para `saida/` + Desktop (+ `--entrega`) → confere →
devolve exit code 0/1 e imprime o relatório.

Partida rápida: copie `assets/modelo-3-quartos.json` (119,56 m², 3 quartos, 10 portas,
8 janelas) e mexa nos números.

### Antes de desenhar: valide o modelo (1 ms, sem AutoCAD)

```bash
python scripts/validar.py modelo.json
```

Barra porta sem vão, texto/selo que estoura o espaço, ambiente invertido ou
sobreposto, área diferente do m² pedido, parede fora do terreno. Cada erro traz
uma `chave` que existe no histórico de falhas do projeto:

```bash
python -m cad_mcp.historico               # sintomas, quantas vezes, o que promoveu
python -m cad_mcp.historico --chave X     # sintoma, evidência, correção
```

**Regra de promoção:** sintoma só vira verificação de código na **3ª ocorrência**
(nunca na primeira — a primeira pode ser typo). Registrar é barato; promover sem
evidência enche o relatório de ruído e a gente passa a ignorá-lo. Detalhes e
tabela do que é (e não é) verificável em `references/falhas.md`.


## Montar um modelo novo do zero

1. **Defina os eixos externos** (ex. 13,00 × 10,00 m) e a espessura (0,15 m).
2. **Desenhe a grade de eixos** das divisórias, alinhando as paredes que se cruzam.
3. **Ambientes = retângulos livres** (face interna = eixo ± espessura/2).
   Some as áreas e **compare com o m² pedido**. Ajuste o footprint, não o texto.
4. **Portas = vãos**: interrompa o eixo da parede em dois trechos. A "parede" não é
   contínua com um arco por cima.
5. **Escolha o quadrante de cada porta** e confira se o arco cai dentro do ambiente.
6. **Texto**: `largura ≈ n_chars × altura × 0,9`. Ambiente estreito → texto menor.
7. **Selo em linhas de ≤ 70 caracteres**, mais estreito que o terreno.
8. Rode, confira, e só então entregue.

## Conferência obrigatória antes de entregar

```bash
python scripts/conferir.py planta.dxf --mapa     # unidades, contagens, arcos, áreas, e a planta em ASCII
python scripts/validar_pdf.py planta.pdf         # folha, tinta, margens, prévia PNG
```

Cheque, nesta ordem:
- `INSUNITS = 6` (metros);
- **toda abertura de arco = 90,00°** — se aparecer 116,62°, é graus passados onde
  `entmake` espera radianos (ver `references/armadilhas.md` #1);
- extensão em metros compatível com o projeto (o plot usa *Extents* — nada pode
  extrapolar muito, ou a planta inteira encolhe);
- soma das áreas dos ambientes = área útil que você vai anunciar;
- PDF: 1 página, folha esperada, tinta > 0,3 %, margens equilibradas;
- `--mapa`: **olhe o ASCII**. É a forma de conferir a topologia sem ver imagem.
  Lembre da sub-amostragem (parede de 0,15 m some em célula de 0,2 m).

Só depois disso copie os arquivos para a pasta da conversa e o Desktop, e diga
claramente o que foi entregue e onde.

## Ferramentas do MCP (45, nomes no padrão `autocad-mcp-pro`)

Vocabulário adotado do `autocad-mcp-pro` 1.6.0 para que prompt escrito para ele
funcione aqui sem tradução (`entity_*`, `drawing_*`, `view_*`, `dimension_*`).
O que não tem equivalente lá mantém nome próprio (`quantitativo`, `script`).

- **Desenho**: `entity_create_line`, `entity_create_polyline`, `entity_create_rectangle`,
  `entity_create_circle`, `entity_create_arc`, `entity_create_text`, `entity_create_mtext`,
  `entity_create_hatch`, `arch_room` (ambiente com nome/área)
- **Cota**: `dimension_linear`, `dimension_aligned`
- **Consulta**: `system_status`, `drawing_info`, `entity_list` (filtra por camada **e** tipo),
  `layer_list`, `block_list`, `quantitativo`
- **Edição pontual**: `entity_erase` (por handle), `entity_erase_filter` (por camada / tipo /
  texto, com pré-visualização), `entity_move` — corrigir sem redesenhar tudo
- **Transformar / duplicar**: `entity_copy` (handle → novo handle), `entity_copy_filter`
  (copia por camada e/ou tipo — é o "copiar o pavimento inteiro"), `entity_rotate`,
  `entity_mirror` (unidade espelhada), `entity_offset` (face de parede a partir do eixo),
  `entity_mirror_filter` (espelha em bloco por camada/tipo), `entity_rotate_filter`
  (gira em bloco por camada/tipo)
- **Arquivo**: `drawing_new`, `drawing_open`, `drawing_save`, `drawing_export_dxf`,
  `drawing_export_pdf`, `plot_pdf(path, folha="A2", escala=50)` — com `escala` a escala é
  **real** (1:50); sem ela é "fit" na folha
- **Preparo do documento**: `drawing_setup(unidades=6, escala_cota=0.1, ltscale=0.2)` — põe
  INSUNITS em metros, DIMSCALE 0,1 (texto de cota 0,25 m, flecha 2 mm no papel a 1:50),
  DIMDEC 2, LUPREC 2 e LTSCALE 0,2 (DASHED com traço de 2 mm a 1:50; 1,0 fica grosseiro e
  0,05 parece contínuo). **Chame depois de `drawing_new`**: sem isso o DXF sai com unidade
  mm e a cota sai com 2,5 m de texto.
- **Camadas**: `layer_create`, `layer_linetype_load` (carrega DASHED/HIDDEN antes de criar
  camada com esse LTYPE), `layer_list`, `layer_set_current`, `drawing_apply_iso_layers`
- **Blocos**: `block_insert`, `block_list`, `block_get_attributes`, `block_set_attributes`
- **Visão/controle**: `view_screenshot`, `view_render_png` (gravam no `path` pedido; devolvem
  `largura`/`altura` — se vier < 320×200 px a janela do AutoCAD está minimizada),
  `view_zoom_extents`, `drawing_undo`, `drawing_redo`, `system_run_command`, `script`,
  `cancel`

`system_run_command` usa a **ponte .NET** (`plugin/CadMcpBridge`, roda dentro do AutoCAD)
quando ela está carregada — é o caminho para `TRIM`, `EXTEND`, `FILLET`, `CHAMFER`.
Sem a ponte, cai para o modo headless e comandos de edição não funcionam.
Conferir: `python -m cad_mcp.bridge ping`.

Mapa completo (nossas 48 × as 247 deles, por família): `docs/COBERTURA.md` no projeto,
gerado por `python tools/importar_acmpro.py`.

## Pendências conhecidas (não silencie)

- `dim_linear` **vertical** devolve 0,0 no backend **ezdxf** (o COM está certo).
- `entity_move` usa `(command "_.MOVE" ...)`, o caminho síncrono do COM: já travou o
  AutoCAD uma vez. Teste com um handle só antes de mover em lote.
- Texto com várias linhas: `entity_create_mtext` não aceita `\P` (o `_q` come a barra).
  Use uma `entity_create_text` por linha.
- Plot/export **não** escolhem a escala sozinhos: passe `escala=50` (e `folha` se quiser
  fixar). PDF com texto vetorizado é limitação do plotter DWG To PDF.
- Módulo de **orçamento/custo** (importador SEINFRA) ainda não existe — só desenho e
  quantitativo. Se o pedido for orçamento, diga que essa parte não está pronta.

## Referências

- `references/modelo-planta.md` — schema completo do `modelo` (paredes, ambientes, portas, selo).
- `references/armadilhas.md` — 34 armadilhas com sintoma/causa/correção. **Leia antes de
  culpar o código.**
- `references/falhas.md` — como o desenho aprende: registro de falhas, regra das 3
  ocorrências, o que é verificável no modelo e o que só existe como regra de código.
- `references/mapa-autocad.md` — fronteira COM × comando (o que é método e o que só
  existe como comando), números do AutoCAD 2025 e como regerar o mapa.
- `assets/modelo-3-quartos.json` — modelo real, validado, para clonar.
