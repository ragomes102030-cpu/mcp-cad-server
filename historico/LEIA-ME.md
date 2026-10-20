# histórico de falhas

`ocorrencias.jsonl` — uma linha JSON por falha. **Append-only**: nunca reescrevemos
linha antiga. Contar ocorrências = contar linhas.

```
quando   chave            sintoma
2026-10-16  arco-graus-em-radianos  arco de 90 saiu 116,62
2026-10-16  selo-transborda         selo de 130 chars esmagou o A3
```

## Para que serve

Não é diário. É a **matéria-prima** de duas coisas:

1. **verificação** — quando um sintoma chega à 3ª ocorrência, vira checagem em
   `src/cad_mcp/validar_modelo.py` (mesma `chave`), que roda em ~1 ms antes do
   AutoCAD;
2. **regra de código** — sintomas que nenhum modelo JSON explica (arco em
   radianos, `(load)` travando o COM, DWG que não sobrescreve) ficam registrados
   com `contexto.corrigido_em` apontando o arquivo.

A regra das 3 ocorrências existe para não transformar um typo em lei. Antes da
terceira, o sintoma é **observação**.

## Comandos

```powershell
cd C:\Users\Correta Engenharia\mcp-cad-server
$env:PYTHONPATH="src"
python -m cad_mcp.historico                 # tabela
python -m cad_mcp.historico --chave X       # sintoma, evidência, correção
python -m cad_mcp.historico --json          # para processar
```

Registrar (dentro do código que falhou — durante a tarefa, não depois):

```python
from cad_mcp.historico import registrar
registrar("porta-sem-vao", "arco desenhado sobre parede fechada",
          modelo=recorte, contexto={"arquivo": "x.dwg"},
          sugestao="abrir o vão no eixo")
```

## Arquivos

| arquivo | o que é |
|---|---|
| `ocorrencias.jsonl` | o log (não editar à mão; use `registrar`/`limpar`) |
| `../src/cad_mcp/historico.py` | escrita, contagem, `promovidos()` |
| `../src/cad_mcp/validar_modelo.py` | as verificações promovidas |
| `../tests/validar_modelo_teste.py` | regressão: modelo bom passa, mutação reprova |

Explicação completa do ciclo: skill `cad-planta-autocad`, `references/falhas.md`.
