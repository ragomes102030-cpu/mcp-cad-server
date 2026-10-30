# MCP CAD Cloud — DXF headless

Servidor MCP HTTP para Render/Linux, baseado em `ezdxf`. Não controla
AutoCAD Windows, não edita DWG e não acessa arquivos do computador local.

## Regra para agentes: este servidor nao abre AutoCAD

Este servico e **cloud/headless**. O processo roda no Render/Linux e nao tem
janela, COM/ActiveX, AutoCAD instalado, desktop Windows ou acesso a arquivos
DWG do computador do usuario. Portanto, o agente nao deve:

- chamar `system_status` esperando AutoCAD COM;
- pedir para o usuario abrir ou reiniciar o AutoCAD;
- usar `abrir_autocad` ou tentar controlar uma janela local;
- tratar a ausencia do AutoCAD como erro do servico.

O fluxo cloud comeca diretamente em:

```text
cad_status
planta_templates
planta_criar_validada(modo="preview")
planta_criar_validada(modo="desenhar", preview_token="...")
export_dxf
```

`new_drawing` cria um DXF em memoria temporaria. O estado e volatil; exporte
antes de reiniciar ou quando a sessao for encerrada. Para desenhar diretamente
no AutoCAD 2025, use o MCP local com backend `autocad_com`.

## Acesso

Nesta versão de teste `/healthz` e `/mcp` são públicos, sem Bearer Token.
O estado é temporário em memória e compartilhado pelo processo. Antes de
usar dados sensíveis, adicionar autenticação e isolamento por projeto.

## Deploy no Render

- Branch: `cloud/ezdxf`
- Build: `pip install -e ./cloud/ezdxf`
- Start: `python -m mcp_cad_cloud.server`
- Health check: `/healthz`
- Endpoint MCP: `/mcp`

## Uso recomendado no Claude (v0.3.1)

Chame **`projetar_residencia(pedido="...")` apenas com pedido**, sem passar
`programa`, quando o usuario nao fornece areas exatas. O backend preenche
as seis areas do layout piloto e informa suas premissas, em vez de tentar
adivinhar o tamanho correto do banheiro e hall. Um dicionario `programa`
parcial tambem recebe os padroes de largura, recuos e ambientes ausentes.

Se o Claude enviar seis nomes de ambientes sem area, os valores padrao
serao usados e informados. **Areas fornecidas explicitamente nunca sao
alteradas para fazer o gerador aceitar.** Se a geometria nao comportar um
banheiro de 4,5 ou 6 m2, a mensagem informa a faixa admissivel para aquele
layout (dependente das areas dos quartos).

"Sala e Cozinha integradas" precisa continuar como dois ambientes nomeados
separadamente no modelo, ainda que abertos fisicamente no desenho.

## Correcao assistida e reversivel do mobiliario — candidata v0.3.6

Use `propor_melhoria_circulacao(pedido="...")`, com APENAS o texto
do pedido (casa terrea compacta de dois quartos). O fluxo:

1. Gera/audita o **original** pelo fluxo estavel `projetar_residencia`
   e fornece seus links DXF/PDF/PNG/ZIP.
2. Localiza o mobiliario mais proximo do gargalo sinalizado,
   produz candidatos por deslocamentos pequenos ou rotacao de 90 graus,
   sempre preservando as dimensoes da base e a area do bloco esquematico.
3. Cada candidato e avaliado por `validar_modelo`, auditoria do DXF
   reaberto e auditoria de circulacao.
4. So apresenta uma proposta se a folga estimada na rota da lavanderia
   ganhar ao menos 0,10 m, sem novos avisos nem perdas estimadas
   superiores a 0,10 m nas demais rotas.
5. A alternativa aprovada pelo criterio piloto recebe **outro** conjunto
   de links, hash do DXF e relatorio antes/depois.

