# MCP CAD Cloud — Auditoria de fundação do MVP 1.0

Data: 2026-10-31. Branch de referência: `cloud/ezdxf`. Issue: #30.

## Escopo efetivamente examinado
Inventário da árvore do repositório (`cloud/ezdxf`): 30 arquivos Python de aplicação e 46 arquivos Python de testes. Leitura de `planta_layout_compacto.py`, `planta_gerador.py`, `planta_assistida.py`, `projeto_arquitetonico.py`, `plant_workflow.py`, `backend.py`, `projeto_automatico.py`, `quantitativos_engenharia.py`, `auditoria_coerencia.py` e `topologia_paredes.py`. Esta auditoria é **estática e parcial**; não equivale a executar toda a suíte.

## Evidências
1. `planta_layout_compacto.py`: documentação e `compativel` restringem o layout de referência a dois quartos e programa compacto. A generalização espacial é um novo requisito, não uma capacidade demonstrada.
2. `planta_gerador.py`: normalização de programa e geração de modelo existentes; devem ser preservadas como adaptadores de compatibilidade.
3. `planta_assistida.py`: template determinístico, paredes e aberturas; reaproveitar regras geométricas validadas.
4. `projeto_arquitetonico.py`: estruturas de vistas arquitetônicas e pacote paramétrico existentes; não reimplementar sem necessidade.
5. `plant_workflow.py`: tokens de preview associados à sessão com TTL de 15 minutos em memória; isso não é persistência durável de projeto.
6. `backend.py`: gerenciamento de workspace e sessão; separar o estado de edição da sessão de transporte.
7. `projeto_automatico.py`: interpretação de pedido e fluxo de geração existentes.
8. `quantitativos_engenharia.py`: extração DXF existente; futura rastreabilidade deve relacionar resultados a IDs de elementos.
9. `auditoria_coerencia.py` e `topologia_paredes.py`: auditorias de coerência, paredes e vãos existentes; incorporar aos gates.
10. Nos módulos inspecionados não foi demonstrado um modelo persistente e versionado de paredes/aberturas com IDs estáveis e operações incrementais; a ausência em todo o repositório ainda precisa ser confirmada.

## Arquitetura-alvo mínima
`Prompt -> ProgramSpec -> ProjectModel (IDs persistentes + restrições) -> LayoutSolver -> CAD Adapter -> Audits -> Sheet/Quantities`.

`ProjectModel` v1 proposto: `project_id`, `schema_version`, `units=m`, `lot`, `rooms[]`, `walls[]`, `openings[]`, `fixtures[]`, `revision`. Cada elemento: `id`, `geometry`, `relationships`, `metadata`. Preservar compatibilidade com os geradores atuais por adaptador, sem mudar saídas aprovadas antes dos testes.

## Gates do próximo incremento (F1)
- Esquema JSON serializável e validado, rejeitando IDs duplicados, referências ausentes, medidas não finitas e geometria inválida.
- Round-trip de serialização preserva IDs e relações.
- Migração de versão explícita e reversível em testes.
- Testes unitários de criação, atualização e rejeição; regressão dos layouts existentes.
- CI verde; PR revisável; só integrar após validação.

## Corpus de homologação
Preparar 20 programas dentro do escopo residencial térreo, variando largura de lote, posição de acesso, número de quartos, suíte, lavanderia, cozinha integrada e restrições de adjacência. Classificar cada cenário como suportado, rejeitado corretamente ou falha; guardar PDFs/DXFs e relatórios por caso. Metas de aceitação na Issue #30.

## Riscos
- Não confundir validade de DXF com qualidade arquitetônica.
- Não afirmar escala certificada, conformidade normativa ou aprovação profissional sem verificação.
- Não substituir desenhos CAD reais por imagens geradas.
- Não publicar mudança de contrato MCP sem testes de compatibilidade.
