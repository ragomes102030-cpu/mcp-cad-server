# -*- coding: utf-8 -*-
"""Leitor mínimo de s-expressions AutoLISP.

Usado para conversar com o AutoCAD via `vl-prin1-to-string`: o LISP devolve
uma forma LISP (ex.: `((0 . "LINE") (8 . "PAREDES"))`) e nós transformamos em
tipos Python. Cobre só o que o AutoCAD emite: listas, listas pontuadas,
strings com escape, números (int/float/cientifico), simbolos, nil e T.
"""
from __future__ import annotations

import re

__all__ = ["parse", "SexpError"]


class SexpError(ValueError):
    pass


_NUM = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


class _Leitor:
    def __init__(self, texto: str) -> None:
        self.t = texto
        self.i = 0

    # ---------------------------------------------------------------- basicos
    def _pular(self) -> None:
        while self.i < len(self.t) and self.t[self.i] in " \t\r\n":
            self.i += 1

    def _ler_string(self) -> str:
        assert self.t[self.i] == '"'
        self.i += 1
        out = []
        while self.i < len(self.t):
            c = self.t[self.i]
            if c == "\\":
                prox = self.t[self.i + 1] if self.i + 1 < len(self.t) else ""
                out.append({"n": "\n", "t": "\t", "r": "\r"}.get(prox, prox))
                self.i += 2
                continue
            if c == '"':
                self.i += 1
                return "".join(out)
            out.append(c)
            self.i += 1
        raise SexpError("string nao terminada")

    def _ler_atomo(self) -> str:
        ini = self.i
        while self.i < len(self.t) and self.t[self.i] not in ' \t\r\n()"':
            self.i += 1
        return self.t[ini:self.i]

    @staticmethod
    def _converter(atomo: str):
        if atomo == "":
            raise SexpError("atomo vazio")
        if _NUM.match(atomo):
            if re.search(r"[.eE]", atomo):
                return float(atomo)
            return int(atomo)
        low = atomo.lower()
        if low == "nil":
            return None
        if low in ("t", "true"):
            return True
        return atomo  # simbolo fica como texto

    # ------------------------------------------------------------------ lista
    def _ler(self):
        self._pular()
        if self.i >= len(self.t):
            raise SexpError("fim inesperado")
        c = self.t[self.i]
        if c == "(":
            self.i += 1
            return self._ler_lista()
        if c == ")":
            raise SexpError(") inesperado")
        if c == '"':
            return self._ler_string()
        return self._converter(self._ler_atomo())

    def _ler_lista(self) -> list:
        itens: list = []
        while True:
            self._pular()
            if self.i >= len(self.t):
                raise SexpError("lista nao fechada")
            if self.t[self.i] == ")":
                self.i += 1
                return itens
            if self.t[self.i] == "." and not _NUM.match(
                (self.t[self.i : self.i + 2]).strip()
            ):
                # lista pontuada (a . b) -> [a, b]  (uso raro; mantemos plano)
                self.i += 1
                continue
            itens.append(self._ler())


def parse(texto: str):
    """Converte a representacao textual de UMA forma LISP em Python."""
    if texto is None:
        return None
    texto = texto.strip()
    if not texto:
        return None
    leitor = _Leitor(texto)
    valor = leitor._ler()
    leitor._pular()
    return valor


def parse_all(texto: str) -> list:
    leitor = _Leitor(texto)
    out = []
    while True:
        leitor._pular()
        if leitor.i >= len(leitor.t):
            return out
        out.append(leitor._ler())
