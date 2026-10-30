# MCP CAD Cloud v0.4.0 — Engineering Quantities Pilot

## Escopo e decisão arquitetural

O MCP CAD é responsável por **geometria** e **quantitativos geométricos**
com origem e critérios rastreáveis. Não consulta tabela SINAPI/SEINFRA, não
compõe insumos, não aplica BDI e **não calcula preços**. O Arquimedes (ou
qualquer cliente MCP) pode orquestrar:
`CAD → quantitativos estruturados → EAP → MCP Custos → Cronograma`.

NÃO há dependência de um servidor de Custos, da Plataforma Obras ou de
um agente específico. O contrato JSON Schema está em
`cloud/ezdxf/schemas/cad-quantitativos-v1.schema.json`. A função
`quantitativo` mantém `entities`, `by_type` e `by_layer` e acrescenta
`quantitativos_construtivos`. Seus argumentos antigos continuam aceitos.

## Camadas de medição intencionalmente EXPLÍCITAS

O motor mede somente as entidades presentes no Modelspace DXF em metros:

| Layer | Geometria | Medição |
|---|---|---|
| `EIXOS-PAREDES` | LINE | comprimento axial (m) |
| `VAOS-PORTAS` | LINE | largura por segmento, quantidade |
| `VAOS-JANELAS` | LINE | largura por segmento, quantidade |
| `PISOS` | LWPOLYLINE fechada de retas | área Gauss e perímetro (m) |

**Não somar linhas de contorno do layer `PAREDES`**: duas faces externas
não representam dois eixos, e cantos/uniões geram contagens equivocadas.

O DXF residencial existente contém paredes desenhadas em faces e não
disponibiliza necessariamente as quatro camadas de medição acima. Nesse
caso, a extração a partir de desenhos existentes retorna
`DADOS INSUFICIENTES` para o levantamento construtivo: a ferramenta não
fabrica eixos ou polígonos de pisos a partir de títulos/cotas em pranchas.
A **normalização auditada** do DXF gerado para este contrato continua uma
evolução separada; não declare que todo arquivo residencial já contém
quantitativos completos.

## Campos obrigatórios para completar uma parede

`altura_paredes_m`, `espessura_paredes_m`,
`aberturas_por_parede` (handle de parede para handles de aberturas),
`inventario_aberturas_completo=true` e alturas correspondentes
`altura_portas_m`/`altura_janelas_m` se a parede tiver aberturas.

Sem inventário explicitamente completo: **área bruta pode existir; área
líquida e volume não são calculados**. Alturas e espessuras nunca
decorrem de padrão legal presumido. As aberturas precisam estar
colineares e contidas no eixo da parede associada, sem sobreposição.

Atribuição de ambiente a portas/pisos exige vínculo fornecido, que
esta versão não infere. Revestimentos ainda exigem definição de
superfície, altura, acabamento e descontos. A declaração de completude
é geométrica e NÃO representa orçamento, material comprado, desconto
legal, área útil normativa ou projeto executivo.

## Exemplo independente, sem preços

Uma parede reta no DXF:

- `EIXOS-PAREDES`: LINE de (0,0) até (4,0) → **4,00 m**.
- Altura fornecida: **3,00 m** e espessura: **0,15 m**.
- Porta `VAOS-PORTAS`: 0,90 m de largura, altura 2,00 m.
- Janela `VAOS-JANELAS`: 1,20 m de largura, altura 1,20 m.
- Inventário de aberturas declarado completo e ambos os handles
  associados a essa parede.

Resultados de referência aritmética:

- Área bruta: 4,00 × 3,00 = **12,00 m²**.
- Aberturas: 0,90 × 2,00 + 1,20 × 1,20 = **3,24 m²**.
- Área líquida: 12,00 − 3,24 = **8,76 m²**.
- Volume geométrico: 8,76 × 0,15 = **1,314 m³**.
- Polígono fechado de piso retangular 4,00 × 3,00 m: área **12,00 m²**,
  perímetro **14,00 m**.

**Limite:** a multiplicação por espessura é uma convenção geométrica
simplificada e não desconta encontros de paredes/volumes compartilhados
nem atende critérios de medição de obra sem contrato explícito. Não
usar diretamente para compra de material.

## Benchmark versionado

```bash
PYTHONPATH=cloud/ezdxf python tools/run_cad_engineering_benchmark.py \
  --output out/cad-engineering-benchmark.json
```

Cada linha contém entrada, resultado esperado, obtido, diferença,
tolerância, status, commit, versão e versão de cálculo. O benchmark v1
inclui cinco retângulos, triângulo 3-4-5, parede com aberturas e mutação
autointersectante. A pipeline de GitHub Actions executa esse benchmark e
arquiva o JSON (30 dias).

## Riscos de segurança e limitações pendentes

- O serviço público atual usa links HTTPS temporários tipo bearer (15 min),
  sem autorização por usuário para downloads. **Não subir projetos privados**
  ou arquivos com dados pessoais enquanto não houver autenticação,
  controle de posse e permissões.
- Estado de desenho é volátil, vinculado a sessão/token, TTL de 3600 s.
- Extração limita complexidade a 15000 entidades elegíveis; limite não
  substitui controles sobre requests HTTP/carga do serviço.
- Auditoria de circulação v1 classifica separadamente problemas
  geométricos, funcionais, avisos e verificações normativas não feitas.
  Conectividade 7/7 NÃO comprova acessibilidade ou funcionamento real.
- Auditoria de geometria gerada permanece parcialmente acoplada ao
  `wall_boundary_segments`. A validação independente introduzida aqui
  cobre linhas de medição, polígonos e erros sintéticos, não toda a
  topologia de paredes/vãos do projeto residencial.
- Benchmark ainda precisa ser ampliado para cobrir visualização PDF
  tipográfica em tamanho real, 5 tipologias efetivamente distintas,
  vínculo de eixos a faces/aberturas do gerador e calibração das larguras
  de circulação sem assumir 0,20 m como precisão executiva.