**A original nao e modificada, substituida nem aprovada para construcao.**
`alternativa_disponivel=false` significa que nenhuma das opcoes
testadas cumpriu os criterios; nunca simular ganho ou fabricar DXF.
Deslocar ou rotacionar mobiliario esquematico nao prova que eletrodomesticos ou
equipamentos caibam, nem verifica instalaçoes, acessibilidade ou
legislacao. A largura da malha tem incerteza de discretizacao de
aproximadamente 0,20 m: ganhos pequenos precisam ser conferidos.

## Diagnostico espacial quantificado — v0.3.5

No retorno `auditoria_circulacao.metricas` surgem:

- `diagnostico_passagens.larguras[]`: para cada um dos sete ambientes,
  `largura_estimativa_m`, `ponto_critico_m` e
  `obstaculos_proximos`, identificando `PAREDE-NN`, `VIDRO-NN`,
  `MOVEL-NN` ou `CONTORNO`.
- `gargalos_estimados[]`: apenas os ambientes previamente sinalizados
  como estreitos pela malha com reserva lateral de 0,25 m.
- `integracao_sala_cozinha`: verifica geometria das zonas contiguas,
  mede por amostragem a maior faixa aberta no limite compartilhado e
  informa coordenadas; uma divisoria que fecha a abertura gera erro.

**Criterio técnico do primeiro item:** busca uma rota de maior folga
mínima (maximin) dentro da casa, a partir de um ponto amplo na sala.
A estimativa é duas vezes a distância ao obstáculo mais próximo,
calculada em grade de 0,10 m. **Não é a largura livre real medida**;
a incerteza aproximada de quantização é 0,20 m, sem incluir desvios de
modelagem, acabamentos, giro ou uso. A porta de entrada, sua largura
e suas ferragens devem ser avaliadas separadamente.

**Atenção:** ambientes sem rota deixam a largura como `null`, nunca
como zero inventado. Pontos de gargalo e identificadores de obstáculos
são dados geométricos para inspeção, não uma conclusão normativa.

## Campos de areas e diagnostico por porta — v0.3.4

A resposta de `projetar_residencia` agora publica
`quadro_areas_m2`, com unidades explicitas:
- `ambientes_solicitados`: soma das seis areas assumidas/fornecidas;
- `circulacao_hall`: area do hall calculada pelas faces livres;
- `total_mapeado`: area dos sete retangulos mapeados;
- `projecao_externa`: largura externa vezes profundidade externa.

A profundidade livre linear do hall usa a chave
`hall_profundidade_livre_m` (em metros). A chave antiga
`hall_livre` fica somente para compatibilidade com consumidores
anteriores; **nao representa m2**. A chave historica
`area_util_total` representa somente a soma das areas geometricas
mapeadas, nao uma area util aferida por norma.

`auditoria_circulacao.metricas.portas` retorna um objeto por arco DXF
com `id` (`P01`, `P02`...), `pivo_m`, `vao_nominal_m`,
`setor_giro_graus`, `colisao_mobiliario_detectada`,
`moveis_interferentes`, `giros_sobrepostos_com`,
`giro_proximo_parede` e `abaixo_largura_piloto`.
A ausencia de colisao identificada e **ausencia pelo metodo
amostrado**, nao comprovacao de operabilidade ou acessibilidade.

### Atualizacao do catalogo no ChatGPT

O servidor FastMCP registra as ferramentas que anuncia em
`cad_status.capabilities`, mas **nao pode obrigar um cliente a
expor ferramentas recem-adicionadas**. Se `projetar_residencia`
aparecer no `cad_status` e nao no catalogo do ChatGPT, verificar
a atualizacao da lista de ferramentas na conexao MCP/Plugin no
ChatGPT, conforme permissoes do proprietario/admin do app.
Nao afirmar ter executado a ferramenta apenas porque esta listada
em `capabilities`. Testar a chamada real apos a atualizacao.

## Auditoria de circulacao e interferencias — v0.3.3

