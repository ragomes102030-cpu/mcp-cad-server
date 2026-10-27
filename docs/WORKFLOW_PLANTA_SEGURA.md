# Workflow obrigatório para plantas

O MCP deve ser tratado como um construtor paramétrico, não como uma lista de
linhas CAD. O agente escolhe o programa; o servidor calcula a geometria,
valida e só então grava o desenho.

## Fluxo

1. `cad_status`
2. `planta_templates`
3. `planta_criar_validada(modo="preview", programa={...})`
4. conferir `ok`, `validacao`, `resumo` e `preview_token`
5. `planta_criar_validada(modo="desenhar", preview_token="...")`
6. `inspect_drawing`, `quantitativo` e exportação

O token expira em 15 minutos, é vinculado ao template e ao modelo completo e
só pode ser consumido uma vez. Desenhar sem preview retorna
`WORKFLOW_REQUIRED`; alterar o modelo depois do preview retorna
`PREVIEW_TOKEN_INVALID`.

## Perfil seguro

O perfil padrão `planta_segura` publica as ferramentas de criação e validação
de plantas e oculta primitivas como `draw_line` e `draw_rectangle`. Isso evita
que modelos menores construam uma planta por retângulos independentes e criem
sobreposição nos encontros das paredes.

Para CAD avançado explícito, iniciar o servidor com:

```text
MCP_CAD_PROFILE=full
```

Esse perfil não deve ser usado para o fluxo comum de plantas residenciais.

## Regra geométrica

Paredes são geradas por eixo, espessura e vãos. O motor unifica os encontros e
desenha os segmentos de contorno, evitando áreas duplicadas. O validador bloqueia
paredes colineares sobrepostas, portas sem vão, portas sobrepostas, móveis
conflitantes e textos sobre móveis antes de qualquer operação no AutoCAD.

## Diferença entre os servidores

- Local: perfil seguro e backend AutoCAD COM; pode abrir o AutoCAD conforme a
  configuração e exige documento/COM pronto para desenhar.
- Cloud: perfil seguro e backend ezdxf; trabalha em memória e exporta o DXF.

O contrato, os templates e as regras de validação devem permanecer iguais. Só o
adaptador de saída é diferente.
