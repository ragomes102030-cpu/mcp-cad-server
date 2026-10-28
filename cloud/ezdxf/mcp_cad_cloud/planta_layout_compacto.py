"""Planta residencial térrea 2D: organização compacta com núcleo íntimo.

Motor de referência para exatamente dois quartos, banheiro, sala, cozinha e
lavanderia. Não inventa conformidade normativa; recusa programas fora do
domínio geométrico validado. Unidades do modelo sempre em metros.
"""
from __future__ import annotations

from mcp_cad_cloud.planta_gerador import ErroPrograma, PAREDE, _numero, _opcional, normalizar_programa, _chave

T = PAREDE
ENTRADA = 0.90


def _nome(item):
    return _chave(item["nome"])


def compativel(programa):
    """Tipo de programa para o qual existe uma solução de duas alas + hall."""
    if not isinstance(programa, dict):
        return False
    try:
        itens = normalizar_programa(programa)
        largura = float(programa.get("largura", programa.get("largura_externa", 0)))
    except (ValueError, TypeError, OverflowError, ErroPrograma):
        return False
    if not 8.7 <= largura <= 9.3 or len(itens) != 6:
        return False
    nomes = [_nome(a) for a in itens]
    return (sum("quarto" in n and "banheiro" not in n for n in nomes) == 2
            and sum("banheiro" in n for n in nomes) == 1
            and sum("sala" in n or "estar" in n for n in nomes) == 1
            and sum("cozinha" in n for n in nomes) == 1
            and sum("servico" in n or "lavanderia" in n for n in nomes) == 1)


