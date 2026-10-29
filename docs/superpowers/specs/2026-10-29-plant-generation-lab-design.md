# Laboratório automatizado de geração e auditoria de plantas

## Intenção

Substituir a verificação manual isolada por um laboratório reproduzível para o MCP CAD Cloud. O laboratório deve revelar em que cenários a geração, exportação, circulação e apresentação visual falham, produzir evidência revisável e orientar correções de causa raiz.

## Estado atual observado

- Base: `cloud/ezdxf` em `c77e87a1f8e2dea5710ac4010eb9de64fffd391a`, versão `0.3.6`.
- A suíte atual passa com 117 testes e um aviso de depreciação do Authlib.
- O pacote já gera plantas compactas e genéricas, exporta DXF e renderiza PDF/PNG. A auditoria geométrica reabre o DXF serializado; a auditoria de circulação estima rotas em uma malha de 10 cm.
- O workflow `.github/workflows/cloud-regressions.yml` roda a suíte, cria prévias e publica artefatos por 30 dias.
- O relato do teste anterior observou que o ganho estimado de 0,27 m é próximo à resolução da malha e não inspecionou visualmente os desenhos. Sobreposição em planta de um móvel com faixa horizontal de janela também pede teste de contexto vertical/função, não uma conclusão automática de colisão.

## Objetivos

1. Exercitar dezenas de briefings determinísticos: pelo menos 30 programas válidos dentro das capacidades declaradas pelo gerador e pelo menos 20 casos adversariais. Variar largura/profundidade e recuos do terreno, áreas e combinações suportadas, mobiliário e limites declarados. Relatar separadamente programas estruturados e briefings em linguagem natural; incluir pelo menos um teste de ponta a ponta da chamada MCP/HTTP, sem afirmar que a matriz inteira cobre o protocolo.
2. Para cada caso válido, percorrer geração e criação real de DXF; salvar bytes em arquivo temporário, reabrir com `ezdxf.readfile`, executar `ezdxf.audit()` e a auditoria geométrica existente.
3. Acrescentar uma verificação geométrica independente, implementada no laboratório e calculada das entidades do DXF reaberto, sem chamar a validação de produção para calcular o mesmo resultado nem confiar nos resumos do gerador como prova. Checar unidades e coordenadas das entidades; terreno e limites; segmentos e vãos de parede; folhas/arcos de portas; linhas de janela; pegadas de móveis e interseções. Conferir também os rótulos de dimensões internas do DXF contra as áreas pedidas, mas identificá-los como consistência de anotação: o DXF atual não contém polígonos fechados por cômodo e, portanto, não permite declarar que a área foi medida diretamente das faces físicas. Manter o escopo e as tolerâncias explícitos.
4. Auditar conectividade, portas e circulação. A produção fixa a malha em 10 cm; medir sensibilidade em 5/10/15 cm com um avaliador independente de teste, sem alterar a configuração de produção só para o benchmark. Se um cálculo não puder usar geometricamente os mesmos obstáculos, expor essa limitação no relatório. Diferenças abaixo da resolução serão sinalizadas como inconclusivas, não como largura exata. Não inferir conformidade legal.
5. Verificar fidelidade ao briefing por requisitos estruturados explicitamente testáveis (ambientes e áreas fornecidos) e por um conjunto separado de briefings naturais cuja interpretação esteja no escopo declarado. Reportar premissas, rejeições corretas e requisitos sem suporte. Casos inválidos devem falhar sem mutação. Adversariais de DXF incluirão mutações controladas em portas, janelas, paredes, móveis e conectividade para provar que o avaliador detecta corrupção; esses arquivos modificados não são saídas válidas a serem rejeitadas pelo gerador.
6. Gerar DXF para todos os válidos; renderizar PDF/PNG em amostras documentadas que cubram cada família de layout e os casos de circulação original/proposta. Montar uma prancha comparativa e inspecionar visualmente a saída neste trabalho. Verificações automáticas de arquivo, enquadramento e conteúdo complementam, mas não substituem, a inspeção humana. Artefatos e relatórios ficam anexados ao CI para revisão.
7. Emitir relatório JSON/Markdown com métricas, identificadores de cenário, falhas completas, regressões e caminhos/hashes dos artefatos. O CI deve anexar prévias e relatórios para revisão.
8. Corrigir defeitos concretos reproduzíveis em ciclos e executar o laboratório e a suíte de regressão após as correções. Manter separados erros do produto, falhas do laboratório e resultados esperados de rejeição.

## Fora de escopo e limites

