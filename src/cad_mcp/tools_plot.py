# -*- coding: utf-8 -*-
"""Primitivas de prancha: viewports, xref, imagem, DWG e fechamento de documento.

Armadilhas do ActiveX confirmadas no AutoCAD 2025 e que explicam o codigo abaixo:
`AddPViewport` nao existe no Block do layout (falha com "unknown name"); o
viewport tem de nascer pelo comando `MVIEW`, que exige TILEMODE=0 e o layout
ativo. `IMAGEATTACH`/`XREF` abrem dialogo e travam o SendCommand por 30 s quando
FILEDIA=1, por isso a variavel e' zerada e restaurada dentro da mesma expressao.
"""
from __future__ import annotations

import os
from pathlib import Path

from .backend_manager import MANAGER


def _doc() -> str:
    return "(vla-get-activedocument (vlax-get-acad-object))"


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _pares(v) -> dict:
    if isinstance(v, dict):
        return {str(k).lower(): x for k, x in v.items()}
    saida = {}
    if isinstance(v, (list, tuple)):
        for item in v:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                saida[str(item[0]).lower()] = item[1]
    return saida


async def _b():
    return await MANAGER.get()


async def _aval(code: str) -> dict:
    b = await _b()
    if not hasattr(b, "_aval"):
        return {"ok": False,
                "erro": "backend '%s' nao executa LISP/VLA; abra o AutoCAD"
                        % getattr(b, "name", "?")}
    try:
        r = b._aval(code)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "erro": str(exc)}
    return r.to_dict() if hasattr(r, "to_dict") else {"ok": True, "payload": r}


def _layout(nome: str, var: str = "__ly") -> str:
    return ('(setq %s nil) (vlax-for __x (vla-get-layouts %s)'
            ' (if (= (strcase (vla-get-name __x)) (strcase "%s")) (setq %s __x)))'
            % (var, _doc(), _esc(nome), var))


def _por_handle(handle: str, var: str = "__vp") -> str:
    return ('(setq %s (vl-catch-all-apply (function (lambda () (vlax-ename->vla-object (handent "%s"))))))'
            ' (if (or (vl-catch-all-error-p %s) (null %s)) (setq %s nil))'
            % (var, _esc(handle), var, var, var))


def _com_filedia(corpo: str) -> str:
    return ('(progn (setq __fd (getvar "FILEDIA")) (setvar "FILEDIA" 0)'
            ' (setq __r (vl-catch-all-apply (function (lambda () %s))))'
            ' (setvar "FILEDIA" __fd)'
            ' (if (vl-catch-all-error-p __r) (strcat "MCPERRO:" (vl-catch-all-error-message __r)) __r))'
            % corpo)


async def viewport_list(layout: str = "Layout1") -> dict:
    """Lista viewports do paper space: handle, numero, tamanho, escala e trava."""
    lisp = (
        '(progn %s (if (null __ly) "MCPERRO:layout nao existe"'
        ' (progn (setq __o nil)'
        '  (vlax-for __v (vla-get-block __ly)'
        '   (if (= (vla-get-objectname __v) "AcDbViewport")'
        '    (setq __o (cons (list'
        '      (cons "handle" (vla-get-handle __v))'
        '      (cons "numero" (vl-princ-to-string (vl-catch-all-apply (function (lambda () (vla-get-number __v))))))'
        '      (cons "largura" (rtos (vla-get-width __v) 2 4))'
        '      (cons "altura" (rtos (vla-get-height __v) 2 4))'
        '      (cons "escala" (rtos (vla-get-customscale __v) 2 6))'
        '      (cons "travado" (if (= (vla-get-displaylocked __v) :vlax-true) "1" "0"))'
        '     ) __o))))'
        '  (reverse __o))))' % _layout(layout)
    )
    r = await _aval(lisp)
    if r.get("ok") and isinstance(r.get("payload"), list):
        r["viewports"] = [_pares(v) for v in r["payload"]]
    return r


async def viewport_create(layout: str = "Layout1", cx: float = 100.0, cy: float = 100.0,
                          largura: float = 180.0, altura: float = 120.0,
                          escala: float | None = None) -> dict:
    """Cria viewport de modelo no paper space via MVIEW, centrado em (cx, cy) mm."""
    x1, y1 = cx - largura / 2.0, cy - altura / 2.0
    x2, y2 = cx + largura / 2.0, cy + altura / 2.0
    lisp = (
        '(progn %s (if (null __ly) "MCPERRO:layout nao existe"'
        ' (progn'
        '  (vl-catch-all-apply (function (lambda () (vla-put-activelayout %s __ly))))'
        '  (setvar "TILEMODE" 0)'
        '  (setq __ant (entlast))'
        '  (command "_.MVIEW" (list %s %s 0.0) (list %s %s 0.0))'
        '  (setq __e (entlast))'
        '  (if (eq __e __ant) "MCPERRO:MVIEW nao criou viewport"'
        '   (progn (setq __vp (vlax-ename->vla-object __e))'
        '    %s'
        '    (vla-get-handle __vp))))))'
        % (_layout(layout), _doc(), x1, y1, x2, y2,
           ('(vl-catch-all-apply (function (lambda () (vla-put-customscale __vp %s))))' % float(escala))
           if escala is not None else '')
    )
    return await _aval(lisp)