def gerar_compacto(programa):
    if not compativel(programa):
        raise ErroPrograma("layout compacto exige 2 quartos, sala, cozinha, lavanderia "
                          "e banheiro em largura externa de 8,70 a 9,30 m")
    itens = normalizar_programa(programa)
    largura = _numero(programa.get("largura", programa.get("largura_externa")), "largura", 8.7, 9.3)
    pe_direito = _numero(programa.get("pe_direito", 2.8), "pe_direito", 2.4, 4)
    if "espessura_parede" in programa:
        if abs(_numero(programa["espessura_parede"], "espessura_parede") - T) > 1e-8:
            raise ErroPrograma("layout compacto exige parede de 0,15 m nesta versão")
    quartos = [a for a in itens if "quarto" in _nome(a) and "banheiro" not in _nome(a)]
    banheiro = next(a for a in itens if "banheiro" in _nome(a))
    sala = next(a for a in itens if "sala" in _nome(a) or "estar" in _nome(a))
    cozinha = next(a for a in itens if "cozinha" in _nome(a))
    lavanderia = next(a for a in itens if "servico" in _nome(a) or "lavanderia" in _nome(a))

    # Profundidade é dimensionada para acomodar quartos, banheiro e hall.
    # Ajustar as duas larguras dos quartos em função das áreas líquidas exatas.
    frente = max(4.85, sala["area"] / 3.75 + T)
    fundo = 3.65
    x_esquerda = quartos[0]["area"] / (fundo - T) + T
    x_direita = largura - (quartos[1]["area"] / (fundo - T) + T)
    largura_nucleo = x_direita - x_esquerda
    if not 2.15 <= largura_nucleo <= 2.85:
        raise ErroPrograma("hall central fora das proporções funcionais; "
                          "as áreas dos quartos exigem outro arranjo")
    h_banheiro = banheiro["area"] / (largura_nucleo - T)
    h_hall = fundo - h_banheiro - T
    if not 1.22 <= h_hall <= 1.65:
        raise ErroPrograma("hall de distribuição inviável para a área solicitada do banheiro")
    for quarto, largura_livre in ((quartos[0], x_esquerda-T),
                                  (quartos[1], largura-x_direita-T)):
        if largura_livre < 2.70 or fundo-T < 3:
            raise ErroPrograma(f"{quarto['nome']}: quarto estreito para mobiliário de referência")

    lado_lav = largura-1.85
    x_lav_esq = lado_lav+T/2
    x_lav_dir = largura-T/2
    livre_lav = x_lav_dir-x_lav_esq
    y_lav_top = T/2+lavanderia["area"]/livre_lav
    y_parede_lav = y_lav_top + T/2
    if not 2.65 <= y_parede_lav <= 3.45 or frente-y_parede_lav < 1.2:
        raise ErroPrograma("lavanderia desproporcional; solicite layout com outros módulos")
    x_cozinha_esq = 4.0
    x_cozinha_dir = lado_lav-T/2
    y_cozinha_top = T/2 + cozinha["area"]/(x_cozinha_dir-x_cozinha_esq)
    if not 2.55 <= y_cozinha_top <= y_parede_lav+0.35:
        raise ErroPrograma("cozinha não comporta bancada e circulação neste arranjo")
    x_sala_dir = T/2 + sala["area"]/(frente-T)
    if not 3.20 <= x_sala_dir <= x_cozinha_esq:
        raise ErroPrograma("sala fora das proporções previstas para este módulo")

    profundidade=frente+fundo
    rec_lat=_opcional(programa,"recuo_lateral")
    rec_fr=_opcional(programa,"recuo_frente")
    rec_fd=_opcional(programa,"recuo_fundo")
    terr_larg=_opcional(programa,"terreno_largura")
    terr_prof=_opcional(programa,"terreno_profundidade")
    if terr_larg is not None and terr_larg+1e-8 < largura + 2*(rec_lat or 0):
        raise ErroPrograma("largura do terreno insuficiente para os recuos informados")
    if terr_prof is not None and terr_prof+1e-8 < profundidade+(rec_fr or 0)+(rec_fd or 0):
        raise ErroPrograma("profundidade do terreno insuficiente para os recuos informados")
    if (terr_larg is None) != (terr_prof is None):
        raise ErroPrograma("informe ambas as dimensões do terreno ou nenhuma")

    def ambiente(room, x1, y1, x2, y2, texto_x=None, texto_y=None):
        if x2-x1 < .85 or y2-y1 < .95:
            raise ErroPrograma(f"{room['nome']}: largura ou profundidade inviável")
        return {"nome":room["nome"], "x1":round(x1,8),"y1":round(y1,8),
                "x2":round(x2,8),"y2":round(y2,8),"h":.16,
                "texto_x": round(texto_x if texto_x is not None else (x1+x2)/2,8),
                "texto_y": round(texto_y if texto_y is not None else (y1+y2)/2,8)}

    ambs=[
        ambiente(sala,T/2,T/2,x_sala_dir,frente-T/2,2.85,frente-.85),
        ambiente(cozinha,x_cozinha_esq,T/2,x_cozinha_dir,y_cozinha_top,4.62,2.45),
        ambiente(lavanderia,x_lav_esq,T/2,x_lav_dir,y_lav_top,lado_lav+.90,y_lav_top-.45),
        ambiente(quartos[0],T/2,frente+T/2,x_esquerda-T/2,profundidade-T/2,
                 1.85,frente+1.10),
        ambiente(quartos[1],x_direita+T/2,frente+T/2,largura-T/2,profundidade-T/2,
                 x_direita+1.4,frente+.90),
        ambiente(banheiro,x_esquerda+T/2,frente+h_hall+T/2,
                 x_direita-T/2,profundidade-T/2,
                 (x_esquerda+x_direita)/2,frente+h_hall+1.35),
        ambiente({"nome":"Hall / circulação"},x_esquerda+T/2,frente+T/2,
                 x_direita-T/2,frente+h_hall-T/2),
    ]
    # Mobiliário preliminar, com retângulos em metros. O validador de modelo
    # confirma que as peças estão inteiramente dentro de um ambiente.
    moveis=[
        (.4,frente-1.95,2.40,frente-1.12), (1.05,1.25,2.55,2.05),
        (5.92,.30,6.65,2.43),
        (7.45,.30,8.10,1.04), (8.20,1.30,8.75,1.86),
        (.65,frente+1.45,2.05,frente+3.30),
        (.20,frente+.23,2.0,frente+.68),
        (x_direita+.35,frente+1.48,x_direita+1.30,frente+3.38),
        (x_direita+1.75,frente+1.35,x_direita+2.24,frente+3.35),
        (x_esquerda+.20,profundidade-1.00,x_esquerda+1.04,profundidade-.20),
        (x_esquerda+.25,frente+h_hall+.20,x_esquerda+.83,frente+h_hall+.56),
        (x_esquerda+1.35,frente+h_hall+.32,x_esquerda+1.96,frente+h_hall+1.04),
    ]
    walls=[
        ("h",0.0,0.0,largura),
        ("h",frente,0.0,largura),
        ("h",frente+h_hall,x_esquerda,x_direita),
        ("h",profundidade,0.0,largura),
        ("h",y_parede_lav,lado_lav,largura),
        ("v",0.0,0.0,profundidade),
        ("v",largura,0.0,profundidade),
        ("v",lado_lav,0.0,y_parede_lav),
        ("v",x_esquerda,frente,profundidade),
        ("v",x_direita,frente,profundidade),
    ]
    holes={}
    portas=[]
    janelas=[]
    def vao(tipo,coord,inicio,tam):
        holes.setdefault((tipo,coord),[]).append((inicio,tam))
    def porta(tipo,coord,inicio,tam,angulo):
        vao(tipo,coord,inicio,tam)
        portas.append((inicio,coord,angulo,tam) if tipo=="h"
                      else (coord,inicio,angulo,tam))
    def janela(tipo,coord,inicio,tam):
        vao(tipo,coord,inicio,tam)
        janelas.append((inicio,coord,inicio+tam,coord) if tipo=="h"
                       else (coord,inicio,coord,inicio+tam))

    # Entrada frontal; acesso ao hall é passagem, sem folha projetada.
    porta("h",0.0,.50,ENTRADA,90)
    janela("h",0.0,2.05,1.45)
    janela("h",0.0,4.75,1.40)
    janela("h",0.0,largura-1.18,.72)
    # Acesso da cozinha à lavanderia, folha para a área de serviço.
    porta("v",lado_lav,1.36,.90,0)
    # Abertura contínua sem porta entre sala/cozinha e hall.
    vao("h",frente,x_esquerda+.66,1.05)
    # Portas para os dormitórios e banheiro sempre orientadas ao hall.
    porta("v",x_esquerda,frente+.16,.90,90)
    porta("v",x_direita,frente+.16,.90,0)
    porta("h",frente+h_hall,x_esquerda+.65,.80,90)
    # Janelas externas de dormitórios e banheiro.
    janela("h",profundidade,.95,1.45)
    janela("h",profundidade,(x_esquerda+x_direita)/2-.32,.64)
    janela("h",profundidade,x_direita+.75,1.34)

    def cortar(a,b,coord,intervalos,horizontal):
        cursor=a
        for inicio,tamanho in sorted(intervalos):
            fim=inicio+tamanho
            if inicio<a+0.12-1e-8 or fim>b-0.12+1e-8 or inicio<cursor-1e-8:
                raise ErroPrograma("vão muito próximo a encontro de paredes ou sobreposto")
            if inicio>cursor+1e-8:
                yield ([cursor,coord,inicio,coord] if horizontal else
                       [coord,cursor,coord,inicio])
            cursor=fim
        if cursor<b-1e-8:
            yield ([cursor,coord,b,coord] if horizontal else [coord,cursor,coord,b])
    paredes=[]
    for tp,coord,a,b in walls:
        paredes.extend(cortar(a,b,coord,holes.get((tp,coord),[]),tp=="h"))

    if terr_larg is not None:
        x0=-(rec_lat if rec_lat is not None else (terr_larg-largura)/2)
        y0=-(rec_fr or 0)
        terreno=(x0,y0,x0+terr_larg,y0+terr_prof)
    else:
        terreno=(-1.0,-3.0,largura+1.0,profundidade+4.0)
    area_ambientes=sum(a["area"] for a in itens)
    area_mapeada=sum((a["x2"]-a["x1"])*(a["y2"]-a["y1"]) for a in ambs)
    area_projecao=largura*profundidade
    selos=[
        "ESTUDO PRELIMINAR 2D - RESIDÊNCIA COMPACTA",
        f"Ambientes solicitados: {area_ambientes:.2f} m² | Ambientes mapeados: {area_mapeada:.2f} m²",
        f"Projeção externa: {area_projecao:.2f} m²",
        f"Dimensões externas: {largura:.2f} x {profundidade:.2f} m",
        "ESTUDO CONCEITUAL — SEM APROVAÇÃO NORMATIVA",
    ]
    avisos=[
        "Modelo 2D preliminar: dimensão funcional, esquadrias e circulação precisam de conferência profissional.",
        "Área mapeada não equivale à área útil total medida em levantamento; regiões sociais abertas podem ficar sem demarcação.",
        "Mobiliário esquemático; não comprova acessibilidade nem espaço para todos os equipamentos.",
        "Recuos fornecidos são hipóteses, não regras legais verificadas.",
    ]
    return {
        "titulo":str(programa.get("titulo") or "RESIDÊNCIA TÉRREA 2 QUARTOS - ESTUDO 2D"),
        "espessura_parede":T,"pe_direito":pe_direito,"terreno":terreno,
        "paredes":paredes, "parede_sem_sobreposicao":True,
        "ambientes":ambs, "portas":portas, "janelas":janelas,
        "moveis":[list(m) for m in moveis],
        "cotas_h":[(0.0,largura,-1.0,-1.0)],
        "cotas_v":[(largura+.8,0.0,profundidade,largura+.8)],
        "selo":[(-.95,-4.2-.25*i,text,.16) for i,text in enumerate(selos)],
        "area_pedida":area_ambientes,
        "estrategia":"compacto_2quartos",
        "avisos":avisos,
        "resumo_geometria":{
            "largura":largura,"profundidade":round(profundidade,4),
            "area_ambientes":round(area_ambientes,4),
            "area_util_total":round(area_mapeada,4),
            "area_construida":round(area_projecao,4),
            "hall_livre":round(h_hall-T,4),
            "tipo":"compacto_2quartos",
        },
    }