- Não alegar aprovação arquitetônica, acessibilidade, atendimento a NBR, código de obras, iluminação/ventilação ou autorização para construir.
- Não prometer perfeição absoluta nem converter estimativa de malha em largura livre certificada.
- Não remover, afrouxar ou reclassificar falhas para melhorar métricas; resultados negativos e avisos devem permanecer visíveis.
- Não mudar o protocolo público ou o contrato do MCP sem necessidade demonstrada por falha reproduzível.
- Não publicar/deployar nem fazer merge da branch de produção como parte da validação local. Preparar branch/PR e relatar as evidências; decisão final de merge/deploy depende de validação comprovada.

## Abordagens consideradas

- **A — laboratório integrado ao pacote `cloud/ezdxf` (escolhida pelo usuário):** corpus e verificações em pytest, funções auxiliares de laboratório isoladas da aplicação, artefatos integrados ao workflow existente e um subconjunto exercitando o fluxo MCP/HTTP. Reaproveita o CI, mantém regressões próximas ao produto e facilita ciclos rápidos.
- **B — benchmark externo via cliente do servidor MCP:** testa mais do ambiente remoto, mas depende de rede/serviço, aumenta variabilidade e custo e dificulta depurar cada falha. Pode ser adicionado depois como smoke test, sem substituir o laboratório determinístico.

## Desenho proposto

- Manter os casos em uma matriz declarativa com ID, tipo (válido/adversarial), briefing, programa esperado, escala/dimensões, requisitos e resultado esperado. Usar sementes explícitas e fixtures sem mutação compartilhada.
- Separar geração e exportação do avaliador independente. Toda métrica computada pela auditoria existente deve ter sua origem indicada; o avaliador não deve aceitar resumos do modelo como prova das entidades físicas.
- Gravar DXF em diretório temporário, reabrir o arquivo, derivar geometria real e cruzar os resultados com requisitos do cenário. Comparar rotas em resoluções múltiplas e registrar variação observada.
- Para cenários válidos, obter os PNG/PDF produzidos pelo fluxo existente; gerar uma folha de contato para amostras cobrindo cada família de layout e incluir esses artefatos no CI. Para falhas, salvar o DXF e um registro de diagnóstico quando houver arquivo válido para inspecionar.
- Produzir um resumo estável com contagens esperadas/aprovadas/rejeitadas, taxas e casos com avisos, duração, hashes e falhas nomeadas. O processo termina com falha de CI quando um requisito obrigatório não passa ou um caso adversarial não é rejeitado conforme esperado.
- Alterar o gerador somente após uma falha mínima reproduzível. Para cada correção, registrar a hipótese, preservar a regressão e repetir primeiro o cenário e depois o conjunto completo.

## Critérios de aceite

- Pelo menos 30 cenários válidos e 20 adversariais determinísticos aparecem no relatório com resultados individuais.
- Os cenários válidos são submetidos a leitura física do DXF serializado, auditoria ezdxf, checagem geométrica independente, conectividade/aberturas/móveis, consistência dos rótulos de área (identificados como anotação) e renderização selecionada com PDF/PNG válidos.
- O relatório declara que o DXF não contém polígonos fechados por cômodo; área de ambiente não é apresentada como medição independente das faces construídas.
- Os adversariais rejeitados não deixam desenho/artefatos parciais e sua razão é identificável.
- O relatório comunica a sensibilidade da malha e mantém ressalvas não legais; nenhuma métrica implica certificação.
- A suíte completa atual e o novo laboratório passam na branch de trabalho; CI da PR anexa evidência visual e relatórios.
- Todas as falhas encontradas são listadas com status; nenhuma falha fica escondida por tolerância sem justificativa ou comparação visual baseada só em pixel.

## Decisões do executor

- Corpus determinístico no repositório, bibliotecas já disponíveis (`ezdxf`, `matplotlib`, `pytest`) e avaliador independente em funções de teste, sem dependência ou custo de produção novo.
- Manter o branch público de produção intacto; trabalhar em `codex/plant-lab-20261029` desde `c77e87a`.
- Usar imagens renderizadas para inspeção humana e métricas numéricas para geometria; não usar comparação pixel a pixel como critério arquitetônico.
- Não criar uma nota subjetiva de “qualidade arquitetônica”. Definir falha obrigatória por contrato verificável (geometria, briefing, portas/vãos, mobiliário, áreas, conectividade e saída visual legível); deixar juízos de projeto/uso e conformidade para avaliação profissional separada.
- A medição independente em grades de 5/10/15 cm é um indicador de sensibilidade apenas; o algoritmo existente permanece em 10 cm e sua resposta deve ser relatada separadamente.
- Nenhuma verificação normativa será atribuída ao laboratório.
