---
name: laje-concreto-armado
description: Use quando o pedido for planta de forma e armação de laje de concreto armado (maciça, nervurada ou pré-moldada). Dimensiona por placa elástica (NBR 6118), monta o quadro de ferros, desenha as pranchas no AutoCAD e entrega o relatório com premissas e verificações.
---

# Lajes de concreto armado — da planta de forma à armação

> **Regra de ouro: contagem de entidades e "0 erros" não provam nada.**
> E aqui há uma segunda: **momento calculado não é armadura adotada.** Quase toda
> laje de uso corrente é governada pela **armadura mínima** — conferir isso antes de
> sair distribuindo barra é o que separa um projeto de um palpite bem desenhado.

## Quando usar

- "cria a planta de forma e armação da laje X"
- "dimensiona a laje do pavimento / cobertura / garagem"
- pedido com geometria de painel, vãos, vigas/pilares de apoio, carga de utilização
- qualquer entrega que peça **planta de forma + armação + quadro de ferros + detalhe de ancoragem**

## Antes de desenhar: o que falta

O pedido quase sempre chega em branco. **Pare e liste o que falta** — não invente
dimensão, carga ou armadura. O que bloqueia e o que dá para fixar como premissa:

| Bloqueia (não dá para desenhar) | Dá para fixar como premissa declarada |
|---|---|
| Geometria / vãos / apoios | Tipo de laje (maciça / nervurada / pré-moldada) |
| Seção das vigas e pilares | Aberturas e shafts (posição e dimensão) |
| Espessura h | Cargas (rev. + acidental) |
| Cobrimento + classe de agressividade | Bloco padrão de pilar/viga do escritório |
| fck / aço | Escala, folha, layout das pranchas |
| Carga permanente e acidental | Dados da cartela (responsável, CREA, data) |

Quando fixar algo como premissa, **marque com `(P)` no relatório** e diga na entrega
que aquilo precisa ser trocado pelo valor real.

## O fluxo, em 5 etapas

### 1. Esforços — placa elástica, e **validada antes de usar**

Ver `references/solver-placa.md` para o código. Nunca use um solver de placas sem
antes checar os dois limites abaixo — é o que pega o erro de contorno (o momento no
apoio sai ~15 % baixo quando a borda engastada é modelada errado).

| Validação | Esperado |
|---|---|
| Viga/uma-via `2,00 × 20,00 m` engastada | M⁺ = qL²/24 = 1,400 · M⁻ = qL²/12 = −2,800 |
| Placa quadrada `4,00 × 4,00 m` | M⁻ borda = −0,0513·qL² (Timoshenko) |

**Ponto crítico:** a borda engastada é `w=0` no nó 0 **e no fantasma `w[-1]=w[1]`**;
nós interiores de `1` a `n-2`. E o momento no apoio sai por **extrapolação quadrática**
`M(0) = 3·M₁ − 3·M₂ + M₃` (o nó 1 está em `x=a`, não em `x=0`).

### 2. Armadura — sempre comparar com a mínima

`As = Msd / (z · fsd)` com `z = 0,95·d`, `fsd = fyk/1,15`, `d = h − cobr − ∅/2`.
Aí **compara com `ρ_mín = 0,15 %` (CA-50)**: `As_mín = 0,0015 · b · h`.

> Se a mínima governar (é o comum), diga isso na entrega. Não é falha — é o
> detalhamento que rege, e o quadro de ferros sai daí.

### 3. Comprimentos e ancoragem

`l_b = (∅/4)·(fyd/fbd)`, com `fbd = η₁·η₂·fctd`, `fctd = 0,7·fctm/γc`,
`fctm = 0,3·fck^⅔`. Para CA-50/C30: `l_b ≈ 0,24 m` (∅8), `0,30 m` (∅10).

| Situação | Comprimento |
|---|---|
| Barra positiva | vão livre + 2·l_b |
| Negativa sobre apoio interno | l_n/4 + largura do apoio + l_n/4 |
| Negativa de borda | l_b + l_n/4 |
| Reforço de abertura | dimensão da abertura + 2·l_b |

Ver `references/verificacoes-nbr6118.md` para a lista completa de conferências.

### 4. Desenho no AutoCAD

Ver `skill/cad-planta-autocad` para as ferramentas. Camadas pedidas: `CONTORNO, EIXOS,
COTAS, FORMA, VIGAS, PILARES, ARMADURA_POS, ARMADURA_NEG, ARMADURA_DIST, ABERTURAS,
TEXTO, LEGENDA, CARTELA`. Barras positivas e negativas em cores diferentes.

**Para não desenhar 340 linhas uma a uma:** crie **1 linha-base e use
`entity_array_rectangular`** (barras ao longo de y, grade em x: `cols=40, col_spacing=0,20`).
O array resolve — mas só se a linha-base e o array estiverem em **rodadas separadas**.

### 5. Entrega

- `.dwg` com as pranchas em layouts (uma aba por prancha)
- `.dxf` de backup
- `.xlsx` do quadro de ferros (posição, φ, qtd, L unit., L total, peso, totais por diâmetro)
- `.md` com premissas, verificações e **os pontos que exigem revisão do responsável**

## Armadilhas de sessão (o que já custou tempo)

Resumo — detalhe completo em `skill/cad-planta-autocad` → *Armadilhas de sessão do MCP*:

- **Nunca `-SCRIPT`.** Deixa diálogo modal e a partir daí `entity_create_*` devolve
  handle sem criar. Recuperação: `drawing_new`.
- **Chamadas na mesma rodada rodam em paralelo.** Apagar-e-recriar e criar-e-arrayar
  na mesma rodada perdem entidade. Cadeie.
- **`entity_list`/`quantitativo` podem estar defasados.** Confirme com render + grep no DXF.
- **`entity_erase_filter` e `entity_set_properties` não aplicam.** Use `entity_erase` por
  handle e `layer_set_current` antes de criar.
- **`dimension_linear` cria na camada corrente** e a unidade segue `DIMLFAC`
  (para milímetros: `DIMLFAC=1000`, `DIMDEC=0`, antes de criar).
- **`drawing_export_pdf`/`batch_plot` não são confiáveis.** Verifique com PNG.
- **`vlax-put` em `ViewCenter` não faz efeito.** Ajuste da vista é manual.

## Referências

- `references/solver-placa.md` — solver biharmônico validado, com o código e os testes
- `references/verificacoes-nbr6118.md` — cada verificação, o número e o limite
- `references/premissas-exemplo.md` — o projeto exemplo parametrizável (Laje-Exemplo-L01)
