# -*- coding: utf-8 -*-
"""Ferramentas das familias `plot/arquivo` e `camada/estilo`.

Mescla controlada do contrato do autocad-mcp-pro 1.6.0 (nomes publicos
`layer_*`, `layout_*`, `page_setup_*`, `plot_style_*`, `drawing_*`,
`linetype_*`, `textstyle_*`, `dimstyle_*`) implementada sobre o NOSSO backend.

Regras aprendidas na validacao ao vivo (AutoCAD 2025, ActiveX):
  * `PlotCentered` NAO existe no Layout  -> acesso sempre por
    `vlax-get-property`/`vlax-put-property` dentro de `vl-catch-all-apply`,
    senao a tool inteira morre com "no function definition";
  * `vla-copy` NAO existe para Layout     -> copia pelo comando `LAYOUT _C`;
  * `vla-item` em nome inexistente estoura "Key not found" -> procurar antes.

Nada aqui usa `SendCommand` de texto livre para decisao. Sem AutoCAD vivo
(backend headless) a funcao responde ok=false com o motivo, em vez de fingir
sucesso.
"""
from __future__ import annotations

import os
from pathlib import Path

from .backend_manager import MANAGER


# ------------------------------------------------------------------ helpers
def _doc() -> str:
    return "(vla-get-activedocument (vlax-get-acad-object))"


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _pares(v) -> dict:
    """Converte a lista de pares `(("chave" valor) ...)` em dict minusculo."""
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


def _sem_lisp(b) -> dict | None:
    """Backend headless nao tem VLA; devolve o erro em vez de estourar."""
    if not hasattr(b, "_aval"):
        return {
            "ok": False,
            "erro": "backend '%s' nao executa LISP/VLA; abra o AutoCAD para esta operacao"
                    % getattr(b, "name", "?"),
        }
    return None


async def _aval(code: str) -> dict:
    """Roda LISP e devolve dict {ok, payload|error}."""
    b = await _b()
    falha = _sem_lisp(b)
    if falha:
        return falha
    try:
        r = b._aval(code)
    except Exception as exc:  # noqa: BLE001 - erro do AutoCAD volta como texto
        return {"ok": False, "erro": str(exc)}
    return r.to_dict() if hasattr(r, "to_dict") else {"ok": True, "payload": r}


# LISP: procura um layout pelo nome e devolve nil (sem estourar) se nao existir.
def _procura_layout(nome: str, var: str = "__l") -> str:
    return ('(setq %s nil) (vlax-for __x (vla-get-layouts %s)'
            ' (if (= (strcase (vla-get-name __x)) (strcase "%s")) (setq %s __x)))'
            % (var, _doc(), _esc(nome), var))


def _procura_camada(nome: str, var: str = "__l") -> str:
    return ('(setq %s nil) (vlax-for __x (vla-get-layers %s)'
            ' (if (= (strcase (vla-get-name __x)) (strcase "%s")) (setq %s __x)))'
            % (var, _doc(), _esc(nome), var))


def _existe(var: str, rotulo: str) -> str:
    return '(if (null %s) "MCPERRO:%s nao existe")' % (var, rotulo)


# ------------------------------------------------------------------- camadas
def _op_camada(name: str, prop: str, valor: str) -> dict:
    """Monta a chamada que liga/desliga uma propriedade booleana da camada."""
    return {
        "lisp": '(progn %s %s (vla-put-%s __l %s) T)'
                % (_procura_camada(name), _existe("__l", "camada '%s'" % _esc(name)),
                   prop, valor)
    }


async def layer_hide(name: str) -> dict:
    """Desliga a camada (entidades ficam invisiveis, mas continuam no desenho)."""
    return await _aval(_op_camada(name, "layeron", ":vlax-false")["lisp"])


async def layer_show(name: str) -> dict:
    """Religa uma camada que estava desligada."""
    return await _aval(_op_camada(name, "layeron", ":vlax-true")["lisp"])


async def layer_freeze(name: str) -> dict:
    """Congela a camada (invisivel e nao selecionavel; mais rapido no regen)."""
    return await _aval(_op_camada(name, "freeze", ":vlax-true")["lisp"])


async def layer_thaw(name: str) -> dict:
    """Descongela a camada."""
    return await _aval(_op_camada(name, "freeze", ":vlax-false")["lisp"])


async def layer_lock(name: str) -> dict:
    """Trava a camada: entidades visiveis, mas nao selecionaveis."""
    return await _aval(_op_camada(name, "lock", ":vlax-true")["lisp"])


