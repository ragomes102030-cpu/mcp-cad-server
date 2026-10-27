# Evolução do MCP para plantas paramétricas

## Regra de execução

O agente deve trabalhar em duas etapas:

1. chamar `validar_planta` ou `planta_assistida(modo="preview")`;
2. somente com `ok=true`, chamar `planta_assistida(modo="desenhar")`.

O MCP bloqueia o desenho quando encontra erros geométricos. A validação cobre:

- paredes colineares sobrepostas ou duplicadas;
- portas sem parede, sem vão ou com vãos sobrepostos;
- janelas sem vão correspondente;
- ambientes sobrepostos ou degenerados;
- mobiliário inválido, sobreposto ou fora de ambiente;
- rótulo de ambiente sobre mobiliário.

## Limite de cada backend

- **Local:** pode abrir o AutoCAD 2025 e desenhar no documento vivo via COM.
- **Cloud:** gera e exporta DXF com ezdxf; não abre nem controla o AutoCAD do computador.

Os dois backends devem receber o mesmo modelo paramétrico e devolver os mesmos
códigos de validação. Diferenças de capacidade devem aparecer no campo
`backend`, nunca como falso sucesso.

## Contrato recomendado para agentes menores

```text
1. Gere o modelo JSON da planta.
2. Chame validar_planta(modelo=...).
3. Se ok=false, corrija somente os itens listados em validacao.erros.
4. Repita a validação.
5. Chame planta_assistida(modo="desenhar") apenas após ok=true.
6. Faça auditoria e salve/exporte o resultado.
```
