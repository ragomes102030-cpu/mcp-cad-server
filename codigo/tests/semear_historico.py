# -*- coding: utf-8 -*-
"""Semeia o historico com as falhas REAIS desta primeira planta.

Nao e exemplo didatico: cada entrada aconteceu de verdade em 16/10/2026,
com o sintoma exato que apareceu na tela. Serve para o historico nao comecar
vazio e para mostrar o formato de uma ocorrencia util (sintoma + evidencia +
sugestao + o que foi corrigido).

Rodar uma vez:  python tests/semear_historico.py
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from cad_mcp.historico import registrar, vezes, formatar_tabela  # noqa: E402


def semear(chave: str, sintoma: str, **kw) -> None:
    """Idempotente: rodar de novo NAO infla a contagem (e nao promove por engano)."""
    if vezes(chave):
        print("  ja registrado, pulando: %s" % chave)
        return
    registrar(chave, sintoma, **kw)


def main() -> int:    # 1. O arco de 90 graus que saiu com 116,620156...
    semear(
        "arco-graus-em-radianos",
        "arco pedido a 90 graus (entmake grupo 50) saiu com 116,620156177409 graus",
        sugestao="grupos 50/51 de entmake/entget esperam RADIANOS; usar (angtof \"90\") "
                 "no LISP e math.radians no Python. Grau pedido x pi/180 = radiano gravado.",
        contexto={
            "evidencia": "90 rad mod 2pi = 2,0354 rad = 116,6201 graus (bate exato)",
            "sonda": "tests/probe_arco4.py (cria ARC+TEXT, salva, exporta DXF, le de volta)",
            "corrigido_em": "planta.py:_rad + com_backend.create_arc/create_text/block_insert",
            "aprendizado": "entget devolve o MESMO numero que o DXF mostra em graus; "
                           "a confusao e entre o que o LISP recebe e o que o arquivo grava",
        },
    )

    # 2. O selo de 130 caracteres que esmagou o A3.
    semear(
        "selo-transborda",
        "selo com linhas de ~130 chars a 0,22 m ocupou ~18 m de papel; plot por Extents "
        "reduziu a planta inteira e a folha saiu 287x227 mm com desenho minusculo",
        sugestao="medir antes: largura ~ 0,9 x altura x n_chars (txt.shx maiusculo). "
                 "Quebrar o selo em linhas <= 70 chars e reduzir a altura.",
        contexto={
            "medida": "avanco real do txt.shx maiusculo ~= 0,9 x altura (nao 0,6)",
            "corrigido_em": "SELO reescrito em 8 linhas <= 70 chars (0,22 -> 0,16 m)",
            "resultado": "A3 volta a 286x295 mm, tinta 2,21%, margens 5,1/6,1 mm",
        },
    )

    # 3. Salvar por cima de um DWG aberto.
    semear(
        "dwg-nao-sobrescreve",
        "drawing_save no mesmo nome de um DWG ja aberto devolve 'Error saving the document'",
        sugestao="salvar em nome livre: tentar, se falhar tentar _2, _3; nunca assumir "
                 "que o nome pedido foi aceito",
        contexto={"corrigido_em": "skill render_planta.py (loop de sufixos) e tests/planta_3q.py",
                  "detalhe": "o erro e do AutoCAD; o arquivo no disco continua o antigo"},
    )

    # 4. Ler DXF antes de salvar.
    semear(
        "dxf-antes-de-salvar",
        "accoreconsole exportou DXF sem os arcos recem-criados; parecia que o entmake nao criava ARC",
        sugestao="accoreconsole le o ARQUIVO no disco, nao a sessao na memoria: "
                 "drawing_save SEMPRE antes de drawing_save_as_dxf",
        contexto={"falso_diagnostico": "concluimos 'arcos nao existem no DXF' por ordem de teste errada",
                  "corrigido_em": "ordem do pipeline em planta_3q.py e render_planta.py"},
    )

    # 5. (load "x.lsp") travando o COM.
    semear(
        "load-lsp-trava-com",
        "(load \"x.lsp\") abriu o dialogo de SECURELOAD e o COM passou a devolver "
        "RPC_E_CALL_REJECTED (0x80010001) em toda chamada",
        sugestao="nunca carregar arquivo LISP; enviar o LISP inline via SendCommand, "
                 "com wrap em vl-catch-all-apply",
        contexto={"corrigido_em": "com_backend._lisp (inline, sem arquivo)"},
    )

    print(formatar_tabela())
    print("\nhistorico semeado em historico/ocorrencias.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

