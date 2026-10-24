# -*- coding: utf-8 -*-
"""Ferramentas do mcp-cad-server (lógica pura, sem MCP).

Cada função aqui é registrada como tool no server.py. Nomes compatíveis com o
contrato que o usuário já usa no CADCraft (inspect_drawing, query_entities,
command_line, script, new_drawing, open, save, cancel) + extras nossos
(desenho de planta, padrão de camadas e quantitativo).
"""
from __future__ import annotations

import ctypes
import os
import tempfile
from pathlib import Path

from .backend_manager import MANAGER
from .layers import ensure_standard_layers as _ensure_layers
from .quantitativo import analisar
from .bridge import Ponte, PonteIndisponivel as _PonteIndisponivel


def _r(res) -> dict:
    """Desembrulha CommandResult em dict simples para o agente."""
    return res.to_dict() if hasattr(res, "to_dict") else {"ok": bool(res), "payload": res}


def _pares(v) -> dict:
    """Converte a lista de pares que o LISP devolve (cons) em dict."""
    if isinstance(v, dict):
        return v
    saida = {}
    if isinstance(v, (list, tuple)):
        for item in v:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                saida[str(item[0]).lower()] = item[1]
    return saida


async def _b():
    return await MANAGER.get()


def _escape_lisp(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


# --------------------------------------------------------------------- status
async def cad_status() -> dict:
    """Qual motor está ativo (AutoCAD vivo ou headless) e o que ele suporta."""
    return await MANAGER.status()


# ------------------------------------------------------------------ leitura
async def inspect_drawing() -> dict:
    """Estado do desenho: variáveis, contagem de entidades e camadas."""
    b = await _b()
    info = await b.drawing_info()
    vars_ = await b.drawing_get_variables(None)
    cont = await b.entity_count()
    lays = await b.layer_list()
    return {"drawing": _r(info), "variables": _r(vars_),
            "entity_count": _r(cont), "layers": _r(lays)}


async def query_entities(layer: str | None = None, tipo: str | None = None) -> dict:
    """Lista entidades, com filtro opcional por camada e por tipo DXF (LINE, TEXT, ARC, LWPOLYLINE...).

    Cada item traz: handle, tipo, objeto (nome COM), camada. Use o handle no erase.
    """
    return _r(await (await _b()).entity_list(layer=layer, tipo=tipo))


async def erase(entity_id: str) -> dict:
    """Apaga UMA entidade pelo handle (ex.: o handle devolvido por query_entities)."""
    return _r(await (await _b()).entity_erase(entity_id))


async def entity_delete(entity_id: str) -> dict:
    """Apaga UMA entidade pelo handle (alias para entity_erase)."""
    return await erase(entity_id)


async def erase_filter(layer: str | None = None, tipo: str | None = None,
                       texto: str | None = None, confirmar: bool = False) -> dict:
    """Apaga em bloco por camada / tipo DXF / conteudo exato de texto.

    Sem `confirmar=True` apenas CONTA quantos seriam apagados (pre-visualizacao).
    Recusa rodar sem nenhum filtro, para nao apagar o desenho inteiro.
    """
    return _r(await (await _b()).entity_erase_filter(layer=layer, tipo=tipo,
                                                     texto=texto, confirmar=confirmar))


async def move_entity(entity_id: str, dx: float, dy: float) -> dict:
    """Move uma entidade pelo handle, em metros (vla-move, não trava o AutoCAD)."""
    return _r(await (await _b()).entity_move(entity_id, dx, dy))


async def copy_entity(entity_id: str, dx: float, dy: float) -> dict:
    """Copia UMA entidade e desloca a cópia (dx, dy). Devolve o handle da cópia."""
    return _r(await (await _b()).entity_copy(entity_id, dx, dy))


async def copy_filter(layer: str | None = None, tipo: str | None = None,
                      dx: float = 0.0, dy: float = 0.0) -> dict:
    """Copia EM BLOCO tudo que casa com camada/tipo e desloca a cópia.

    É o que faz "copiar o pavimento inteiro" ou "duplicar todas as janelas":
    devolve quantas entidades foram copiadas.
    """
    return _r(await (await _b()).entity_copy_filter(layer=layer, tipo=tipo, dx=dx, dy=dy))


async def mirror_filter(layer: str | None = None, tipo: str | None = None,
                         x1: float | None = None, y1: float | None = None,
                         x2: float | None = None, y2: float | None = None) -> dict:
    """Espelha EM BLOCO tudo que casa com camada/tipo, em relação ao eixo (x1,y1)-(x2,y2).

    Mantém os originais (cria a cópia espelhada). Devolve quantas entidades foram espelhadas.
    """
    return _r(await (await _b()).entity_mirror_filter(layer=layer, tipo=tipo,
                                                      x1=x1, y1=y1, x2=x2, y2=y2))


async def rotate_filter(layer: str | None = None, tipo: str | None = None,
                        x: float = 0.0, y: float = 0.0, angulo: float = 0.0) -> dict:
    """Gira EM BLOCO tudo que casa com camada/tipo em torno de (x, y). Ângulo em GRAUS."""
    return _r(await (await _b()).entity_rotate_filter(layer=layer, tipo=tipo,
                                                      x=x, y=y, angulo=angulo))


async def rotate_entity(entity_id: str, x: float, y: float, angulo: float) -> dict:
    """Gira uma entidade em torno de (x, y). Ângulo em GRAUS (anti-horário)."""
    return _r(await (await _b()).entity_rotate(entity_id, x, y, angulo))


async def mirror_entity(entity_id: str, x1: float, y1: float, x2: float, y2: float) -> dict:
    """Espelha uma entidade em relação ao eixo (x1,y1)-(x2,y2), MANTENDO o original.

    Devolve o handle da cópia espelhada.
    """
    return _r(await (await _b()).entity_mirror(entity_id, x1, y1, x2, y2))


async def offset_entity(entity_id: str, distance: float, side: int = 1) -> dict:
    """Cria uma paralela a uma LINE, a `distance`, para um dos lados.

    side=+1: esquerda do sentido do segmento; side=-1: direita.
    É assim que se desenha a outra face da parede a partir do eixo.
    """
    return _r(await (await _b()).entity_offset(entity_id, distance, side))


async def layer_list() -> dict:
    """Lista as camadas do desenho."""
    return _r(await (await _b()).layer_list())


async def block_list() -> dict:
    """Lista os blocos definidos no desenho."""
    return _r(await (await _b()).block_list())


# ------------------------------------------------------------- comandos CAD
async def command_line(text: str) -> dict:
    """Executa UM comando do AutoCAD (ex.: 'LINE 0,0 10,0 10,5 C').

    Vai pelo backend (COM ou accoreconsole), que ESPERA o comando acabar.
    Nao use a ponte .NET aqui: o `exec` dela e assincrono e nao devolve se o
    comando cortou alguma coisa - bom para pingar, ruim para decidir.

    Pontos com virgula viram coordenada; espaco separa argumentos.
    """
    b = await _b()
    return _r(await b.execute_lisp(f'(command "{_escape_lisp(text)}")'))


async def script(linhas: list[str]) -> dict:
    """Executa vários comandos em sequência."""
    resultados, falhas = [], 0
    for ln in linhas:
        r = await command_line(ln)
        resultados.append(r)
        if not r.get("ok"):
            falhas += 1
    return {"ok": falhas == 0, "executados": len(linhas), "falhas": falhas, "resultados": resultados}


async def cancel() -> dict:
    """Envia ESC ao AutoCAD (cancela comando em execução / limpa seleção)."""
    b = await _b()
    if b.name == "file_ipc":
        try:
            target = getattr(b, "_command_hwnd", None) or getattr(b, "_hwnd", None)
            VK_ESCAPE, WM_KEYDOWN, WM_KEYUP = 0x1B, 0x0100, 0x0101
            post = ctypes.windll.user32.PostMessageW
            post(target, WM_KEYDOWN, VK_ESCAPE, 0)
            post(target, WM_KEYUP, VK_ESCAPE, 0)
            return {"ok": True, "acao": "ESC enviado ao AutoCAD"}
        except Exception as exc:
            return {"ok": False, "erro": str(exc)}
    elif b.name == "autocad_com":
        try:
            from . import win32_bridge
            h = win32_bridge.find_autocad_window()
            if h:
                win32_bridge.enviar_esc(h, forcado=True)
                return {"ok": True, "acao": "ESC enviado ao AutoCAD via COM"}
        except Exception:
            pass
        return {"ok": False, "erro": "cancel via COM nao implementado"}
    return {"ok": False, "erro": "cancel so funciona com AutoCAD aberto (COM ou file_ipc)"}


# ------------------------------------------------------------- arquivo
async def new_drawing(name: str | None = None) -> dict:
    """Cria um desenho novo."""
    return _r(await (await _b()).drawing_create(name=name))


async def open(path: str) -> dict:
    """Abre um DXF/DWG existente."""
    return _r(await (await _b()).drawing_open(path))


async def save(path: str | None = None) -> dict:
    """Salva o desenho (SAVEAS se path for informado)."""
    return _r(await (await _b()).drawing_save(path=path))


async def export_dxf(path: str) -> dict:
    """Exporta o desenho atual para DXF."""
    return _r(await (await _b()).drawing_save_as_dxf(path))


async def plot_pdf(path: str, folha: str | None = None, escala: float | None = None) -> dict:
    """Plota o desenho em PDF.

    folha: "A4", "A3", "A2", "A1" ou "A0" (sem ela, A4/ajustar).
    escala: ex. 50 para 1:50 REAL. Sem escala o desenho é ajustado na folha
    (fit) e a escala do papel não é controlada. Com escala e sem folha, a folha
    é escolhida sozinha (A4…A0); se não couber, o tool devolve ok=false dizendo
    qual folha/escala usar.
    """
    b = await _b()
    try:
        return _r(await b.drawing_plot_pdf(path, media=folha, escala=escala))
    except TypeError:
        # Backends headless (ezdxf/file_ipc) expõem só `path`: folha/escala são
        # do motor COM. Em vez de estourar, plota no padrão e avisa.
        d = _r(await b.drawing_plot_pdf(path))
        d["aviso"] = "backend '%s' ignora folha/escala; plotado no padrao" % b.name
        return d


async def drawing_setup(unidades: int = 6, escala_cota: float = 0.1,
                        ltscale: float = 0.2) -> dict:
    """Ajusta unidades e escala de cota do desenho ATUAL (chame após new_drawing).

    unidades: 6 = metros (padrão). Sem isso o DXF sai com INSUNITS=mm (4).
    escala_cota: vira o DIMSCALE. O estilo tem DIMTXT=2,5, então o texto da cota
    mede 2,5 * escala_cota metros. Para planta em metros use 0,1 (texto 0,25).
    Define também TEXTSIZE 0,2, que é a altura padrão de texto novo.
    Com 0,1 a flecha (DIMASZ 1,0 x DIMSCALE) fica 0,10 m = 2 mm no papel a 1:50.
    ltscale: 0,2 deixa o DASHED com traço de 2 mm e vão de 1 mm no papel a 1:50
    (padrão do acad.lin: 0,5 / -0,25). 1,0 dá traço de 10 mm (grosseiro) e 0,05
    dá 0,5 mm (parece linha contínua). Se o LTYPE veio do acadiso.lin (padrão
    12,7 / -6,35), o mesmo 0,2 fica 25x maior — confira o padrão no DXF.
    Crava também DIMTXT 2,5, DIMGAP 0,5, DIMTIH/DIMTOH 0, DIMLUNIT 2 e DIMBLK "." —
    esses herdavam o seed do template e duas rodadas iguais saíam com extensões
    diferentes só por causa do texto da cota ("11" x "11,00").
    """
    return _r(await (await _b()).drawing_setup(unidades=unidades, escala_cota=escala_cota,
                                               ltscale=ltscale))


async def render_png(path: str | None = None) -> dict:
    """Gera PNG do desenho e grava EXATAMENTE em `path` (se informado).

    Devolve ok=false se a captura falhar ou se o PNG sair minusculo (janela do
    AutoCAD minimizada) — antes o tool dizia ok e ignorava `path`.
    """
    b = await _b()
    try:
        r = await b.get_screenshot()
    except AttributeError:
        return {"ok": False, "erro": "backend %s não gera imagem; use o modo autocad" % b.name}
    d = _r(r)
    if not d.get("ok"):
        return d
    p = d.get("payload") or {}
    origem = p.get("png") if isinstance(p, dict) else None
    if not origem or not os.path.exists(origem):
        return {"ok": False, "erro": "a captura não gerou arquivo PNG", "payload": p}
    destino = path or os.path.join(tempfile.gettempdir(), "cad_render.png")
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    if os.path.normcase(os.path.abspath(origem)) != os.path.normcase(os.path.abspath(destino)):
        # Copia por bytes: evita "arquivo em uso" quando o destino já existe.
        Path(destino).write_bytes(Path(origem).read_bytes())
    largura = p.get("largura")
    altura = p.get("altura")
    if not largura or not altura:
        try:
            from PIL import Image  # type: ignore
            with Image.open(destino) as im:
                largura, altura = im.size
        except Exception:
            largura = altura = None
    if largura and altura and (largura < 300 or altura < 200):
        return {"ok": False, "path": destino, "largura": largura, "altura": altura,
                "erro": ("PNG saiu %dx%d px: a janela do AutoCAD está minimizada ou "
                         "diminuta. Restaure/maximize a janela e chame de novo."
                         % (largura, altura))}
    return {"ok": True, "path": destino, "bytes": os.path.getsize(destino),
            "largura": largura, "altura": altura}


async def screenshot(path: str | None = None) -> dict:
    """Captura a janela do CAD (mesmo que render_png no modo headless)."""
    return await render_png(path)


# ------------------------------------------------------------- undo / view
async def undo() -> dict:
    """Desfaz a última operação."""
    return _r(await (await _b()).undo())


async def redo() -> dict:
    """Refaz a última operação desfeita."""
    return _r(await (await _b()).redo())


async def zoom_extents() -> dict:
    """Zoom para os limites do desenho."""
    return _r(await (await _b()).zoom_extents())


# ------------------------------------------------------------- desenho
async def draw_line(x1: float, y1: float, x2: float, y2: float, layer: str | None = None) -> dict:
    """Desenha uma linha."""
    return _r(await (await _b()).create_line(x1, y1, x2, y2, layer=layer))


async def draw_rectangle(x1: float, y1: float, x2: float, y2: float, layer: str | None = None) -> dict:
    """Desenha um retângulo (polyline fechada)."""
    return _r(await (await _b()).create_rectangle(x1, y1, x2, y2, layer=layer))


async def draw_polyline(points: list[list[float]], closed: bool = False, layer: str | None = None) -> dict:
    """Desenha uma polyline pelos pontos [[x,y], ...]."""
    return _r(await (await _b()).create_polyline(points, closed=closed, layer=layer))


async def draw_circle(cx: float, cy: float, radius: float, layer: str | None = None) -> dict:
    """Desenha um círculo."""
    return _r(await (await _b()).create_circle(cx, cy, radius, layer=layer))


async def draw_arc(cx: float, cy: float, radius: float, start_angle: float, end_angle: float, layer: str | None = None) -> dict:
    """Desenha um arco (abertura de porta, por exemplo)."""
    return _r(await (await _b()).create_arc(cx, cy, radius, start_angle, end_angle, layer=layer))


async def draw_text(x: float, y: float, text: str, height: float = 2.5, rotation: float = 0.0, layer: str | None = None) -> dict:
    """Escreve um texto simples."""
    return _r(await (await _b()).create_text(x, y, text, height=height, rotation=rotation, layer=layer))


async def draw_mtext(x: float, y: float, width: float, text: str, height: float = 2.5, layer: str | None = None) -> dict:
    """Escreve um texto multilinha."""
    return _r(await (await _b()).create_mtext(x, y, width, text, height=height, layer=layer))


async def draw_hatch(entity_id: str, pattern: str = "ANSI31") -> dict:
    """Hachura uma entidade fechada (recebe o handle dela)."""
    return _r(await (await _b()).create_hatch(entity_id, pattern=pattern))


async def entity_create_table(
    x: float, y: float,
    rows: list[list[str]],
    headers: list[str] | None = None,
    column_widths: list[float] | None = None,
    row_height: float = 2.5,
    text_height: float = 2.5,
    title: str | None = None,
    layer: str | None = None,
) -> dict:
    """Cria uma tabela com cabeçalhos e linhas.

    Argumentos:
        x, y: ponto de inserção (canto inferior esquerdo)
        rows: lista de linhas, cada linha é uma lista de células (strings)
        headers: lista opcional de cabeçalhos das colunas
        column_widths: larguras das colunas (opcional, default 10.0 cada)
        row_height: altura das linhas (default 2.5)
        text_height: altura do texto (default 2.5)
        title: título da tabela (opcional)
        layer: camada (opcional, default "0")
    """
    return _r(await (await _b()).create_table(
        x=x, y=y, rows=rows, headers=headers, column_widths=column_widths,
        row_height=row_height, text_height=text_height, title=title, layer=layer
    ))


async def dim_linear(x1: float, y1: float, x2: float, y2: float, dim_x: float, dim_y: float) -> dict:
    """Cota linear entre dois pontos, com a linha de cota em (dim_x, dim_y).

    Em cota HORIZONTAL (y1 == y2) só o Y do terceiro ponto posiciona a linha: o
    DIMLINEAR ignora o X — para deslocar o texto para a esquerda use uma cota
    vertical/alinhada ou mova o texto depois. Em cota VERTICAL (x1 == x2) é o X que
    posiciona. Não é bug da ferramenta: é como o DIMLINEAR escolhe a direção.
    """
    return _r(await (await _b()).create_dimension_linear(x1, y1, x2, y2, dim_x, dim_y))


async def dim_aligned(x1: float, y1: float, x2: float, y2: float, offset: float) -> dict:
    """Cota alinhada entre dois pontos, com afastamento."""
    return _r(await (await _b()).create_dimension_aligned(x1, y1, x2, y2, offset))


# ------------------------------------------------------------- camadas
async def linetype_load(nome: str, arquivo: str = "acad.lin") -> dict:
    """Carrega um tipo de linha (LTYPE) do .lin e confirma que entrou na tabela.

    Use antes de layer_create(..., linetype="DASHED"): sem o LTYPE carregado a
    camada não é criada. Nomes comuns: CONTINUOUS, DASHED, HIDDEN, CENTER, PHANTOM.
    """
    return _r(await (await _b()).layer_linetype_load(nome, arquivo=arquivo))


async def layer_create(name: str, color: int | str = 7, linetype: str = "CONTINUOUS") -> dict:
    """Cria uma camada.

    Se o `linetype` não existir no desenho o tool devolve ok=false dizendo para
    rodar linetype_load (antes ele devolvia payload 0 sem erro).
    """
    return _r(await (await _b()).layer_create(name, color=color, linetype=linetype))


async def layer_set_current(name: str) -> dict:
    """Define a camada corrente."""
    return _r(await (await _b()).layer_set_current(name))


async def ensure_standard_layers() -> dict:
    """Cria o conjunto padrão de camadas (PAREDES, PORTAS, JANELAS, COTAS, TEXTOS, HACHURA...)."""
    return await _ensure_layers(await _b())


# ------------------------------------------------------------- blocos
async def block_insert(name: str, x: float, y: float, scale: float = 1.0, rotation: float = 0.0) -> dict:
    """Insere um bloco."""
    return _r(await (await _b()).block_insert(name, x, y, scale=scale, rotation=rotation))


async def block_attributes(entity_id: str) -> dict:
    """Lê os atributos de um bloco inserido (largura de porta, tipo de janela...)."""
    return _r(await (await _b()).block_get_attributes(entity_id))


async def block_set_attribute(entity_id: str, tag: str, value: str) -> dict:
    """Altera um atributo de bloco."""
    return _r(await (await _b()).block_update_attribute(entity_id, tag, value))


# ------------------------------------------------------------- nossos extras
async def desenhar_ambiente(
    nome: str,
    x: float,
    y: float,
    largura: float,
    altura: float,
    com_hachura: bool = True,
    com_texto: bool = True,
    altura_texto: float = 0.18,
    padrao_hachura: str = "ANSI31",
) -> dict:
    """Desenha um ambiente como contorno fechado em PAREDES + hachura + texto com nome e área.

    Retorna handle, área e perímetro — a base do quantitativo e da EAP por ambiente.
    """
    b = await _b()
    area = round(largura * altura, 3)
    per = round(2 * (largura + altura), 3)
    cont = await b.create_rectangle(x, y, x + largura, y + altura, layer="PAREDES")
    if not cont.ok:
        return {"ok": False, "erro": cont.error or "falha ao desenhar contorno"}

    saida = {"ok": True, "ambiente": nome, "area": area, "perimetro": per,
             "contorno": cont.payload, "hachura": None, "texto": None}

    if com_hachura:
        _pl = cont.payload
        handle = _pl if isinstance(_pl, str) else ((_pl or {}).get("handle") if isinstance(_pl, dict) else None)
        if handle:
            h = await b.create_hatch(handle, pattern=padrao_hachura)
            saida["hachura"] = _r(h)

    if com_texto:
        rotulo = f"{nome}\\P{area:,.2f} m²".replace(",", "X").replace(".", ",").replace("X", ".")
        t = await b.create_text(x + largura / 2, y + altura / 2, rotulo,
                                height=altura_texto, layer="TEXTOS")
        saida["texto"] = _r(t)
    return saida


async def quantitativo(layer: str | None = None) -> dict:
    """Lê o desenho atual e devolve quantitativos por camada (comprimentos, áreas, blocos, textos, cotas).

    Funciona nos dois motores: o AutoCAD exporta um DXF temporário e a análise roda nele.
    Se o documento ativo estiver vazio (ex.: o COM caiu e o AutoCAD criou outro desenho),
    devolve ok=false dizendo qual documento foi lido — antes devolvia um quantitativo
    vazio com ok=true.
    """
    b = await _b()
    info = _pares(_r(await b.drawing_info()).get("payload"))
    tmp = os.path.join(tempfile.gettempdir(), "cad_mcp_quantitativo.dxf")
    exp = await b.drawing_save_as_dxf(tmp)
    if not exp.ok:
        return {"ok": False, "erro": exp.error or "não foi possível exportar DXF para análise"}
    dados = analisar(tmp)
    lidas = int(dados.get("total_entidades") or 0)
    no_cad = info.get("entidades")
    dados["documento"] = info.get("nome")
    dados["caminho"] = info.get("caminho")
    dados["entidades_no_autocad"] = no_cad
    if lidas == 0:
        caminho = info.get("caminho")
        salvo = bool(caminho) and os.path.exists(str(caminho))
        if isinstance(no_cad, int) and no_cad > 0:
            dica = ("" if salvo else
                    " O desenho nunca foi salvo em disco (caminho '%s' não existe) — "
                    "rode drawing_save antes de medir." % (caminho or ""))
            return {
                "ok": False,
                "erro": ("o AutoCAD diz que '%s' tem %d entidades, mas o DXF exportado saiu "
                         "VAZIO — a exportação falhou ou exportou outro documento.%s"
                         % (info.get("nome"), no_cad, dica)),
                "documento": info.get("nome"), "caminho": caminho,
                "entidades_no_autocad": no_cad, "backend": b.name,
            }
        return {
            "ok": False,
            "erro": ("o desenho ativo '%s' está VAZIO (0 entidades, %s camadas). "
                     "O DWG que você desenhou não é o documento ativo: confira com "
                     "inspect_drawing, abra o DWG certo (open) e rode de novo."
                     % (info.get("nome") or "?", info.get("camadas"))),
            "documento": info.get("nome"), "caminho": caminho,
            "entidades_no_autocad": no_cad, "backend": b.name,
        }
    dados["ok"] = True
    dados["backend"] = b.name
    if isinstance(exp.payload, dict) and exp.payload.get("aviso"):
        dados["aviso"] = exp.payload["aviso"]
    if layer:
        for chave in ("entidades_por_camada", "comprimento_por_camada", "area_fechada_por_camada"):
            dados[chave] = {k: v for k, v in dados[chave].items() if k == layer}
    return dados


async def arch_wall(walls: list[list[list[float]]], poche: bool = False) -> dict:
    """Desenha paredes de uma planta baixa.

    Argumentos:
        walls: lista de paredes, cada parede é uma lista de pontos [[x1, y1], [x2, y2], ...]
               que definem a polilinha da parede
        poche: se True, preenche com material poché (hachura)

    Retorna lista de handles das paredes criadas.
    """
    b = await _b()
    handles = []
    
    for wall_points in walls:
        if len(wall_points) < 2:
            continue
        result = await b.create_polyline(wall_points, closed=False, layer="PAREDES")
        if result.ok:
            handle = result.payload if isinstance(result.payload, str) else (
                result.payload.get("handle") if isinstance(result.payload, dict) else None
            )
            if handle:
                handles.append(handle)
                if poche:
                    await b.create_hatch(handle, pattern="ANSI31")
    
    return {"ok": True, "payload": {"handles": handles, "count": len(handles)}}


async def arch_opening(wall: str, offset: float, width: float,
                      kind: str = "door", swing: str = "left",
                      hand: str = "start", sill: float = 0.0,
                      height: float = 2.10, tag: str | None = None,
                      opening_id: str | None = None, lang: str = "pt",
                      poche: bool = False) -> dict:
    """Host a door or a window in a drawn wall by distance along it; the wall is cut.
    
    Implementacao baseada no modulo arch.py. A parede deve ja' existir no desenho.
    
    Argumentos:
        wall: handle da parede (polyline na camada PAREDES)
        offset: distancia do inicio da parede ate o inicio da abertura
        width: largura da abertura
        kind: tipo - "door", "window" ou "void"
        swing: direcao de abertura - "left" (esquerda) ou "right" (direita)
        hand: lado da dobradica - "start" (inicio) ou "end" (fim)
        sill: peitoril (altura do piso ate o inicio da janela)
        height: altura total da abertura
        tag: etiqueta opcional
        opening_id: ID unico da abertura
        lang: idioma para etiquetas
        poche: preencher com material poché
    
    Retorna dict com handles das entidades criadas.
    """
    from .arch import Parede, Abertura, primitivas, validar, trechos
    from .com_backend import _q  # para escapar strings no LISP
    
    b = await _b()
    
    # Obter os vertices da polyline usando LISP direto
    # Chamar _eval_lines para obter o texto bruto
    lisp_code = '(entget (handent "%s"))' % _q(wall)
    ok, linhas, erro = b._eval_lines(lisp_code)
    if not ok:
        return {"ok": False, "erro": "nao conseguiu ler vertices da parede: %s" % erro}
    
    if not linhas:
        return {"ok": False, "erro": "entget nao retornou dados"}
    
    # Parsear manualmente a lista DXF para extrair vertices (códigos 10 e 20)
    # A string está no formato: ((-1 . <Entity...) (0 . "LWPOLYLINE") (10 x y) (10 x2 y2) ...)
    # Precisamos extrair todos os pares (10 x y) ou (10 x 20 y)
    import re
    text = linhas[0]
    
    # Extrair todos os padrões: (10 número número) ou (10 número) (20 número)
    # O formato pode ser: (10 x y) ou (10 x) (20 y)
    vertices = []
    
    # Encontrar todos os (10 x y) onde x e y são números
    pattern1 = r'\(10\s+([\d.-]+)\s+([\d.-]+)\)'
    for m in re.finditer(pattern1, text):
        vertices.append((float(m.group(1)), float(m.group(2))))
    
    # Se não encontrou, tentar padrão (10 x) (20 y)
    if not vertices:
        coords_10 = re.findall(r'\(10\s+([\d.-]+)\)', text)
        coords_20 = re.findall(r'\(20\s+([\d.-]+)\)', text)
        vertices = list(zip(map(float, coords_10), map(float, coords_20)))
    
    if not vertices:
        return {"ok": False, "erro": "parede sem vertices na entidade"}
    
    eixo = tuple(vertices)
    
    # Criar objetos Parede e Abertura
    p = Parede(id="temp_wall", eixo=eixo, espessura=0.15, altura=2.70)
    
    # Mapear parâmetros
    tipo_map = {"door": "porta", "window": "janela", "void": "vao"}
    gira_map = {"left": "esquerda", "right": "direita"}
    dob_map = {"start": "inicio", "end": "fim"}
    
    ab = Abertura(
        id=opening_id or "A1",
        parede="temp_wall",
        tipo=tipo_map.get(kind, "porta"),
        offset=offset,
        largura=width,
        altura=height,
        peitoril=sill,
        dobradica=dob_map.get(hand, "inicio"),
        gira=gira_map.get(swing, "esquerda")
    )
    
    # Validar
    try:
        validar([p], [ab])
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    
    # Obter primitivas para desenhar
    prim = primitivas(p, ab)
    
    # Desenhar de acordo com o tipo
    handles = []
    layer = "PAREDES"
    
    if ab.tipo == "porta" and "arco" in prim:
        # Desenhar arco da porta
        cx, cy, r, a1, a2 = prim["arco"]
        result = await b.create_arc(cx, cy, r, a1, a2, layer=layer)
        if result.ok:
            handles.append(result.payload)
    elif ab.tipo == "janela" and "linhas" in prim:
        # Desenhar linhas da janela
        for (x1, y1), (x2, y2) in prim["linhas"]:
            result = await b.create_line(x1, y1, x2, y2, layer=layer)
            if result.ok:
                handles.append(result.payload)
    
    # Cortar o trecho da parede onde fica a abertura
    if ab.tipo in ("porta", "janela", "vao"):
        # Obter os trechos da parede sem a abertura
        trechos_parede = trechos(p, [ab])
        
        # Apagar a parede original
        await b.entity_erase(wall)
        
        # Redesenhar a parede com os trechos como polylines
        # Converter trechos para polylines (cada trecho é uma polyline de 2 pontos)
        for (x1, y1), (x2, y2) in trechos_parede:
            result = await b.create_polyline([[x1, y1], [x2, y2]], closed=False, layer="PAREDES")
            if result.ok:
                handles.append(result.payload)
    
    return {"ok": True, "payload": {"handles": handles, "opening_id": ab.id}}


async def arch_stair(x: float = 0.0, y: float = 0.0, largura: float = 1.10,
                     degraus: int = 11, piso: float = 0.28,
                     altura_total: float | None = 1.80, angulo: float = 0.0,
                     seta: bool = True, rotulo: str | None = "SUBA",
                     camada: str = "ESCADAS", lang: str = "pt") -> dict:
    """Draw a straight-run staircase in plan; reports its Blondel step rule.

    Implementacao baseada no modulo arch.py (`escada_reta`). Desenha um tramo
    reto: duas talaias, (degraus-1) pisadas, uma seta de subida e um rotulo.
    A escada NAO precisa de nada ja' desenhado -- e geometria nova no modelo.

    Argumentos:
        x, y          -- canto de partida da escada (metros, no modelspace)
        largura       -- largura do tramo (> 0)
        degraus       -- numero de risos (inteiro >= 1)
        piso          -- profundidade (corrida) de cada degrau (> 0)
        altura_total  -- subida total; com ela, calcula o riso e a regra de Blondel
        angulo        -- direcao de subida em graus (0 = +X, 90 = +Y)
        seta          -- desenha a seta de subida (default True)
        rotulo        -- texto ao lado (default "SUBA"; None desliga)
        camada        -- camada das entidades (default "ESCADAS")
        lang          -- "pt" (SUBA) ou "en" (UP) para o rotulo-padrao

    Retorna dict com os handles das entidades criadas e o resumo da escada
    (comprimento, riser, corrida e a regra de Blondel).
    """
    from .arch import escada_reta

    if rotulo is None:
        label = None
    elif isinstance(rotulo, str) and rotulo not in ("", "SUBA", "UP"):
        label = rotulo                        # texto proprio, respeitado em qualquer lang
    else:
        label = "UP" if lang == "en" else "SUBA"

    try:
        geo = escada_reta(x=x, y=y, largura=largura, degraus=degraus, piso=piso,
                          altura_total=altura_total, angulo=angulo, seta=seta,
                          rotulo=label, camada=camada)
    except ValueError as e:
        return {"ok": False, "erro": str(e)}

    b = await _b()
    handles = []

    # talaias + pisadas: linhas retas
    for (a, c) in geo["linhas"]:
        r = await b.create_line(a[0], a[1], c[0], c[1], layer=camada)
        if r.ok:
            handles.append(r.payload)

    # seta de subida: tronco (linha) + ponta (polilinea de 3 pontos)
    if seta and geo.get("seta"):
        s = geo["seta"]
        t = s["tronco"]
        r = await b.create_line(t[0], t[1], t[2], t[3], layer=camada)
        if r.ok:
            handles.append(r.payload)
        r = await b.create_polyline([[pt[0], pt[1]] for pt in s["ponta"]],
                                    closed=False, layer=camada)
        if r.ok:
            handles.append(r.payload)

    # rotulo de subida
    if geo.get("rotulo"):
        lz = geo["rotulo"]
        r = await b.create_text(lz["x"], lz["y"], lz["texto"],
                                height=lz["altura"], rotation=lz["rotacao"], layer=camada)
        if r.ok:
            handles.append(r.payload)

    geo["handles"] = handles
    geo["count"] = len(handles)
    return {"ok": True, "payload": geo}


# --- novas ops por geometria (ponte .NET ou COM) -----------------------------
async def _pontes_trim(alvo: str, corte: str, keep: list[float]) -> dict:
    """Encurta a reta `alvo` ate' a `corte`, mantendo o lado de `keep`."""
    try:
        b = await _b()
        if hasattr(b, 'entity_trim'):
            r = await b.entity_trim(alvo=alvo, corte=corte, keep=keep)
            return r.to_dict() if hasattr(r, 'to_dict') else {"ok": bool(r), "payload": r}
    except Exception:
        pass
    try:
        return Ponte().trim(alvo=alvo, corte=corte, keep=keep)
    except _PonteIndisponivel:
        return {"ok": False, "erro": "ponte .NET nao carregada (reinicie o AutoCAD)"}


async def _pontes_extend(alvo: str, limite: str, ponto: list[float] | None = None) -> dict:
    """Estende a reta `alvo` ate' a `limite` (extremo auto se `ponto` for None)."""
    try:
        b = await _b()
        if hasattr(b, 'entity_extend'):
            r = await b.entity_extend(alvo=alvo, limite=limite, ponto=ponto)
            return r.to_dict() if hasattr(r, 'to_dict') else {"ok": bool(r), "payload": r}
    except Exception:
        pass
    try:
        return Ponte().extend(alvo=alvo, limite=limite, ponto=ponto)
    except _PonteIndisponivel:
        return {"ok": False, "erro": "ponte .NET nao carregada (reinicie o AutoCAD)"}


async def _pontes_fillet(h1: str, h2: str, raio: float, trim: bool = True,
                       p1: list[float] | None = None, p2: list[float] | None = None) -> dict:
    """Arredonda o canto entre duas retas com arco tangente de `raio`."""
    try:
        b = await _b()
        if hasattr(b, 'entity_fillet'):
            r = await b.entity_fillet(h1=h1, h2=h2, raio=raio, trim=trim, p1=p1, p2=p2)
            return r.to_dict() if hasattr(r, 'to_dict') else {"ok": bool(r), "payload": r}
    except Exception:
        pass
    try:
        return Ponte().fillet(h1=h1, h2=h2, raio=raio, trim=trim, p1=p1, p2=p2)
    except _PonteIndisponivel:
        return {"ok": False, "erro": "ponte .NET nao carregada (reinicie o AutoCAD)"}


async def trim_entity(alvo: str, corte: str, keep: list[float]) -> dict:
    """Corta a reta `alvo` na interseccao com `corte`, mantendo o lado de `keep`.

    Geometria nativa via ponte .NET (sem SendCommand). Devolve {ok, handle, ...}.
    """
    return await _pontes_trim(alvo=alvo, corte=corte, keep=keep)


async def extend_entity(alvo: str, limite: str, ponto: list[float] | None = None) -> dict:
    """Estende a reta `alvo` ate' encontrar a reta `limite`."""
    return await _pontes_extend(alvo=alvo, limite=limite, ponto=ponto)


async def fillet_entity(h1: str, h2: str, raio: float, trim: bool = True,
                        p1: list[float] | None = None, p2: list[float] | None = None) -> dict:
    """Arredonda o canto entre duas retas com arco tangente de `raio`."""
    return await _pontes_fillet(h1=h1, h2=h2, raio=raio, trim=trim, p1=p1, p2=p2)


TOOLS = [
    cad_status,
    inspect_drawing, query_entities, erase, entity_delete, erase_filter, move_entity,
    copy_entity, copy_filter, mirror_filter, rotate_filter,
    rotate_entity, mirror_entity, offset_entity,
    layer_list, linetype_load, block_list, quantitativo,
    command_line, script, cancel,
    new_drawing, open, save, export_dxf, plot_pdf, drawing_setup, render_png, screenshot,
    undo, redo, zoom_extents,
    draw_line, draw_rectangle, draw_polyline, draw_circle, draw_arc,
    draw_text, draw_mtext, draw_hatch, entity_create_table, dim_linear, dim_aligned,
    layer_create, layer_set_current, ensure_standard_layers,
    block_insert, block_attributes, block_set_attribute,
    desenhar_ambiente, arch_wall,
    trim_entity, extend_entity, fillet_entity,
    arch_opening,
    arch_stair,
]

# --------------------------------------------------------------- vocabulario
# Nome PUBLICO da ferramenta: padrao `verbo_objeto` do autocad-mcp-pro 1.6.0
# (entity_*, drawing_*, view_*, dimension_*, layer_*, block_*, system_*, arch_*).
# Adotado para que um prompt escrito para aquele servidor funcione aqui sem
# traducao. A funcao Python mantem o nome antigo: nada de codigo quebra.
# Sem equivalente do outro lado, o nome fica como esta (quantitativo, script).
NOMES = {
    "cad_status": "system_status",
    "inspect_drawing": "drawing_info",
    "query_entities": "entity_list",
    "erase": "entity_erase",
    "erase_filter": "entity_erase_filter",
    "move_entity": "entity_move",
    "copy_entity": "entity_copy",
    "copy_filter": "entity_copy_filter",
    "mirror_filter": "entity_mirror_filter",
    "rotate_filter": "entity_rotate_filter",
    "rotate_entity": "entity_rotate",
    "mirror_entity": "entity_mirror",
    "offset_entity": "entity_offset",
    "layer_list": "layer_list",
    "linetype_load": "layer_linetype_load",
    "block_list": "block_list",
    "quantitativo": "quantitativo",
    "command_line": "system_run_command",
    "script": "script",
    "cancel": "cancel",
    "new_drawing": "drawing_new",
    "open": "drawing_open",
    "save": "drawing_save",
    "export_dxf": "drawing_export_dxf",
    "plot_pdf": "drawing_export_pdf",
    "render_png": "view_render_png",
    "screenshot": "view_screenshot",
    "undo": "drawing_undo",
    "redo": "drawing_redo",
    "zoom_extents": "view_zoom_extents",
    "draw_line": "entity_create_line",
    "draw_rectangle": "entity_create_rectangle",
    "draw_polyline": "entity_create_polyline",
    "draw_circle": "entity_create_circle",
    "draw_arc": "entity_create_arc",
    "draw_text": "entity_create_text",
    "draw_mtext": "entity_create_mtext",
    "draw_hatch": "entity_create_hatch",
    "dim_linear": "dimension_linear",
    "dim_aligned": "dimension_aligned",
    "layer_create": "layer_create",
    "layer_set_current": "layer_set_current",
    "ensure_standard_layers": "drawing_apply_iso_layers",
    "block_insert": "block_insert",
    "block_attributes": "block_get_attributes",
    "block_set_attribute": "block_set_attributes",
    "desenhar_ambiente": "arch_room",
    "trim_entity": "entity_trim",
    "extend_entity": "entity_extend",
    "fillet_entity": "entity_fillet",
    "entity_delete": "entity_delete",
    "arch_wall": "arch_wall",
    "arch_opening": "arch_opening",
    "arch_stair": "arch_stair",
}


def nome_publico(fn) -> str:
    """Nome exposto no MCP. Cai para o nome da funcao se nao mapeado."""
    return NOMES.get(getattr(fn, "__name__", str(fn)), getattr(fn, "__name__", str(fn)))


# --- familias plot/arquivo + camada/estilo (mescla do autocad-mcp-pro) ---
from . import tools_ext as _ext  # noqa: E402

TOOLS.extend(_ext.TOOLS)
NOMES.update(_ext.NOMES)
# expoe as funcoes novas como atributos do modulo (tools.layer_hide, ...)
globals().update({_f.__name__: _f for _f in _ext.TOOLS})

from . import tools_plot as _plot  # noqa: E402

TOOLS.extend(_plot.TOOLS)
NOMES.update(_plot.NOMES)
globals().update({_f.__name__: _f for _f in _plot.TOOLS})

from . import tools_geo as _geo  # noqa: E402

TOOLS.extend(_geo.TOOLS)
NOMES.update(_geo.NOMES)
globals().update({_f.__name__: _f for _f in _geo.TOOLS})


_publicos = [nome_publico(t) for t in TOOLS]
if len(set(_publicos)) != len(_publicos):
    from collections import Counter
    _dup = [n for n, c in Counter(_publicos).items() if c > 1]
    raise RuntimeError("nome publico duplicado em tools.NOMES: %s" % _dup)