Na ferramenta `projetar_residencia`, apos a verificacao geométrica de
correspondencia modelo/DXF, uma segunda auditoria cruza:
- abertura de portas representada por `ARC` real no DXF;
- retangulos de mobiliario lidos de `LWPOLYLINE`;
- eixos de parede ja confrontados com as faces do DXF;
- alcance a partir da porta de entrada por malha de 0,10 m, evitando
  paredes e mobiliario;
- verificacao de todos os sete ambientes do modelo compacto.

**Erros comprovados** (sem entrada, ambiente sem conexao, colisao da
area de giro com mobiliario) bloqueiam DXF, PDF e PNG no fluxo automatico.
**Avisos preliminares** (setores de giro de portas sobrepostos,
aproximacao de folga, proximidade entre giro e parede) nao bloqueiam.
A malha de 0,10 m e raio de folga de 0,25 m sao parametros internos
para diagnostico, **nao declaracoes de conformidade NBR 9050**.
Nao verifica operabilidade de esquadrias, ventilacao, iluminacao,
seguranca contra incendio nem legislacao municipal.
A verificacao depende da concordancia previo-auditada entre o modelo e
as entidades DXF; erros compartilhados pelo algoritmo do gerador e
auditor precisam de testes adicionais.

## Auditoria geometrica de DXF serializado (v0.3.2)

No fluxo `projetar_residencia`, apos o desenho e antes de gerar PDF/PNG
e os links, o sistema **grava o DXF em um arquivo temporario e reabre com
`ezdxf.readfile`**. Compara as entidades reais com o contrato do modelo:
vertices e fechamento do TERRENO, todas as faces LINE das PAREDES,
ARC e folhas de PORTAS, vidro das JANELAS, LWPOLYLINE de MOBILIARIO,
origens das cotas DIMENSION, anotacoes internas e $INSUNITS=metros.

Detecta manipulacoes que `doc.audit()` nao detecta (por exemplo,
terreno com largura errada, porta sem arco, segmento extra que
fecha a abertura sala/cozinha, cota movida). Em divergencia,
`projetar_residencia` devolve
`etapa=auditoria_geometrica, code=CONTRATO_GEOMETRICO_VIOLADO`
sem fornecer links de download nem afirmar sucesso. Respostas validas
incluem `auditoria_geometrica` e medidas extraidas do arquivo.

**Limite explicito:** trata-se de comparacao entre modelo e DXF,
e a extracao das faces esperadas utiliza a mesma rotina de paredes
do desenho. Portanto, nao identifica automaticamente toda falha de
arquitetura, acessibilidade, ventilacao ou legislacao, nem garante
independencia completa caso o modelo e o gerador compartilhem um defeito.
Nao substitui projeto legal ou executivo.

## Um prompt para uma planta: projetar_residencia (fase piloto)

A partir da versao 0.3.0, o Claude pode chamar uma unica ferramenta:

```text
projetar_residencia(
    pedido="Desenhe uma casa terrea de dois quartos, sala, cozinha, banheiro e lavanderia em um terreno de 10 x 20 metros"
)
```

O fluxo interno realiza **preview / validacao / desenho CAD / auditoria ezdxf /
quantitativo / geracao PDF A3 e PNG a partir das entidades DXF / exportacao
DXF e ZIP**. Tudo em uma unica chamada MCP, sem o agente gerenciar
`preview_token`. A resposta retorna `arquivos.dxf_url`, `zip_url`,
`pdf_url` e `png_url`, todos temporarios por 15 minutos, mais SHA-256.
Esta versao utiliza matplotlib no servidor Render.

O Claude pode fornecer opcionalmente `programa={...}` com nomes e areas
especificos dos ambientes. Sem isso, o motor assume as seis areas piloto
18/9/5/12/10/5 m2, largura externa 9 m, paredes 0,15 m e recuos
hipoteticos 3/0,5/2 m, declarados explicitamente na resposta.
O campo `pedido` suporta a identificacao de uma casa terrea de 2 quartos,
com eventual terreno declarado como "10 x 20" ou "10 por 20".
O servidor nao usa LLM proprio para interpretar portugues; o Claude pode
preencher o `programa` estruturado ao precisar de areas exatas.

