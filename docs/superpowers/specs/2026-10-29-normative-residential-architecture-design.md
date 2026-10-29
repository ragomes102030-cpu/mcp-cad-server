# Projeto de arquitetura residencial compacto com verificações normativas rastreáveis

## Intenção

Evoluir o MCP CAD Cloud de um gerador de estudo preliminar para uma ferramenta de apoio à produção e revisão de documentação arquitetônica de uma residência compacta. O usuário escolheu começar pela família residencial compacta e manter município como configuração do projeto.

O sistema deve mostrar quais requisitos foram considerados, quais passaram ou falharam, quais não se aplicam e quais não podem ser testados. “Conforme às NBRs” nunca será um rótulo geral sem uma matriz de aplicabilidade, fontes vigentes, evidências e revisão profissional.

## Estado atual

- A branch de trabalho `codex/plant-lab-20261029` contém o laboratório da família `compacto_2quartos`, com saída DXF/PDF/PNG e auditorias geométricas, de conectividade e circulação.
- O motor atual admite uma tipologia estreita e fixa; sua saída foi avaliada como estudo preliminar, não como projeto completo ou pronto para obra.
- Na revisão do laboratório em 29/10/2026, os 30 cenários compactos aceitos não geraram avisos de gargalo de circulação após a correção do acesso à lavanderia; permanecem limitações na medição de áreas/rotas e nenhuma verificação NBR implementada.
- A geometria é produzida em metros e exportada para DXF; não há hoje conjunto completo de plantas, cortes, fachadas, cobertura, quadro de esquadrias, carimbo parametrizado ou matriz normativa.

## Objetivos

1. Definir um perfil de projeto de residência unifamiliar compacta, inicialmente térrea e com dois dormitórios, registrando os dados necessários à análise de aplicabilidade: uso, município/UF, número de pavimentos, dimensões do lote, implantação, áreas, programa, condições de acessibilidade e estágio documental.
2. Criar uma matriz normativa versionada. Cada requisito deve registrar norma/edição, status e data de verificação no catálogo, fonte autorizada, cláusula consultada após acesso legítimo ao texto, condição de aplicabilidade, parâmetro, unidade, resultado, evidência e limitações.
3. Cobrir documentação de arquitetura e representação gráfica primeiro; incluir critérios de acessibilidade, desempenho habitacional, implantação, ventilação/iluminação e segurança somente depois de identificar a regra aplicável e ter fonte verificável para cada critério.
4. Gerar um conjunto arquitetônico coerente com o estágio declarado do projeto, incluindo, conforme o escopo selecionado, implantação/situação, planta baixa cotada, cobertura, cortes, fachadas, identificação de ambientes, quadro de áreas e esquadrias, legenda, notas e carimbo.
5. Separar a legislação municipal/estadual e condicionantes do terreno das NBRs. Cada perfil local precisa identificar município, fonte oficial, versão/data, parâmetros extraídos e pontos pendentes de conferência; município desconhecido ou dados incompletos resultam em `não testável`, nunca aprovação presumida.
6. Criar verificações automatizadas independentes para geometria e conteúdo da documentação, com evidência ligada ao DXF/PDF reaberto e cenários válidos, inválidos e limítrofes.
7. Produzir relatório de revisão com status `passou`, `falhou`, `não testável` ou `não aplicável`, mostrando evidências e pendências sem converter estimativas em certificação.

## Fora de escopo da primeira etapa

- Projetos elétrico, hidráulico, sanitário, estrutural, incêndio, gás, climatização, acústica ou paisagismo.
- Aprovação automática em prefeitura, emissão de ART/RRT ou substituição de responsável técnico.
- Garantia universal de conformidade com “todas as NBRs”; normas aplicáveis dependem do tipo de projeto e das condições locais.
- Certificação de desempenho, acessibilidade, segurança ou autorização para construir sem revisão profissional e sem dados/fontes suficientes.
- Reproduzir ou redistribuir o conteúdo integral de normas protegidas por direito autoral.

## Abordagens consideradas

- **A — uma tipologia com matriz de aplicabilidade e evidência (escolhida pelo usuário):** começar com a residência compacta já existente, adicionar contexto do projeto, verificações por requisito e documentação correspondente; município fica como perfil configurável. Limita a primeira entrega, mas permite testar resultados e revelar lacunas de forma auditável.
- **B — cobrir várias tipologias ao mesmo tempo:** amplia a variedade, mas exige domínios geométricos, critérios e corpus maiores antes que uma delas possa ser validada com rigor.
- **C — implementar somente carimbo e formatação da prancha:** entrega apresentação mais completa rapidamente, mas não atende ao objetivo de verificar requisitos de arquitetura nem cria a base de aplicabilidade normativa.

