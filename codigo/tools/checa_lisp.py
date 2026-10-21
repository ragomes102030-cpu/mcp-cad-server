# -*- coding: utf-8 -*-
"""Valida as expressoes LISP que o backend manda para o AutoCAD.

Motivo: um parentese fora de lugar em entity_offset deixou o AutoCAD travado
num laco, sem erro visivel (o texto virava "(if teste a b c)" -> erro de sintaxe
e a linha de comando ficava esperando). Contar parenteses NAO pega esse erro:
a contagem fecha, mas a arvore fica errada. Este script monta a arvore e
confere a aridade das formas especiais.

Uso:
    python checa_lisp.py
"""
import asyncio
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent / "src"
sys.path.insert(0, str(RAIZ))

import cad_mcp.com_backend as cb  # noqa: E402


# ---------------------------------------------------------------- tokenizador
def tokenizar(texto):
    tokens = []
    i = 0
    n = len(texto)
    while i < n:
        c = texto[i]
        if c in " \t\r\n":
            i += 1
        elif c == "(":
            tokens.append("(")
            i += 1
        elif c == ")":
            tokens.append(")")
            i += 1
        elif c == '"':
            j = i + 1
            while j < n:
                if texto[j] == "\\":
                    j += 2
                    continue
                if texto[j] == '"':
                    break
                j += 1
            tokens.append(texto[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < n and texto[j] not in ' \t\r\n()"':
                j += 1
            tokens.append(texto[i:j])
            i = j
    return tokens


def arvore(texto):
    pilha = [[]]
    for t in tokenizar(texto):
        if t == "(":
            pilha.append([])
        elif t == ")":
            if len(pilha) == 1:
                raise ValueError("fecha parenteses sem abrir")
            fechado = pilha.pop()
            pilha[-1].append(fechado)
        else:
            pilha[-1].append(t)
    if len(pilha) != 1:
        raise ValueError("faltam %d parenteses" % (len(pilha) - 1))
    return pilha[0]


def primeiro(no):
    if isinstance(no, list) and no and isinstance(no[0], str):
        return no[0].lower()
    return None


def validar(no, caminho="", erros=None):
    if erros is None:
        erros = []
    if not isinstance(no, list):
        return erros
    cabeca = primeiro(no)
    if cabeca == "if":
        # (if teste entao) ou (if teste entao senao)
        if len(no) not in (3, 4):
            erros.append("%s (if ...) com %d argumentos (esperado 2 ou 3): %r"
                         % (caminho, len(no) - 1, no[:2]))
    elif cabeca == "setq":
        if (len(no) - 1) % 2 != 0:
            erros.append("%s (setq ...) com numero impar de argumentos" % caminho)
    elif cabeca == "progn" and len(no) < 2:
        erros.append("%s (progn) vazio" % caminho)
    for i, filho in enumerate(no):
        validar(filho, "%s/%s[%d]" % (caminho, cabeca or "?", i), erros)
    return erros


# --------------------------------------------------------- captura de expressoes
class Captura:
    def __init__(self):
        self.expr = []

    def _aval(self, expr, timeout=30.0):
        self.expr.append(expr)
        return "CAPTURADO"

    def _eval(self, expr, timeout=30.0):
        self.expr.append(expr)
        return "CAPTURADO"


CASOS = [
    ("entity_move", ("1A", 1.0, 2.0)),
    ("entity_copy", ("1A", 1.0, 2.0)),
    ("entity_copy_filter", ("TESTE", None, 10.0, 0.0)),
    ("entity_copy_filter", ("TESTE", "LINE", 10.0, 0.0)),
    ("entity_rotate", ("1A", 0.0, 0.0, 90.0)),
    ("entity_mirror", ("1A", 0.0, 0.0, 0.0, 5.0)),
    ("entity_offset", ("1A", 0.25, 1)),
    ("entity_offset", ("1A", 0.25, -1)),
    ("entity_erase", ("1A",)),
    ("entity_erase_filter", ("TESTE", "LINE", None, True)),
    ("entity_list", ("TESTE", "LINE")),
]


def main():
    falhas = 0
    for nome, args in CASOS:
        cap = Captura()
        metodo = getattr(cb.ComBackend, nome, None)
        if metodo is None:
            print("[FALHA] %s nao existe" % nome)
            falhas += 1
            continue
        try:
            asyncio.run(metodo(cap, *args))
        except Exception as exc:
            print("[FALHA] %s nao chamou _aval: %r" % (nome, exc))
            continue
        if not cap.expr:
            print("[FALHA] %s nao chamou _aval" % nome)
            falhas += 1
            continue
        expr = cap.expr[0]
        erros = []
        try:
            arvore_ok = arvore(expr)
        except ValueError as exc:
            print("[FALHA] %-20s arvore invalida: %s" % (nome, exc))
            falhas += 1
            continue
        validar(arvore_ok, erros=erros)
        if erros:
            falhas += 1
            print("[FALHA] %-20s %s" % (nome, erros[0]))
            for e in erros[1:]:
                print("        %s" % e)
        else:
            print("[OK]    %-20s %d chars" % (nome, len(expr)))
    print()
    print("RESULTADO: %s" % ("OK" if falhas == 0 else "%d EXPRESSAO(OES) COM PROBLEMA" % falhas))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