**Escopo restrito:** este piloto aceita apenas residencia terrea compacta
com 2 quartos convencionais, 1 banheiro, sala, cozinha e area de servico.
Rejeita pedidos de suites, garagem, varanda, piscina, pavimentos extras
e outros numeros de dormitorios. Requisitos nao suportados nao sao
silenciosamente omitidos. O PDF e conceitual, nao projeto legal ou
executivo. Recuos nao foram verificados com legislacao de Fortaleza
ou de outro municipio. Para outros arranjos, ampliar o motor de layout
antes de declarar suporte.

Use somente desenhos de teste neste ambiente publico sem autenticacao.
Quem receber os links podera acessar o arquivo durante os 15 minutos de TTL.

## Planta assistida

O cloud expõe `planta_assistida` para gerar a mesma residência determinística
em DXF headless. `modo="preview"` não altera o desenho; `modo="desenhar"`
cria entidades somente na sessão ezdxf temporária. Ele usa paredes por faces
sem sobreposição, vãos reais para portas/janelas e cotas do fundo. Não abre o
AutoCAD e não gera DWG nativo.

## Perfil de ferramentas cloud

O servico publicado usa `MCP_CAD_PROFILE=full` e expoe as ferramentas
verificadas de planta mais as primitivas headless do pacote `tools.py`.
Assim, o catalogo publico inclui `planta_templates`, `planta_criar_validada`,
`validar_planta` e tambem comandos como `draw_line`, `draw_rectangle`,
`arch_wall` e `entity_create_ellipse`.

Para restringir deliberadamente o catalogo ao fluxo seguro de planta, defina
`MCP_CAD_PROFILE=planta_segura`. O perfil padrao do servico cloud e `full`,
mas o agente deve continuar priorizando preview, validacao e auditoria antes
de usar primitivas.

## Testes

```powershell
$env:PYTHONPATH = "cloud/ezdxf"
python -m pytest cloud/ezdxf/tests -q
```

Verificação pós-deploy:

```powershell
python tools/verify_cloud_release.py --url https://SEU-SERVICO.onrender.com/mcp
```

O comando verifica versão, revisão, backend, transporte e uma requisição real
de `initialize` sem Bearer Token.

## Programa residencial sob medida — experimental

O MCP oferece o template `programa_sob_medida` para um estudo preliminar
de **residências térreas em duas faixas** (social à frente, íntima ao fundo).
Não é um algoritmo geral de arquitetura e não entrega projeto legal/executivo.

Use `planta_templates` para descobrir os recursos e `planta_criar_validada`:

```json
{
  "modo": "preview",
  "template": "programa_sob_medida",
  "programa": {
    "largura": 10,
    "terreno_largura": 12,
    "terreno_profundidade": 20,
    "recuo_frente": 3,
    "recuo_fundo": 2,
    "recuo_lateral": 1,
    "ambientes": [
      {"nome": "Sala de estar", "area": 18},
      {"nome": "Cozinha", "area": 9},
      {"nome": "Área de serviço", "area": 4},
      {"nome": "Quarto 1", "area": 12},
      {"nome": "Quarto 2", "area": 10},
      {"nome": "Banheiro social", "area": 4}
    ]
  }
}
```

Analise `resumo`, `avisos`, `modelo` e `validacao`. Somente depois,
chame o mesmo comando com `modo="desenhar"` e o `preview_token` retornado,
seguido de `drawing_audit` e `export_dxf`.

- `area` é área livre do ambiente, não projeção externa;
  corredores e paredes são contabilizados separadamente.
- O gerador exige sala com entrada externa, corredor para os demais cômodos,
  paredes de 15 cm e dimensões internas mínimas preliminares configuradas no
  código. Rejeita geometria inviável em vez de desenhá-la silenciosamente.
- Os recuos indicados pelo usuário são **dados de entrada**, não confirmação
  de permissibilidade urbanística. Sem dados do lote, o contorno é ilustrativo.
