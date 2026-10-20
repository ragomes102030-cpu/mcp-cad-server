# Schema do "modelo" de planta (`cad_mcp/planta.py`)

Todo o desenho é **dado**. O módulo só sabe transformar este dicionário em entidades.
Unidade: **metros**. Ângulos em **graus** (a conversão para radianos é feita internamente).

```python
{
  "titulo": "...",              # opcional, só informativo
  "espessura_parede": 0.15,     # todas as paredes (m)
  "terreno": (x1, y1, x2, y2),  # retângulo do lote, camada TERRENO
  "paredes":    [(x1, y1, x2, y2), ...],       # EIXOS das paredes (ver abaixo)
  "ambientes":  [ {"nome": "...", "x1":, "y1":, "x2":, "y2":, "h": 0.22}, ... ],
  "portas":     [(x, y, angulo_graus, largura_m), ...],
  "janelas":    [(x1, y1, x2, y2), ...],
  "moveis":     [(x1, y1, x2, y2), ...],
  "cotas_h":    [(x1, x2, y_medido, y_texto), ...],
  "cotas_v":    [(x, y1, y2, x_texto), ...],
  "selo":       [(x, y, "texto", altura), ...],
  "dim_txt": 0.22,   # opcional: altura do texto das cotas
  "dim_asz": 0.18,   # opcional: tamanho da seta das cotas
}
```

## `paredes` — eixos, não faces

Cada trecho é o **eixo** da parede. O renderizador transforma em faixa de espessura
`espessura_parede` para os dois lados do eixo (`cons_faixa_parede`).

**Porta = trecho de parede separado.** Não existe "arco pintado por cima da parede":
você interrompe o eixo e o vão fica de verdade.

```python
# parede corrida com um vão de 0,80 m entre x=2,30 e x=3,10
(0.00, 5.10, 2.30, 5.10),
(3.10, 5.10, 7.00, 5.10),
```

### Alternativa melhor: `paredes_arquitetonicas` + `aberturas` (hospedadas)

Em vez de cortar à mão, declare a parede **inteira** e a abertura **na parede**
(offset + largura). O `planta.py` chama `cad_mcp.arch.expandir()` e o vão vira
consequência do corte — não dá para desenhar porta sobre parede fechada.

```json
"paredes_arquitetonicas": [
  {"id": "S", "eixo": [[0, 0], [13, 0]]},
  {"id": "L", "eixo": [[13, 0], [13, 10]]}
],
"aberturas": [
  {"id": "D1", "parede": "S", "tipo": "porta",  "offset": 8.60, "largura": 0.90,
   "dobradica": "inicio", "gira": "esquerda"},
  {"id": "J1", "parede": "S", "tipo": "janela", "offset": 1.20, "largura": 1.40,
   "peitoril": 0.90}
]
```

- `offset` é medido do **início do eixo** (na ordem dos pontos) até o batente inicial;
- `fechada: true` fecha o polígono (último ponto → primeiro), útil para perímetro;
- `tipo`: `porta` | `janela` | `vao` (vão puro não desenha folha nem caixa);
- `dobradica`: `inicio` | `fim`; `gira`: `esquerda` | `direita` (90°);
- paredes com vértice: a abertura não pode atravessar o vértice (é recusada).

A validação disso é `tests/test_arch.py` (roda sem AutoCAD). Quando o modelo usa
`paredes_arquitetonicas`, `portas` e `janelas` são geradas — não declare as duas coisas.

## `ambientes` — use as faces **internas**

Cada ambiente é o retângulo livre (entre as faces internas). Para parede de 0,15 m,
a face interna fica a 0,075 m do eixo:

```
eixo em x = 7,00  ->  face interna = 7,075
```
Na prática, monte a lista dos eixos + espessura e derive:
`xi = eixo + espessura/2`. A área útil que aparece no selo é a **soma** desses
retângulos — por isso ela tem que ser conferida contra o número pedido.

`h` é a altura do texto do nome (padrão 0,26). **Ambiente estreito pede texto menor**:
`largura_do_texto ≈ n_caracteres × h × 0,9` — se passar da largura livre do ambiente,
o texto invade a parede.

## `portas`

`(x, y, angulo, largura)`: o **ponto de dobradiça** em `(x, y)`, o arco de 90° varrendo
de `angulo` até `angulo+90`, e a folha saindo de `(x, y)` na direção `angulo`.

Use `angulo = 90` para porta que abre "para cima" (residência comum no hemisfério sul
do desenho, ou seja, varrendo para a esquerda), `0` para abrir para a direita,
`180`/`270` para as outras diagonais. **Confira sempre se o quadrante varrido cai
dentro do ambiente**, e não em cima da parede perpendicular:

```python
# porta no vão 8,30–9,10 da parede y=6,20, dobradiça na esquerda, abrindo para o norte
(8.30, 6.275, 90.0, 0.80),
```

## `janelas` — duas linhas

`(x1, y1, x2, y2)`: o eixo do vão. O renderizador desenha **duas linhas paralelas**
a ±espessura/4, na camada JANELAS, por cima da faixa da parede.

## `selo` (a legenda)

Aqui mora o maior risco de estragar a folha. **Largura ≈ `n_chars × altura × 0,9`.**

Regras que funcionaram:
- quebre em linhas de **no máximo ~70 caracteres**;
- altura 0,20–0,22 para o título, 0,16–0,18 para o resto;
- mantenha a largura total **menor que a do terreno**, senão o plot (que usa
  *Extents*) encolhe o desenho para caber a legenda junto.

## Camadas usadas

`TERRENO`, `PAREDES`, `PORTAS`, `JANELAS`, `MOBILIARIO`, `COTAS`, `TEXTOS`
(criadas automaticamente por `desenhar_modelo`; ver `cad_mcp/layers.py`).

## Exemplo completo

`assets/modelo-3-quartos.json` — residência 3 quartos, 119,56 m² de área útil:
13,00 × 10,00 m de eixos, 24 trechos de parede, 10 ambientes, 10 portas, 8 janelas,
16 peças de mobiliário, 7 cotas e selo. Serve de ponto de partida: copie, mexa nos
números e rode.