async def layer_unlock(name: str) -> dict:
    """Destrava a camada."""
    return await _aval(_op_camada(name, "lock", ":vlax-false")["lisp"])


async def layer_isolate(name: str) -> dict:
    """Isola: desliga TODAS as camadas menos `name` (o alvo fica ligado)."""
    return await _aval(
        "(progn (setq __d %s) (setq __alvo (strcase \"%s\"))"
        " (vlax-for __x (vla-get-layers __d)"
        "  (vla-put-layeron __x (if (= (strcase (vla-get-name __x)) __alvo)"
        " :vlax-true :vlax-false))) T)" % (_doc(), _esc(name))
    )


async def layer_delete(name: str) -> dict:
    """Apaga a camada. Precisa estar vazia; as camadas '0' e atual nao saem."""
    return await _aval(
        "(progn %s %s (vla-delete __l) T)"
        % (_procura_camada(name), _existe("__l", "camada '%s'" % _esc(name)))
    )


async def layer_modify(name: str, color: int | None = None,
                       linetype: str | None = None,
                       lineweight: int | None = None) -> dict:
    """Muda cor (1-255), tipo de linha e/ou espessura (1/100 mm) de uma camada."""
    b = await _b()
    fn = getattr(b, "layer_set_properties", None)
    if fn is None:
        return {"ok": False, "erro": "backend '%s' sem layer_set_properties"
                                     % getattr(b, "name", "?")}
    r = await fn(name, color=color, linetype=linetype, lineweight=lineweight)
    return r.to_dict() if hasattr(r, "to_dict") else {"ok": bool(r)}


# ------------------------------------------------------------------ layouts
async def layout_list() -> dict:
    """Lista as abas de layout (Model + paper space) na ordem em que aparecem."""
    return await _aval(
        '(progn (setq __d %s) (setq __out nil)'
        ' (vlax-for __x (vla-get-layouts __d) (setq __out (cons (vla-get-name __x) __out)))'
        ' (reverse __out))' % _doc()
    )


async def layout_create(name: str) -> dict:
    """Cria uma aba de layout (paper space) nova."""
    return await _aval(
        '(progn (vla-add (vla-get-layouts %s) "%s") T)' % (_doc(), _esc(name))
    )


async def layout_set_current(name: str) -> dict:
    """Ativa uma aba de layout (o que o CTAB faz)."""
    return await _aval('(progn (setvar "CTAB" "%s") T)' % _esc(name))


async def layout_rename(antigo: str, novo: str) -> dict:
    """Renomeia a aba. Os handles das entidades nao mudam."""
    return await _aval(
        '(progn %s %s (vla-put-name __l "%s") T)'
        % (_procura_layout(antigo), _existe("__l", "layout '%s'" % _esc(antigo)), _esc(novo))
    )


async def layout_delete(name: str) -> dict:
    """Apaga a aba de layout e tudo que estiver nela."""
    return await _aval(
        '(progn %s %s (vla-delete __l) T)'
        % (_procura_layout(name), _existe("__l", "layout '%s'" % _esc(name)))
    )


async def layout_copy(origem: str, novo: str) -> dict:
    """Copia a aba (page setup + geometria) e renomeia a copia.

    O Layout do ActiveX nao tem `Copy`: quem copia e' o comando LAYOUT _C,
    que herda page setup e geometria do paper space.
    """
    return await _aval(
        '(progn %s %s'
        ' (command "_.LAYOUT" "_C" "%s" "%s")'
        ' (setq __achou nil)'
        ' (vlax-for __x (vla-get-layouts %s)'
        '  (if (= (strcase (vla-get-name __x)) (strcase "%s")) (setq __achou T)))'
        ' (if __achou T "MCPERRO:copia nao criada (LAYOUT _C falhou)"))'
        % (_procura_layout(origem), _existe("__l", "layout '%s'" % _esc(origem)),
           _esc(origem), _esc(novo), _doc(), _esc(novo))
    )


# ------------------------------------------------------- page setup / plot
_ROTACAO = {
    "0": 0, "landscape": 0, "paisagem": 0, "horizontal": 0,
    "90": 1, "portrait": 1, "retrato": 1, "vertical": 1,
    "180": 2, "270": 3,
}

# Propriedades lidas/escritas por simbolo: as que nao existirem no objeto sao
# simplesmente puladas (PlotCentered e' o caso conhecido no AutoCAD 2025).
_PROPS_PAGE = ("Configname", "CanonicalMediaName", "PlotRotation",
               "StyleSheet", "PlotType", "StandardScale", "PaperUnits",
               "PlotCentered")


