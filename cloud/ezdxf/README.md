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
