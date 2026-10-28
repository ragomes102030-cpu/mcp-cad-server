"""Gerador de estudos preliminares residenciais em duas faixas, com medidas em metros.

Não substitui projeto arquitetônico, verificação urbanística ou de acessibilidade.
Em vez de forçar dimensões inviáveis, informa um erro e solicita revisão.
"""
from __future__ import annotations

import math
import unicodedata

PAREDE = 0.15
CORREDOR_EIXOS = 1.20
PORTA = 0.90
MARGEM = 0.30
JANELA_MAX = 1.20
TEMPLATE = "programa_sob_medida"
FRONTAL = ("sala", "estar", "jantar", "cozinha", "servico", "garagem", "varanda", "lavabo")
MIN_DIM = {
    "quarto": 2.50, "suite": 2.50, "sala": 2.50, "estar": 2.50,
    "cozinha": 1.80, "banheiro": 1.40, "lavabo": 1.10,
    "servico": 1.20, "garagem": 2.50,
}


class ErroPrograma(ValueError):
    """Programa incoerente ou incompatível com este arranjo inicial."""


def _numero(valor, campo, minimo=None, maximo=None):
    try:
        numero = float(valor)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ErroPrograma(f"{campo}: informe um número em metros ou metros quadrados") from exc
    if not math.isfinite(numero):
        raise ErroPrograma(f"{campo}: valor precisa ser finito")
    if minimo is not None and numero < minimo:
        raise ErroPrograma(f"{campo}: valor mínimo {minimo}")
    if maximo is not None and numero > maximo:
        raise ErroPrograma(f"{campo}: valor máximo {maximo}")
    return numero


def _opcional(programa, campo):
    if programa.get(campo) is None:
        return None
    return _numero(programa[campo], campo, 0)


def _chave(nome):
    return unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().casefold()


def _minimo(nome):
    chave = _chave(nome)
    return next((valor for termo, valor in MIN_DIM.items() if termo in chave), 1.20)


def normalizar_programa(programa):
    if not isinstance(programa, dict):
        raise ErroPrograma("o programa deve ser um objeto JSON")
    itens = programa.get("ambientes")
    if not isinstance(itens, list) or not 2 <= len(itens) <= 16:
        raise ErroPrograma("informe de 2 a 16 ambientes com nome e area")
    ambientes, vistos = [], set()
    for indice, item in enumerate(itens, 1):
        if not isinstance(item, dict):
            raise ErroPrograma(f"ambiente {indice}: informe nome e area")
        nome = item.get("nome")
        if not isinstance(nome, str) or not nome.strip() or len(nome) > 70:
            raise ErroPrograma(f"ambiente {indice}: nome inválido")
        nome = nome.strip()
        chave = _chave(nome)
        if chave in vistos or chave == "circulacao":
            raise ErroPrograma(f"nome de ambiente duplicado ou reservado: {nome}")
        vistos.add(chave)
        area = _numero(item.get("area"), f"{nome}.area", 1, 200)
        setor = item.get("setor")
        if setor is None:
            setor = "frontal" if any(k in chave for k in FRONTAL) else "fundo"
        if setor not in ("frontal", "fundo"):
            raise ErroPrograma(f"{nome}: setor deve ser frontal ou fundo")
        ambientes.append({"nome": nome, "area": area, "setor": setor})
    return ambientes


def _dividir(ambientes, largura):
    """Devolve profundidade e limites, preservando a área LIVRE pedida.

    Cada ambiente tem (largura da célula - parede) * (profundidade - parede)
    igual à área informada, sob a premissa de paredes de 15 cm centradas nos eixos.
    """
    largura_util = largura - len(ambientes) * PAREDE
    if largura_util <= 0:
        raise ErroPrograma("largura insuficiente para paredes e ambientes")
    profundidade_util = sum(a["area"] for a in ambientes) / largura_util
    profundidade = profundidade_util + PAREDE
    x, celulas = 0.0, []
    for ambiente in ambientes:
        largura_celula = ambiente["area"] / profundidade_util + PAREDE
        celulas.append((ambiente, x, x + largura_celula))
        x += largura_celula
    for ambiente, x1, x2 in celulas:
        util_x, util_y = x2 - x1 - PAREDE, profundidade - PAREDE
        minimo = _minimo(ambiente["nome"])
        if min(util_x, util_y) + 1e-8 < minimo:
            raise ErroPrograma(
                f"{ambiente['nome']}: dimensões internas {util_x:.2f} x {util_y:.2f} m; "
                f"este arranjo em duas faixas exige no mínimo {minimo:.2f} m em cada direção. "
                "Revise áreas/largura ou use um layout com mais faixas."
            )
        if x2 - x1 < PORTA + 2 * MARGEM:
            raise ErroPrograma(f"{ambiente['nome']}: largura insuficiente para porta")
    return profundidade, celulas


