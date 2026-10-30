# MCP CAD Cloud — MVP 1.2, porta de qualidade das pranchas

**Escopo:** piloto de residência térrea compacta de dois quartos, geração de
vistas arquitetônicas e pacote para **revisão profissional**, não licenciamento
aprovado. Município, zoneamento, normas e parâmetros obrigatórios ainda devem
ser conferidos com fontes verificáveis e responsável técnico.

## Defeitos reproduzidos antes das correções

No commit de testes `f7b5d66`, cinco mutações de DXF passavam despercebidas
pelo auditor antigo: uma parede deslocada, uma camada de parede trocada,
segmento duplicado, escala escrita errada e rótulo de cota adulterado.
O CI registrou **5 falhas, 199 aprovados**:
https://github.com/ragomes102030-cpu/mcp-cad-server/actions/runs/41057158258

No teste separado `b49a3b7`, o pico do telhado da fachada lateral divergia
do corte perpendicular em aproximadamente **0,20984 m**, com a mesma planta.
Resultado reproduzido: **1 falha, 205 aprovados**:
https://github.com/ragomes102030-cpu/mcp-cad-server/actions/runs/41057581893

## Verificações acrescentadas

1. **DXF serializado:** as entidades reabertas precisam corresponder aos
   segmentos geométricos originais nas coordenadas de papel (mm), com
   escala real `1000 / escala`; também são conferidas camadas, tipos,
   multiplicidades, posição e conteúdo dos rótulos.
2. **Escala:** o texto do carimbo deve conferir com a escala efetivamente
   aplicada a todos os viewports da folha.
3. **Entre vistas:** a implantação precisa representar a projeção real da
   planta; a cobertura inclui o beiral informado; fachadas têm envelopes
   equivalentes, portas/janelas projetadas nas posições do modelo e todos
   os cortes/fachadas devem alcançar a mesma elevação de cumeeira.
4. **Saída:** inconsistência geométrica entre vistas ou entre DXF e modelo
   bloqueia a exportação; o resultado deve registrar `code`, `view_id`
   e `source_id` para localizar a divergência. O relatório JSON dentro
   do ZIP inclui `cross_view_coherence`; a resposta MCP inclui
   `auditoria_coerencia`.

## Teste reproduzível

```bash
python -m pip install -e ./cloud/ezdxf pytest matplotlib
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python -m pytest cloud/ezdxf/tests -q
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_plant_lab.py --output out/plant-lab
PYTHONPATH=cloud/ezdxf MCP_CAD_PROFILE=full python tools/run_licensing_corpus.py --output out/licensing-corpus
```

O GitHub Actions publica o corpus, os relatórios e as imagens geradas para
revisão. Suíte verde **não substitui** a inspeção dos PDFs/PNGs em escala
100% por profissional. Entre as limitações restantes: faces acabadas ainda
não mensuradas independentemente, verificação de interferências gráficas
incompleta, resultados de acessibilidade apenas aproximados, e ausência
de perfil normativo/municipal completo. Nenhum resultado equivale à
conformidade legal ou à autorização para construir.

**Regra de promoção:** manter este PR em draft até testes completos,
inspeção de amostras gráficas e confirmação do commit publicado em
`/healthz`, seguida de MCP `initialize` e `tools/list` reais.