## Desenho proposto

### Contexto do projeto

Usar um objeto versionado de dados do projeto com tipologia, uso, município/UF, pavimentos, lote, recuos informados, programa, áreas solicitadas, orientação, níveis e estágio do projeto. Campos indispensáveis para um requisito devem ser validados antes da geração; ausência de dado deve produzir pergunta, pendência ou resultado `não testável`, sem adivinhação silenciosa.

### Matriz de requisitos

Manter dados estruturados separados do código de geometria. Cada item terá identificador estável, referência normativa, edição/status/data de consulta, gatilhos de aplicabilidade, critério verificável, unidade/tolerância, evidência esperada, função verificadora, cenários de teste e rota de revisão humana. A matriz não deve conter cópias extensas do texto das normas.

O inventário registra a ABNT NBR 9050:2020 Versão Corrigida:2021 como “Em Vigor”, com base em ficha oficial ABNT/Sebrae confirmada em 11/12/2025. As demais candidatas mantêm “Não confirmado” quando não houve ficha oficial detalhada disponível. Nenhum texto normativo foi copiado ou usado para implementar critérios; todas as nove linhas permanecem sem avaliador e `não testável`. A lista é não exaustiva e deve ser atualizada antes de qualquer uso profissional.

### Saídas arquitetônicas

Separar claramente estudo preliminar, projeto para licenciamento e documentação executiva. O usuário definiu como primeira meta documentação arquitetônica para licenciamento, com perfil municipal configurável. O conjunto de pranchas deve mostrar escala, orientação, níveis e cotas pertinentes, símbolos e legendas consistentes, quadro de áreas/esquadrias quando aplicável e carimbo editável com obra, endereço/município, cliente, autores e registros informados, conteúdo da folha, número, escala, data e revisão. Não inventar nomes, registros ou assinaturas.

### Avaliação e rastreabilidade

O validador independente deve analisar entidades do DXF serializado e elementos efetivamente renderizados, não apenas o resumo interno do gerador. Cada achado aponta para IDs de entidades/ambientes, prancha, parâmetro, referência normativa e cenário. A cobertura de regra e a cobertura de geometria serão reportadas separadamente. Testes adversariais devem provar que violações e requisitos ausentes são detectados.

### Revisão

Perfis normativos e municipais incluem fonte, edição, data da checagem e responsável pela interpretação. Mudança de edição invalida a marca de revisão anterior e exige análise de impacto. Resultado automático não equivale a aprovação; itens que dependem de interpretação, visita, cálculo especializado ou decisão do órgão permanecem como revisão profissional.

## Critérios de aceite propostos

- Nenhum resultado geral afirma conformidade se houver requisito aplicável sem status ou evidência.
- Critérios implementados têm referência rastreável, versão, resultado individual, teste positivo e teste adversarial.
- Dados ausentes, fonte desatualizada e jurisdição não configurada aparecem como pendência/`não testável`.
- DXF/PDF exportados são reabertos e inspecionados; folhas incluem carimbo e identificação coerentes com o perfil.
- O primeiro corpus cobre variação de lote, áreas, orientação, programa suportado, aberturas e condições de acessibilidade definidas depois da revisão das fontes.
- A saída é rotulada pelo estágio do projeto e não é apresentada como projeto executivo se não contiver as entregas e verificações desse estágio.
- CI anexa relatório e amostras visuais e impede regressões em critérios obrigatórios.

## Decisões já tomadas e decisões pendentes

- **Tomada pelo usuário:** focar arquitetura; começar pela residência compacta existente; permitir município configurável.
- **Proposta do executor:** usar uma matriz versionada com rastreabilidade, quatro estados de validação e escopo progressivo; não fazer alegação genérica de atendimento normativo.
- **Aprovado pelo usuário:** a primeira meta é um conjunto arquitetônico para projeto de licenciamento de residência compacta, com perfil municipal configurável. Como nenhuma cidade foi escolhida, requisitos municipais permanecem `não testáveis` até existir um perfil local com fonte e revisão.
- **Pendente de fonte:** conferir diretamente no catálogo ABNT o status e as edições das normas candidatas e ter acesso legítimo aos textos necessários antes de implementar qualquer critério detalhado.
- **Pendente para testes municipais:** município inicial de validação. O usuário escolheu deixar município configurável, portanto a matriz deve suportar perfis locais sem fingir cobrir uma cidade não selecionada.

## Limites

Este documento propõe o escopo de produto e a estratégia de validação. Ele não declara atendimento a qualquer norma. Normas podem ser atualizadas, requisitos legais variam por jurisdição e a interpretação final requer profissional habilitado e fonte oficial atual.