async def page_setup_list(layout: str = "Model") -> dict:
    """Le o page setup salvo na aba: device, papel, rotacao, CTB e centralizacao."""
    lisp = (
        '(progn %s %s (setq __o nil)'
        " (foreach __p '(%s)"
        "  (if (not (vl-catch-all-error-p"
        "        (setq __v (vl-catch-all-apply 'vlax-get-property (list __l __p)))))"
        "   (setq __o (cons (list (vl-princ-to-string __p) (vl-princ-to-string __v)) __o))))"
        ' (reverse __o))'
        % (_procura_layout(layout), _existe("__l", "layout '%s'" % _esc(layout)),
           " ".join(_PROPS_PAGE))
    )
    r = await _aval(lisp)
    if r.get("ok"):
        r["page_setup"] = _pares(r.get("payload"))
    return r


async def page_setup_apply(layout: str = "Model", device: str | None = None,
                           paper: str | None = None, orientation: str = "landscape",
                           plot_style: str | None = None,
                           centered: bool | None = None) -> dict:
    """Aplica o page setup de uma vez (equivalente ao PAGESETUP do AutoCAD).

    device: "DWG To PDF.pc3" (default do AutoCAD), "AutoCAD PDF (General
    Documentation).pc3" etc.
    paper: nome canonico do papel, ex. "ISO_A3_(420.00_x_297.00_MM)".
    orientation: landscape|portrait|90|180|270 (rotacao do papel).
    plot_style: nome ou caminho do .ctb/.stb (ex. "monochrome.ctb").
    centered: centraliza o plot; ignorado se o objeto Layout nao expuser a
    propriedade (AutoCAD 2025 nao expoe).
    """
    rot = _ROTACAO.get(str(orientation).lower())
    if rot is None:
        return {"ok": False, "erro": "orientation invalida: %r" % (orientation,)}

    pares = []
    if device:
        pares.append("(cons 'Configname \"%s\")" % _esc(device))
    if paper:
        pares.append("(cons 'CanonicalMediaName \"%s\")" % _esc(paper))
    pares.append("(cons 'PlotRotation %d)" % rot)
    if plot_style:
        pares.append("(cons 'StyleSheet \"%s\")" % _esc(plot_style))
    if centered is not None:
        pares.append("(cons 'PlotCentered %s)" % (":vlax-true" if centered else ":vlax-false"))

    lisp = (
        '(progn %s %s (setq __f nil)'
        ' (foreach __pv (list %s)'
        "  (if (vl-catch-all-error-p (vl-catch-all-apply 'vlax-put-property"
        '        (list __l (car __pv) (cdr __pv))))'
        '   (setq __f (cons (vl-princ-to-string (car __pv)) __f))))'
        ' (list (cons "falhas" (reverse __f)) (cons "ok" (if __f nil T))))'
        % (_procura_layout(layout), _existe("__l", "layout '%s'" % _esc(layout)),
           " ".join(pares))
    )
    r = await _aval(lisp)
    if r.get("ok"):
        r["page_setup"] = _pares(r.get("payload"))
        r["ok"] = not (r["page_setup"].get("falhas") or [])
    return r


def _dirs_plot_styles() -> list[Path]:
    raizes = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        raizes.append(Path(appdata) / "Autodesk")
    for base in (r"C:\Program Files\Autodesk", r"C:\Program Files (x86)\Autodesk"):
        if os.path.isdir(base):
            raizes.append(Path(base))
    achados = []
    for raiz in raizes:
        if not raiz.is_dir():
            continue
        try:
            for p in raiz.rglob("*"):
                if p.is_dir() and p.name.lower() == "plot styles":
                    achados.append(p)
        except OSError:
            continue
    return achados


async def plot_style_list() -> dict:
    """Lista os arquivos .ctb/.stb instalados (monochrome, acad, grayscale...)."""
    try:
        b = await _b()
        if hasattr(b, 'plot_style_list'):
            r = await b.plot_style_list()
            if r.ok:
                return {"ok": True, "payload": r.payload, "pastas": []}
    except Exception:
        pass
    nomes: set[str] = set()
    pastas = []
    for d in _dirs_plot_styles():
        pastas.append(str(d))
        for ext in ("*.ctb", "*.stb"):
            try:
                for f in d.glob(ext):
                    nomes.add(f.name)
            except OSError:
                continue
    return {"ok": True, "payload": sorted(nomes), "pastas": pastas}


