# Validação dos ambientes (coordenadas internas) a partir do spec do cliente.
# Os pontos de entrada são os limites dos ambientes (interiores) e as portas/janelas.
# As regras:
#  - parede interna entre dois ambientes tem 0,10 m de espessura (xou).
#  - a parede externa tem 0,20 m de espessura.
#  - cada abertura (porta/janela) é recortada na parede correspondente.
#  - as dimensões internas dos ambientes são:
#      Sala: x=0.20..5.20, y=0.20..4.20
#      Cozinha: x=5.30..9.80, y=0.20..3.00
#      Lavanderia: x=5.30..7.30, y=3.10..4.20
#      Banheiro social: x=7.40..9.80, y=3.10..4.20
#      Suíte: x=0.20..4.00, y=4.30..7.80
#      Quarto 2: x=4.10..6.80, y=4.30..7.80
#      Banheiro da suíte: x=6.90..9.80, y=4.30..6.00
#      Circulação: x=3.10..5.20, y=4.30..7.80

import json

out = {}

# --- Paredes externas (espessura 0.20 m) ---
out["external_walls"] = {
    "south":  {"x1": 0.0,  "y1": 0.0,  "x2": 10.0, "y2": 0.2,  "color": 7},
    "north":  {"x1": 0.0,  "y1": 7.8,  "x2": 10.0, "y2": 8.0,  "color": 7},
    "west":   {"x1": 0.0,  "y1": 0.0,  "x2": 0.2,  "y2": 8.0,  "color": 7},
    "east":   {"x1": 9.8,  "y1": 0.0,  "x2": 10.0, "y2": 8.0,  "color": 7},
}

# --- Paredes internas (espessura 0.10 m) ---
out["internal_walls"] = [
    # x=5.25 (sala <-> cozinha/lavanderia): y de 0.20 a 4.20
    {"x1": 5.20, "y1": 0.20, "x2": 5.30, "y2": 4.20, "color": 8, "between": ["SALA", "COZINHA"]},
    # y=3.05 (cozinha <-> lavanderia): x de 5.30 a 9.80
    {"x1": 5.30, "y1": 3.00, "x2": 9.80, "y2": 3.10, "color": 8, "between": ["COZINHA", "LAVANDERIA"]},
    # x=7.35 (lavanderia <-> banheiro social): y de 3.10 a 4.20
    {"x1": 7.30, "y1": 3.10, "x2": 7.40, "y2": 4.20, "color": 8, "between": ["LAVANDERIA", "BANHEIRO_SOCIAL"]},
    # y=4.25 (sala <-> suíte/quarto 2): x de 0.20 a 5.20
    {"x1": 0.20, "y1": 4.20, "x2": 5.20, "y2": 4.30, "color": 8, "between": ["SALA", "SUITE_CORR"]},
    # x=4.05 (suíte <-> quarto 2): y de 4.30 a 7.80
    {"x1": 4.00, "y1": 4.30, "x2": 4.10, "y2": 7.80, "color": 8, "between": ["SUITE", "QUARTO_2"]},
    # x=6.85 (quarto 2 <-> banheiro da suíte): y de 4.30 a 6.00
    {"x1": 6.80, "y1": 4.30, "x2": 6.90, "y2": 6.00, "color": 8, "between": ["QUARTO_2", "BANHEIRO_SUITE"]},
]

# --- Aberturas (portas/janela) - recortes nas paredes ---
out["openings"] = {
    "PORTA_01": {"wall": "south",         "x1": 2.05, "y1": 0.0, "x2": 2.95, "y2": 0.20, "width": 0.90, "label": "ENTRADA PRINCIPAL", "color": 3},
    "PORTA_02": {"wall": "x5.25",         "x1": 5.20, "y1": 0.80, "x2": 5.30, "y2": 1.60, "width": 0.80, "label": "SALA -> COZINHA", "color": 3},
    "PORTA_03": {"wall": "y3.05",         "x1": 5.80, "y1": 3.00, "x2": 6.60, "y2": 3.10, "width": 0.80, "label": "COZINHA -> LAVANDERIA", "color": 3},
    "PORTA_04": {"wall": "x7.35",         "x1": 7.30, "y1": 3.40, "x2": 7.40, "y2": 4.10, "width": 0.70, "label": "BANHEIRO SOCIAL", "color": 3},
    "PORTA_05": {"wall": "x4.05",         "x1": 4.00, "y1": 5.00, "x2": 4.10, "y2": 5.80, "width": 0.80, "label": "QUARTO 2", "color": 3},
    "PORTA_06": {"wall": "y4.25",         "x1": 2.00, "y1": 4.20, "x2": 2.80, "y2": 4.30, "width": 0.80, "label": "SUÍTE (DE CIMA)", "color": 3},
    "PORTA_07": {"wall": "x6.85",         "x1": 6.80, "y1": 4.60, "x2": 6.90, "y2": 5.30, "width": 0.70, "label": "BANHEIRO DA SUÍTE", "color": 3},
    "JANELA_01": {"wall": "north",        "x1": 1.50, "y1": 7.80, "x2": 3.50, "y2": 8.00, "width": 2.00, "label": "SALA", "color": 4},
    "JANELA_02": {"wall": "east",         "x1": 9.80, "y1": 1.00, "x2": 10.00, "y2": 2.20, "width": 1.20, "label": "COZINHA", "color": 4},
    "JANELA_03": {"wall": "west",         "x1": 0.0, "y1": 5.00, "x2": 0.20, "y2": 6.20, "width": 1.20, "label": "QUARTO 2", "color": 4},
    "JANELA_04": {"wall": "north_suite",  "x1": 1.00, "y1": 7.80, "x2": 2.50, "y2": 8.00, "width": 1.50, "label": "SUÍTE", "color": 4},
}

with open("ambientes_validados.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("escrito ambientes_validados.json")
print(json.dumps(out, ensure_ascii=False, indent=2)[:3000])
