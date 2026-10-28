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