async def batch_plot(layouts: list[str] | None = None, out_dir: str | None = None,
                     media: str | None = None, escala: float | None = None,
                     padrao: str = "{layout}.pdf") -> dict:
    """Plota varias abas em PDF de uma vez (o PUBLISH do AutoCAD, sem dialogo).

    layouts: nomes das abas; sem isso, todas as de paper space ("Model" fica fora).
    out_dir: pasta de saida (default: a do desenho atual).
    padrao: nome do arquivo; `{layout}` vira o nome da aba.
    """
    b = await _b()
    if not hasattr(b, "drawing_plot_pdf"):
        return {"ok": False, "erro": "backend '%s' nao plota PDF" % getattr(b, "name", "?")}

    if layouts is None:
        r = await layout_list()
        if not r.get("ok"):
            return r
        brutos = r.get("payload") or []
        layouts = [n for n in brutos if str(n).lower() != "model"]
    if not layouts:
        return {"ok": False, "erro": "nenhuma aba de paper space para plotar"}

    base = Path(out_dir) if out_dir else None
    if base is not None:
        base.mkdir(parents=True, exist_ok=True)

    resultados, falhas = [], 0
    for nome in layouts:
        troca = await layout_set_current(nome)
        if not troca.get("ok"):
            resultados.append({"layout": nome, "ok": False,
                               "erro": troca.get("error") or troca.get("erro")})
            falhas += 1
            continue
        arquivo = padrao.replace("{layout}", str(nome))
        destino = str((base / arquivo) if base else Path(arquivo).resolve())
        try:
            res = await b.drawing_plot_pdf(destino, media=media, escala=escala)
        except TypeError:
            # backend headless aceita so' o caminho: plota no padrao
            res = await b.drawing_plot_pdf(destino)
        d = res.to_dict() if hasattr(res, "to_dict") else {"ok": bool(res)}
        d["layout"] = nome
        d["arquivo"] = destino
        resultados.append(d)
        if not d.get("ok"):
            falhas += 1

    return {"ok": falhas == 0, "plotados": len(layouts) - falhas,
            "falhas": falhas, "resultados": resultados}


# ------------------------------------------------------------------ arquivo
async def drawing_save_as(path: str) -> dict:
    """Salva o desenho com outro nome/caminho (SAVEAS; a extensao decide DWG/DXF)."""
    b = await _b()
    r = await b.drawing_save(path=path)
    return r.to_dict() if hasattr(r, "to_dict") else {"ok": bool(r)}


async def drawing_purge() -> dict:
    """Purga do desenho tudo que nao esta em uso (camadas, blocos, tipos de linha)."""
    b = await _b()
    fn = getattr(b, "drawing_purge", None)
    if fn is None:
        return {"ok": False, "erro": "backend '%s' sem purge" % getattr(b, "name", "?")}
    r = await fn()
    return r.to_dict() if hasattr(r, "to_dict") else {"ok": bool(r)}


async def drawing_audit() -> dict:
    """Roda o AUDIT e conserta os problemas estruturais que ele conseguir."""
    return await _aval('(progn (command "_.AUDIT" "_Y") T)')


# ------------------------------------------------------------------ estilos
def _colecao(nome: str) -> str:
    return ('(progn (setq __d %s) (setq __out nil)'
            ' (vlax-for __x (vla-get-%s __d) (setq __out (cons (vla-get-name __x) __out)))'
            ' (reverse __out))' % (_doc(), nome))


async def linetype_list() -> dict:
    """Nomes de todos os tipos de linha carregados no desenho."""
    return await _aval(_colecao("linetypes"))


async def textstyle_list() -> dict:
    """Nomes de todos os estilos de texto (STYLE) do desenho."""
    return await _aval(_colecao("textstyles"))


async def dimstyle_list() -> dict:
    """Nomes de todos os estilos de cota (DIMSTYLE) do desenho."""
    return await _aval(_colecao("dimstyles"))


# ------------------------------------------------------------------ registro
TOOLS = [
    # camadas
    layer_hide, layer_show, layer_freeze, layer_thaw,
    layer_lock, layer_unlock, layer_isolate, layer_delete, layer_modify,
    # layouts
    layout_list, layout_create, layout_set_current,
    layout_rename, layout_delete, layout_copy,
    # page setup / plot
    page_setup_list, page_setup_apply, plot_style_list, batch_plot,
    # arquivo
    drawing_save_as, drawing_purge, drawing_audit,
    # estilos
    linetype_list, textstyle_list, dimstyle_list,
]

NOMES = {f.__name__: f.__name__ for f in TOOLS}