- A geometria não certifica acessibilidade, desempenho, segurança, iluminação,
  ventilação, aprovação legal ou atendimento a normas municipais.
- O backend usa um estado DXF efêmero compartilhado no processo; **não use
  concorrência de usuários/projetos em produção** antes do isolamento de sessão.

Rode os testes com `python -m pip install -e ./cloud/ezdxf pytest` e
`PYTHONPATH=cloud/ezdxf python -m pytest cloud/ezdxf/tests -q`.

### Evolução 2D: disposição compacta de dois quartos

Para programas com exatamente dois quartos, sala, cozinha, lavanderia e
banheiro, e largura externa entre 8,70 e 9,30 m, a estratégia
`automatico` seleciona o layout `compacto_2quartos`. A solução usa sala
e cozinha integradas, lavanderia delimitada, hall curto e acessos diretos
a dois dormitórios e ao banheiro. Cada área solicitada continua identificada
no modelo e o DXF inclui mobiliário esquemático, vãos e arcos de portas.
Layouts incompatíveis não devem receber declarações de conformidade.

Estratégias de `programa`:
- `automatico`: selecionar o compacto apenas quando houver compatibilidade;
  caso contrário, usa o arranjo experimental anterior;
- `compacto_2quartos`: exigir o algoritmo compacto, com erro explícito
  quando o programa não for viável;
- `duas_faixas`: preservar a distribuição histórica apenas para testes.

As duas estratégias são **estudos preliminares**, não plantas prontas para
obra. Área de ambientes cadastrados, área mapeada, projeção construída e área
total efetiva têm definições distintas. A planta não prova legalidade,
acessibilidade, ventilação, implantação, posicionamento de equipamentos
hidrossanitários, distâncias de uso ou segurança contra incêndio.

O script `tools/render_cloud_previews.py` compara as duas soluções antigas e
a solução compacta em PNG, gerando também DXF e JSON da geometria. O GitHub
Actions publica o pacote como artefato `plantas-previas-pr1`, para revisão
antes do merge.

## Exportação DXF: links reais para auditoria independente

`export_dxf(workspace_token="...")` devolve **dois URLs HTTPS temporários**:
`download_url` para `desenho.dxf.zip` e `dxf_url` para `desenho.dxf`.
Os bytes correspondem exatamente ao DXF produzido pelo `ezdxf`.
Para conferir integridade, compare `sha256_dxf` e `sha256_zip` com os
hashes dos arquivos baixados. Os links expiram após 15 minutos.

No Claude, após gerar a planta, execute o export e **abra ou baixe o URL
retornado** imediatamente. O download não exige reescrever base64 nem ter
`ezdxf` instalado no ambiente do chat. Para análise geométrica independente,
abra o DXF no programa CAD local ou em Python com `ezdxf`.

Caso um cliente antigo dependa de base64, existe a opção
`export_dxf(incluir_base64=true)`; o padrão agora é `false` para evitar
respostas enormes que não podem ser salvas confiavelmente.

O endpoint `/downloads/{token}/{fmt}` disponibiliza os arquivos somente
em memória e limita quantidade, bytes e prazo de armazenamento. O URL é uma
credencial temporária: **qualquer pessoa com esse link pode acessar o arquivo**
até a expiração. Este servidor permanece sem autenticação e é **só para
desenhos de teste**, não para projetos confidenciais. Os arquivos desaparecem
ao reiniciar o serviço ou expirar.

## Compatibilidade com MCP HTTP moderno — sem sessão persistente

Clientes ChatGPT e Claude podem usar o protocolo MCP HTTP mais recente
(2026-07-28), que **não envia** o antigo cabeçalho `Mcp-Session-Id`.

No primeiro comando, como `cad_status`, `new_drawing` ou
`planta_criar_validada(modo="preview")`, o servidor devolve um
`workspace_token` aleatório e temporário. Para manter o mesmo desenho
nas chamadas posteriores, passar esse mesmo argumento a cada ferramenta:

1. `planta_criar_validada(programa=..., modo="preview")`
   -> guardar `preview_token` **e** `workspace_token`.
2. `planta_criar_validada(programa=..., modo="desenhar",
   preview_token=..., workspace_token=...)`.
3. `drawing_audit(workspace_token=...)`.
4. `export_dxf(workspace_token=...)`.

Não confundir `preview_token` (autorização de uso único para transformar
a prévia em desenho) com `workspace_token` (referência opaca ao arquivo
DXF temporário). Não divulgar tokens nem usá-los em outros chats.
Clientes com sessão HTTP antiga continuam funcionando sem esse parâmetro.
O modo sem autenticação permanece experimental: quem possuir o token de
um workspace poderá acessá-lo até ele expirar (1 h).

## Uso online temporário sem autenticação (modo de teste)

Nesta PR, `MCP_CAD_AUTH_MODE` usa o valor padrão `off`. O serviço
**não exige usuário, senha, token Bearer nem `MCP_CAD_API_KEY`** no
modo de teste. Isso simplifica a conexão ao ChatGPT/Claude Online.

- No Render, deixar `MCP_CAD_AUTH_MODE=off` (ou não definir a variável).
- Manter o perfil `MCP_CAD_PROFILE=planta_segura`, quando possível.
- O acesso não é privado: **qualquer pessoa com a URL pode chamar o MCP**.
  Não colocar desenhos confidenciais ou dados pessoais no serviço público.
- O isolamento de desenhos por `Mcp-Session-Id`, tokens de aprovação
  de uso único, TTL 1 h, limite de 64 sessões e bloqueio das operações
  não implementadas continuam ativos. Esses controles não substituem
  autenticação nem impedem todo abuso ou negação de serviço.
- Caso o cliente não envie identificador de sessão estável, o comando
  recusa manipular o desenho remoto para impedir mistura entre usuários.
- Desenhos são voláteis: sempre exportar DXF antes de desconectar.

Para reativar autenticação futuramente **sem alterar código**:

1. Definir `MCP_CAD_AUTH_MODE=required` no Render.
2. Configurar `MCP_CAD_API_KEY` com 32+ caracteres aleatórios.
3. Conectar Claude/ChatGPT com cabeçalho
   `Authorization: Bearer <chave>` ou `X-MCP-CAD-API-KEY`, se suportado.

Não publicar dados privados em modo `off`. A validação real dos
conectores e a revisão de segurança ainda são pré-requisitos antes de
declarar o sistema pronto para produção.

### Convenção geométrica do layout compacto

Os parâmetros de `largura` e `profundidade` representam **faces
externas** da edificação. As paredes perimetrais têm eixo deslocado
para dentro em meia espessura. As cadeias de cotas externas, a área
de projeção e os recuos referenciam o contorno construído, não eixos
de paredes. As áreas internas referenciam as faces livres. A estratégia
antiga `duas_faixas` permanece experimental e deve ser tratada como
estudo geométrico não aprovado, sem promessa de dimensões externas.

## Laboratório automatizado de plantas

Para executar a matriz localmente no PowerShell, a partir da raiz do
repositório:

```powershell
$env:PYTHONPATH = "cloud/ezdxf"
$env:MCP_CAD_PROFILE = "full"
python -m pytest cloud/ezdxf/tests -q
python tools/run_plant_lab.py --output out/plant-lab
python tools/run_licensing_corpus.py --output out/licensing-corpus
```

O laboratório cria 30 programas que passam pela validação estrita de
prévia, variando áreas de ambientes, largura da casa e implantação no
lote. Também verifica 12 entradas inválidas e 10 corrupções controladas
de DXF. Cada caso válido é desenhado, auditado, salvo e reaberto com
`ezdxf`; a geometria física é comparada com expectativas independentes,
e conectividade e interferências são registradas junto à auditoria do
produto. A largura de passagem independente é uma estimativa por malha
em 5, 10 e 15 cm e não representa medição ou conformidade normativa.

