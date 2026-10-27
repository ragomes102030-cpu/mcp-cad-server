# Planta assistida para agentes pequenos

## Objetivo

`planta_assistida` é a ferramenta de alto nível do MCP local. Ela recebe um programa controlado, monta a geometria paramétrica, valida os ambientes e só então desenha no AutoCAD 2025 via COM. No modo desenho, o MCP pode iniciar o `acad.exe`, aguardar o COM e começar a desenhar sem exigir que o usuário abra o AutoCAD manualmente.

O primeiro template suporta a residência unifamiliar de 12,00 x 11,00 m, com paredes de 0,15 m, pé-direito de 2,80 m e dez ambientes:

- sala de estar/jantar;
- cozinha;
- área de serviço;
- banheiro social;
- circulação;
- quarto 2;
- quarto 3;
- suíte;
- banheiro da suíte;
- hall/closet.

## Protocolo recomendado

1. Chame `planta_assistida` com `modo="preview"`.
2. Confira `ok`, `validacao`, `resumo.area_util` e `resumo.areas`.
3. Só depois chame a mesma ferramenta com `modo="desenhar"`; por padrão, ela abre o AutoCAD se necessário.
4. Audite o retorno e salve usando a ferramenta de desenho do MCP.

Exemplo mínimo:

```json
{
  "programa": {
    "titulo": "PLANTA TESTE - RESIDÊNCIA UNIFAMILIAR",
    "area_util_minima": 100
  },
  "modo": "preview"
}
```

Para desenhar no AutoCAD local:

```json
{
  "programa": {
    "titulo": "PLANTA TESTE - RESIDÊNCIA UNIFAMILIAR"
  },
  "modo": "desenhar"
}
```

O agente não precisa chamar `new_drawing` nem descobrir coordenadas individualmente. A ferramenta inicia o AutoCAD 2025, espera o backend COM, cria um documento novo e desenha o modelo inteiro. Para exigir que o AutoCAD já esteja aberto, passe `"abrir_autocad": false`. O tempo de espera pode ser ajustado com `"timeout_s": 90`.

## Guardrails

- O `preview` não abre nem modifica desenho.
- O modo `desenhar` inicia `acad.exe` somente no MCP local e aguarda o COM; o cloud não tem essa capacidade.
- O programa é rejeitado antes de qualquer chamada ao backend quando há ambiente desconhecido, ambiente ausente, dimensão externa incompatível, parede diferente de 0,15 m ou pé-direito fora da faixa permitida.
- `desenhar` exige `autocad_com`. O servidor não converte silenciosamente para ezdxf.
- O desenho começa em um documento novo do AutoCAD; a planta ativa anterior não é apagada.
- A validação impede a criação quando há erro de geometria, porta sem vão, parede inválida ou texto incompatível com o ambiente.
- Paredes do template são renderizadas por faces/cabeceiras únicas, e não por retângulos independentes; os vãos de portas e janelas ficam realmente livres.
- A validação também rejeita folha de porta que atravesse outra parede. Aberturas externas são descontadas do eixo da parede antes do desenho.
- As cotas são geradas nas duas fachadas horizontais: frente `5,00 / 3,60 / 3,40 / 12,00` e fundo `4,60 / 4,00 / 3,40 / 12,00`.

## Limite do template

O primeiro template é deliberadamente fechado para dar previsibilidade a modelos menores. Para outras dimensões ou outro programa, crie um novo template validado em vez de permitir que o agente altere coordenadas livremente.
