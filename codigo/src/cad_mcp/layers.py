# -*- coding: utf-8 -*-
"""Padrão de camadas (base ABNT/escritório) usado pelo gerador de plantas."""
from __future__ import annotations

# nome -> (cor ACI, tipo de linha)
LAYER_STANDARD: dict[str, tuple[int, str]] = {
    "PAREDES":    (4, "CONTINUOUS"),   # ciano
    "PORTAS":     (3, "CONTINUOUS"),   # verde
    "JANELAS":    (5, "CONTINUOUS"),   # azul
    "MOBILIARIO": (9, "CONTINUOUS"),   # cinza claro
    "HACHURA":    (8, "CONTINUOUS"),   # cinza escuro
    "COTAS":      (1, "CONTINUOUS"),   # vermelho
    "TEXTOS":     (7, "CONTINUOUS"),   # preto/branco
    "TERRENO":    (6, "CONTINUOUS"),   # magenta
    "EIXOS":      (2, "CENTER"),       # amarelo, linha de centro
    "PROJECAO":   (2, "DASHED"),       # amarelo tracejado
    "ESQUADRIAS_COTA": (1, "CONTINUOUS"),
}


async def ensure_standard_layers(backend) -> dict:
    """Cria (idempotente) o conjunto padrão de camadas e devolve o que foi feito.

    Carrega os LTYPEs nao-CONTINUOUS antes: `layer_create` recusa a camada se o
    tipo de linha nao existe na tabela, e o desenho sai sem linha de centro.
    """
    criadas, existentes, erros = [], [], []
    for _nome, (_cor, lt) in LAYER_STANDARD.items():
        if lt and lt.upper() != "CONTINUOUS":
            try:
                rl = await backend.layer_linetype_load(lt)
                if not rl.ok:
                    erros.append({"camada": _nome, "erro": "linetype %s: %s" % (lt, rl.error)})
            except Exception as exc:  # noqa: BLE001 - segue; layer_create reporta de novo
                erros.append({"camada": _nome, "erro": "linetype %s: %s" % (lt, exc)})
    for nome, (cor, lt) in LAYER_STANDARD.items():
        try:
            r = await backend.layer_create(nome, color=cor, linetype=lt)
            _ex = (r.payload or {}).get("existed") if isinstance(r.payload, dict) else False
            (criadas if r.ok and not _ex else existentes).append(nome)
        except Exception as exc:  # pragma: no cover
            erros.append({"camada": nome, "erro": str(exc)})
    return {"criadas": criadas, "ja_existiam": existentes, "erros": erros,
            "padrao": {k: {"cor": v[0], "linetype": v[1]} for k, v in LAYER_STANDARD.items()}}