O diretório de saída contém `report.json` e `report.md`, os DXFs, PDFs e
PNGs selecionados, uma folha de contato, duas execuções naturais do
manipulador da ferramenta e a comparação visual de circulação original/proposta.
O teste HTTP separado percorre `initialize`, `tools/list`, `tools/call` e os
downloads no transporte MCP real. A proposta é exportada sem ser aplicada ao
desenho original. O workflow de CI publica
esses arquivos como artefato `plant-generation-lab` por 30 dias.

O corpus arquitetônico separado usa 30 programas aceitos pelo validador
estrito e dez casos adversariais. Reabre e audita DXF da planta e das folhas,
verifica as nove vistas, cotas gerais, programa/áreas, portas, janelas,
mobiliário e circulação. O relatório contabiliza avisos por código e inclui
PDF/PNG de amostra e folha de contato; CI publica `residential-licensing-corpus`
por 30 dias. Isso cobre regressões do escopo implementado, não aprovação
normativa ou municipal.

Limites de medição: o DXF ainda não grava polígonos fechados por cômodo;
por isso a comparação de áreas verifica as cotas textuais do arquivo, não
áreas físicas medidas de contornos. Os desenhos são estudos preliminares
e não recebem nota subjetiva de qualidade, aprovação arquitetônica,
acessibilidade ou conformidade legal.

## Pacote arquitetônico para revisão de licenciamento

A ferramenta MCP `projetar_pacote_licenciamento` gera pranchas arquitetônicas
editáveis para uma residência térrea compacta de dois quartos. Recebe o
programa, contexto do município, envelope vertical, lista de vistas/folhas e
dados do carimbo. Cada DXF é serializado, reaberto e auditado antes de entrar
no ZIP com PDF, PNG e relatórios JSON/Markdown. O MCP HTTP retorna links
temporários para a primeira prancha e para o conjunto.

Se `folhas` for omitido, a ferramenta cria quatro folhas A3: planta baixa,
implantação/cobertura, dois cortes e quatro fachadas, com escalas declaradas.
O usuário ainda pode fornecer uma composição própria. A planta traz cotas
externas da edificação; o pacote ainda não contém quadro completo de
esquadrias, detalhes construtivos, notas específicas da prefeitura ou cotas
internas.

Na planta baixa, os eixos ortogonais de parede são representados pelas duas
faces paralelas, espaçadas pela espessura declarada no modelo, e pelos
fechamentos transversais nos extremos dos segmentos/vãos. A auditoria da folha
reaberta conserva IDs separados para as duas faces e detecta a remoção de uma
delas. Essa representação 2D não adiciona hachura de material ou composição
construtiva.

O registro `mcp_cad_cloud/normas_arquitetura.json` é um inventário pequeno e
explicitamente não exaustivo de normas candidatas. Em 29/10/2026, a ficha
ABNT/Sebrae consultada informa a ABNT NBR 9050:2020 Versão Corrigida:2021 como
vigente, confirmada em 11/12/2025. Isso confirma apenas os metadados da ficha;
nenhum texto protegido foi copiado ou usado para implementar critério. As
demais entradas continuam com status não confirmado quando não foi obtida
uma ficha oficial detalhada nesta revisão. Nenhum item possui avaliador de
critério, portanto a ferramenta registra os requisitos como `não testável` e
mantém a situação em `review_required`.

Preencha município/UF e os campos do carimbo com dados fornecidos pelo usuário.
Para avaliação local, crie um perfil municipal versionado com fonte oficial,
data de consulta e revisor; sem isso, a legislação municipal é `não testável`.
Antes de cadastrar qualquer verificador normativo, confirme a edição/status no
catálogo ABNT, obtenha acesso autorizado ao texto, registre referência de
critério e evidência, e crie testes positivos e adversariais independentes.
O pacote requer revisão de profissional habilitado e não declara conformidade
integral, aprovação de prefeitura ou prontidão para construção. Elétrica,
hidráulica, sanitária, estrutural, incêndio e demais projetos complementares
seguem fora do escopo desta etapa.