async def viewport_delete(layout: str, handle: str) -> dict:
    """Apaga um viewport pelo handle. O viewport 1 (a folha) nao pode sair."""
    lisp = (
        '(progn %s (if (null __vp) "MCPERRO:viewport %s nao existe"'
        ' (if (and (not (vl-catch-all-error-p (vl-catch-all-apply (function (lambda () (vla-get-number __vp)))) ))'
        '          (= (vl-catch-all-apply (function (lambda () (vla-get-number __vp)))) 1))'
        '  "MCPERRO:viewport 1 e a folha; nao pode ser apagado"'
        '  (progn (vla-delete __vp) T))))'
        % (_por_handle(handle), _esc(handle))
    )
    return await _aval(lisp)


async def viewport_set_scale(layout: str, handle: str, escala: float) -> dict:
    """Recalibra o viewport: 1:50 => escala 50 (CustomScale)."""
    lisp = (
        '(progn %s (if (null __vp) "MCPERRO:viewport %s nao existe"'
        ' (progn (vla-put-customscale __vp %s) (rtos (vla-get-customscale __vp) 2 6))))'
        % (_por_handle(handle), _esc(handle), float(escala))
    )
    return await _aval(lisp)


async def viewport_lock(layout: str, handle: str, travar: bool = True) -> dict:
    """Trava/destrava a escala do viewport (DisplayLocked)."""
    lisp = (
        '(progn %s (if (null __vp) "MCPERRO:viewport %s nao existe"'
        ' (progn (vla-put-displaylocked __vp %s) T)))'
        % (_por_handle(handle), _esc(handle), ":vlax-true" if travar else ":vlax-false")
    )
    return await _aval(lisp)


async def xref_attach(path: str, x: float = 0.0, y: float = 0.0,
                      scale: float = 1.0, rotation: float = 0.0) -> dict:
    """Anexa um DWG/DXF como referencia externa no ponto (x, y)."""
    if not os.path.exists(path):
        return {"ok": False, "erro": "arquivo nao encontrado: %s" % path}
    return await _aval(_com_filedia(
        '(progn (command "_.XATTACH" "%s" (list %s %s 0.0) %s %s) T)'
        % (_esc(path.replace("\\", "/")), x, y, scale, rotation)
    ))


async def xref_manage(name: str, operacao: str = "reload", novo_path: str | None = None) -> dict:
    """Uma operacao sobre uma xref: reload | unload | detach | path."""
    op = operacao.lower()
    mapa = {"reload": '"_R"', "recarregar": '"_R"',
            "unload": '"_U"', "descarregar": '"_U"',
            "detach": '"_D"', "desanexar": '"_D"'}
    if op in ("path", "caminho"):
        if not novo_path:
            return {"ok": False, "erro": "operacao 'path' exige novo_path"}
        return await _aval('(progn (command "_.-XREF" "_P" "%s" "%s") T)'
                           % (_esc(name), _esc(novo_path.replace("\\", "/"))))
    if op not in mapa:
        return {"ok": False, "erro": "operacao invalida: %r (use reload/unload/detach/path)" % operacao}
    return await _aval('(progn (command "_.-XREF" %s "%s") T)' % (mapa[op], _esc(name)))


async def image_attach(path: str, x: float = 0.0, y: float = 0.0,
                       scale: float = 1.0, rotation: float = 0.0) -> dict:
    """Anexa imagem raster (PNG/JPG/TIF) no ponto (x, y)."""
    if not os.path.exists(path):
        return {"ok": False, "erro": "imagem nao encontrada: %s" % path}
    return await _aval(_com_filedia(
        '(progn (command "_.IMAGEATTACH" "%s" (list %s %s 0.0) %s %s) T)'
        % (_esc(path.replace("\\", "/")), x, y, scale, rotation)
    ))


async def drawing_export_dwg(path: str) -> dict:
    """Grava o desenho como DWG nativo (nao DXF renomeado)."""
    if not path.lower().endswith(".dwg"):
        path = path + ".dwg"
    alvo = Path(path).expanduser()
    alvo.parent.mkdir(parents=True, exist_ok=True)
    b = await _b()
    r = await b.drawing_save(path=str(alvo))
    return r.to_dict() if hasattr(r, "to_dict") else {"ok": bool(r)}


def _fechar_lisp(salvar: bool, forcar: bool) -> str:
    guarda = "" if forcar else (
        '(if (<= (vla-get-count (vla-get-documents (vlax-get-acad-object))) 1)'
        ' "MCPERRO:ultimo desenho aberto; use forcar=True para fechar o AutoCAD")'
    )
    return ('(progn (setq __d %s) %s'
            ' (if (null (vla-get-fullname __d)) "MCPERRO:desenho novo sem caminho; salve antes"'
            '  (progn (vla-close __d %s) T)))'
            % (_doc(), guarda, ":vlax-true" if salvar else ":vlax-false"))


async def document_close(salvar: bool = False, forcar: bool = False) -> dict:
    """Fecha o documento ativo; recusa fechar o ultimo desenho sem forcar=True."""
    return await _aval(_fechar_lisp(salvar, forcar))


async def drawing_close(salvar: bool = True, forcar: bool = False) -> dict:
    """Alias de document_close com o default do mcp-pro (salva ao fechar)."""
    return await _aval(_fechar_lisp(salvar, forcar))


TOOLS = [
    viewport_list, viewport_create, viewport_delete, viewport_set_scale, viewport_lock,
    xref_attach, xref_manage, image_attach,
    drawing_export_dwg, document_close, drawing_close,
]

NOMES = {f.__name__: f.__name__ for f in TOOLS}