def _cortar(a, b, coord, vaos, horizontal):
    vaos = sorted(vaos)
    cursor, segmentos = a, []
    for inicio, largura in vaos:
        fim = inicio + largura
        if inicio < a + 1e-8 or fim > b - 1e-8:
            raise ErroPrograma("abertura fora do segmento de parede")
        if inicio < cursor - 1e-8:
            raise ErroPrograma("portas ou janelas sobrepostas")
        if inicio - cursor > 1e-7:
            segmentos.append([cursor, coord, inicio, coord] if horizontal
                             else [coord, cursor, coord, inicio])
        cursor = fim
    if b - cursor > 1e-7:
        segmentos.append([cursor, coord, b, coord] if horizontal
                         else [coord, cursor, coord, b])
    return segmentos


def gerar_modelo(programa):
    """Gera geometria preliminar determinística ou rejeita arranjo inviável."""
    if not isinstance(programa, dict):
        raise ErroPrograma("o programa deve ser um objeto JSON")
    largura = _numero(programa.get("largura", programa.get("largura_externa")), "largura", 4, 40)
    pe_direito = _numero(programa.get("pe_direito", 2.80), "pe_direito", 2.40, 4)
    if "espessura_parede" in programa:
        t = _numero(programa["espessura_parede"], "espessura_parede", 0.01, 1)
        if abs(t - PAREDE) > 1e-8:
            raise ErroPrograma("esta versão suporta paredes de 0,15 m")
    ambientes_pedidos = normalizar_programa(programa)
    frente = [a for a in ambientes_pedidos if a["setor"] == "frontal"]
    fundo = [a for a in ambientes_pedidos if a["setor"] == "fundo"]
    if not frente or not fundo:
        raise ErroPrograma("o arranjo de duas faixas exige ambientes frontais e de fundo")
    sala = next((a for a in frente if any(s in _chave(a["nome"]) for s in ("sala", "estar"))), None)
    if sala is None:
        raise ErroPrograma("inclua uma sala/estar frontal para a entrada externa")
    prof_frente, celulas_frente = _dividir(frente, largura)
    prof_fundo, celulas_fundo = _dividir(fundo, largura)
    y_corredor = prof_frente
    y_fundo = prof_frente + CORREDOR_EIXOS
    profundidade = y_fundo + prof_fundo
    if profundidade > 60:
        raise ErroPrograma("profundidade excessiva; revise o programa")

    terreno_largura = _opcional(programa, "terreno_largura")
    terreno_profundidade = _opcional(programa, "terreno_profundidade")
    recuo_lateral = _opcional(programa, "recuo_lateral")
    recuo_frente = _opcional(programa, "recuo_frente")
    recuo_fundo = _opcional(programa, "recuo_fundo")
    if terreno_largura is not None and terreno_largura + 1e-8 < largura + 2 * (recuo_lateral or 0):
        raise ErroPrograma("edificação excede a largura disponível do terreno/recuos")
    if terreno_profundidade is not None and terreno_profundidade + 1e-8 < profundidade + (recuo_frente or 0) + (recuo_fundo or 0):
        raise ErroPrograma("edificação excede a profundidade disponível do terreno/recuos")

    vaos, paredes_brutas, portas, janelas, ambientes = {}, [], [], [], []
    avisos = ["Estudo preliminar: sem verificação de normas locais, iluminação, ventilação ou acessibilidade."]
    def abrir(tipo, coordenada, inicio, tamanho):
        vaos.setdefault((tipo, coordenada), []).append((inicio, tamanho))

    paredes_brutas.extend([
        ("h", 0.0, 0.0, largura), ("h", y_corredor, 0.0, largura),
        ("h", y_fundo, 0.0, largura), ("h", profundidade, 0.0, largura),
        ("v", 0.0, 0.0, profundidade), ("v", largura, 0.0, profundidade),
    ])
    for celulas, y0, y1 in ((celulas_frente, 0.0, y_corredor),
                            (celulas_fundo, y_fundo, profundidade)):
        for _, _, limite in celulas[:-1]:
            paredes_brutas.append(("v", limite, y0, y1))

    for celulas, parede_interna, parede_externa, frontal, origem, fim in (
        (celulas_frente, y_corredor, 0.0, True, 0.0, y_corredor),
        (celulas_fundo, y_fundo, profundidade, False, y_fundo, profundidade),
    ):
        for room, x1, x2 in celulas:
            meio = (x1 + x2) / 2
            porta_x = meio - PORTA / 2
            abrir("h", parede_interna, porta_x, PORTA)
            portas.append((porta_x, parede_interna, 90 if frontal else 270, PORTA))
            largura_celula = x2 - x1
            eh_entrada = frontal and room["nome"] == sala["nome"]
            if eh_entrada:
                entrada_x = x1 + MARGEM
                abrir("h", parede_externa, entrada_x, PORTA)
                portas.append((entrada_x, parede_externa, 90, PORTA))
            largura_janela = min(JANELA_MAX, largura_celula - 2 * MARGEM)
            if largura_janela >= 0.60:
                janela_x = x2 - MARGEM - largura_janela if eh_entrada else meio - largura_janela / 2
                if not eh_entrada or janela_x >= entrada_x + PORTA + 0.20:
                    abrir("h", parede_externa, janela_x, largura_janela)
                    janelas.append((janela_x, parede_externa, janela_x + largura_janela, parede_externa))
                else:
                    avisos.append(f"{room['nome']}: sem janela na fachada frontal neste arranjo")
            livre_x = largura_celula - PAREDE
            h = min(0.22, 0.70 * livre_x / max(1.0, 0.90 * len(room["nome"])))
            ambientes.append({
                "nome": room["nome"], "x1": x1 + PAREDE / 2,
                "x2": x2 - PAREDE / 2,
                "y1": origem + PAREDE / 2, "y2": fim - PAREDE / 2,
                "h": max(0.05, h),
            })

    paredes = []
    for tipo, coordenada, inicio, fim in paredes_brutas:
        paredes.extend(_cortar(inicio, fim, coordenada, vaos.get((tipo, coordenada), []),
                               tipo == "h"))
    ambientes.append({
        "nome": "Circulação", "x1": PAREDE / 2, "y1": y_corredor + PAREDE / 2,
        "x2": largura - PAREDE / 2, "y2": y_fundo - PAREDE / 2, "h": 0.16,
    })
    area_util = sum((a["x2"] - a["x1"]) * (a["y2"] - a["y1"]) for a in ambientes)
    area_ambientes = sum(a["area"] for a in ambientes_pedidos)
    area_construida = largura * profundidade

    if terreno_largura is not None and terreno_profundidade is not None:
        x0 = -(recuo_lateral if recuo_lateral is not None else (terreno_largura - largura) / 2)
        y0 = -(recuo_frente or 0)
        terreno = (x0, y0, x0 + terreno_largura, y0 + terreno_profundidade)
    else:
        terreno = (-1.5, -5.0, largura + 1.5, profundidade + 5.0)
        avisos.append("Contorno do terreno ilustrativo: informar largura e profundidade reais")
    if any(v is None for v in (recuo_lateral, recuo_frente, recuo_fundo)):
        avisos.append("Recuos incompletos: confirmar legislação urbanística antes de implantar")
    sello = [
        "PLANTA PRELIMINAR - PROGRAMA SOB MEDIDA",
        f"Ambientes (área líquida): {area_ambientes:.2f} m²",
        f"Circulação + ambientes: {area_util:.2f} m²",
        f"Projeção externa: {area_construida:.2f} m²",
        f"Dimensões externas: {largura:.2f} x {profundidade:.2f} m",
        "Cotas em metros | NÃO É PROJETO EXECUTIVO",
    ]
    selo = [(-1.4, -5.5 - i * 0.25, txt, 0.16) for i, txt in enumerate(sello)]
    return {
        "titulo": str(programa.get("titulo") or "ESTUDO PRELIMINAR - RESIDÊNCIA TÉRREA"),
        "espessura_parede": PAREDE, "pe_direito": pe_direito,
        "terreno": terreno, "paredes": paredes, "parede_sem_sobreposicao": True,
        "ambientes": ambientes, "portas": portas, "janelas": janelas, "moveis": [],
        "cotas_h": [(0.0, largura, -1.0, -1.0)],
        "cotas_v": [(largura + 0.8, 0.0, profundidade, largura + 0.8)],
        "selo": selo, "area_pedida": area_ambientes,
        "avisos": avisos, "resumo_geometria": {
            "largura": largura, "profundidade": round(profundidade, 4),
            "area_ambientes": round(area_ambientes, 4),
            "area_util_total": round(area_util, 4),
            "area_construida": round(area_construida, 4),
            "corredor_livre": CORREDOR_EIXOS - PAREDE,
        },
    }
