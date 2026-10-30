# MVP 1.3 — detalhamento verificável e legibilidade da planta compacta

Base: residência unifamiliar térrea de 2 quartos, branch de produção `cloud/ezdxf`.
Esta etapa amplia o **pacote para revisão profissional**; não é projeto executivo
nem verificação de acessibilidade/NBR/legislação municipal.

## Melhorias implementadas

- `ARQ-PLANTA`: quadro de **portas** com largura (L) do modelo e altura
  (H) calculada com os mesmos dados do envelope usados nos cortes e fachadas.
- Quadro de **janelas** com largura real do segmento (incluindo orientações
  verticais), altura (H) e peitoril (P) relativos à cota de piso.
- Identificadores das janelas externas posicionados do lado de fora da
  edificação, afastando-os de móveis e equipamentos internos.
- Nova auditoria `auditoria_legibilidade`: compara caixas de texto
  **estimadas** com o contorno dos móveis e com outras anotações. Emite
  `view_id`, `source_id`, `other_source_id` e código do conflito.
- As evidências são registradas em `report.json`, `report.md` do ZIP e na
  resposta MCP do pacote. A auditoria **não bloqueia exportação** somente
  com estimativas de texto; os problemas precisam de revisão visual.

## Caso real reproduzido

No modelo piloto 10 × 20 m, a identificação `J02` era colocada sobre a
bancada da cozinha: `opening-tag:window:1` × `furniture:2`.
O teste `test_compact_plan_window_ids_do_not_overlap_furniture` falhou
antes da correção e passou após a mudança de posição.

## Invariantes e limites

1. As alturas de portas/janelas são calculadas exclusivamente a partir do
   `BuildingEnvelope` informado; sem norma implícita nem inventar valores.
2. A largura de janela vem de `hypot(dx, dy)`, nunca só de `dx` (que seria
   zero em janela orientada verticalmente).
3. O modelo DXF e as pranchas são reabertos/auditados antes da entrega.
4. A auditoria gráfica usa caixas aproximadas de fonte, não os glifos reais
   do PDF; logo, `warnings=[]` **não atesta legibilidade perfeita**.
5. A escala e a posição de anotação exigem inspeção do PDF A3 em 100%,
   especialmente em cômodos pequenos, carimbos, giros de portas e cotas.

## Regressão reproduzível

```bash
python -m pip install -e ./cloud/ezdxf pytest matplotlib
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python -m pytest cloud/ezdxf/tests -q
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_plant_lab.py --output out/plant-lab
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_licensing_corpus.py --output out/licensing-corpus
```

O relatório técnico e as imagens são artefatos do GitHub Actions. A
inspeção humana deve ser acompanhada de registro de defeitos antes de
elevar o escopo para tipologias adicionais.
