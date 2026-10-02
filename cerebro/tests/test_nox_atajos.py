"""Atajos de chat tolerantes (nox_atajos): detener, seguir, ven, recoger del suelo y guardar algo concreto."""
import os
import sys

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_atajos as a  # noqa: E402

r = Resultados()

for frase in ("detente", "Detente!", "quédate", "quedate aquí", "quédate ahí", "Cobalt, detente por favor", "espera", "espérame", "espera un momento", "alto", "ALTO", "para", "stop",
              "no me sigas", "deja de seguirme", "no te muevas", "quieto", "frena"):
    r.check(f"detener: '{frase}'", a.interpretar_detener(frase) is True)
for frase in ("para de decir tonterías", "espera, que te cuento algo", "quédate con la espada", "no me sigas el juego", "detente a pensar en lo que hiciste", "hola", "ven"):
    r.check(f"detener NO se dispara con: '{frase}'", a.interpretar_detener(frase) is False)

for frase in ("sígueme", "sigueme", "Sígueme por favor", "acompáñame", "follow me"):
    r.check(f"seguir: '{frase}'", a.interpretar_seguir(frase) is True)
for frase in ("sígueme el rollo", "sigue minando", "ven"):
    r.check(f"seguir NO: '{frase}'", a.interpretar_seguir(frase) is False)
for frase in ("ven", "Ven aquí", "ven aca", "acércate", "Cobalt, ven por favor"):
    r.check(f"ven: '{frase}'", a.interpretar_ven(frase) is True)
for frase in ("ven atiende los hornos", "ven a las coordenadas 10 64 10", "ven y sígueme", "que ven"):
    r.check(f"ven NO (es una orden compuesta, la entiende el modelo): '{frase}'", a.interpretar_ven(frase) is False)

x = a.interpretar_recoger("recoge la carne podrida")
r.check("recoger: 'recoge la carne podrida' -> material carne podrida, sin entregar", x == {"material": "carne podrida", "radio": 16, "entregar": False})
x = a.interpretar_recoger("tráeme la carne que tiré")
r.check("recoger: 'tráeme la carne que tiré' -> carne, y la entrega", x and x["material"] == "carne" and x["entregar"] is True)
x = a.interpretar_recoger("recoge los diamantes en 20 bloques y dámelos")
r.check("recoger: radio y entrega", x and x["material"] == "diamantes" and x["radio"] == 20 and x["entregar"] is True)
x = a.interpretar_recoger("recoge lo que tiré")
r.check("recoger: 'lo que tiré' = todo (material None)", x and x["material"] is None)
x = a.interpretar_recoger("Cobalt, recoge todo lo que hay en el suelo por favor")
r.check("recoger: 'todo lo que hay en el suelo' = todo", x and x["material"] is None)
x = a.interpretar_recoger("recoge los objetos del suelo en 500 bloques")
r.check("recoger: el radio se limita a 48", x and x["radio"] == 48)
x = a.interpretar_recoger("agarra la pala que deje caer")
r.check("recoger: 'agarra la pala que deje caer' -> pala", x and x["material"] == "pala")
for frase in ("recoge la cosecha", "recoge los cultivos maduros", "trae 8 semillas del cofre", "tráeme hierro del baúl", "recoge la mena de hierro", "trae a mi perro", "hola", "guarda todo en el cofre"):
    r.check(f"recoger NO se dispara con: '{frase}'", a.interpretar_recoger(frase) is None)

x = a.interpretar_guardar("deja los cultivos en el cofre")
r.check("guardar: 'los cultivos' -> lista de cultivos (con trigo y patatas)", x and x["csv"] and "minecraft:wheat" in x["csv"] and "minecraft:potato" in x["csv"])
x = a.interpretar_guardar("guarda las semillas en el cofre")
r.check("guardar: 'las semillas' -> sufijo seeds (sirve para las de mods)", x and "seeds" in x["csv"].split(","))
x = a.interpretar_guardar("mete la carne en un cofre")
r.check("guardar: algo concreto sin categoría -> material tal cual (se traduce fuera)", x and x["material"] == "carne" and x["csv"] is None)
r.check("guardar: 'el pico en mi cofre'", (a.interpretar_guardar("guarda el pico en mi cofre") or {}).get("material") == "pico")
for frase in ("guarda todo en el cofre", "guarda todo", "guarda las cosas en el cofre", "guarda todo lo que llevas en el cofre", "deja de molestar", "hola", "pon una antorcha aquí"):
    r.check(f"guardar NO se dispara con: '{frase}'", a.interpretar_guardar(frase) is None)

x = a.interpretar_talar("tala un árbol")
r.check("talar: 'tala un árbol' -> unos 8 troncos", x == {"cantidad": 8, "radio": 16})
x = a.interpretar_talar("corta 20 troncos")
r.check("talar: 'corta 20 troncos' -> 20", x and x["cantidad"] == 20)
x = a.interpretar_talar("consígueme 64 de madera")
r.check("talar: 'consígueme 64 de madera' -> 64", x and x["cantidad"] == 64)
x = a.interpretar_talar("tala 3 árboles")
r.check("talar: '3 árboles' -> 3 x 8 troncos", x and x["cantidad"] == 24)
x = a.interpretar_talar("tala árboles en 25 bloques")
r.check("talar: radio pedido", x and x["radio"] == 25 and x["cantidad"] == 32)
x = a.interpretar_talar("tala 500 troncos en 100 bloques")
r.check("talar: cantidad tope 256 y radio tope 32", x and x["cantidad"] == 256 and x["radio"] == 32)
x = a.interpretar_talar("Cobalt, por favor, tala")
r.check("talar: 'tala' a secas -> lo de siempre (32 troncos)", x == {"cantidad": 32, "radio": 16})
r.check("talar: 'puedes cortar un tronco' -> 1", (a.interpretar_talar("puedes cortar un tronco") or {}).get("cantidad") == 1)
for frase in ("corta el pelo", "consigue diamantes", "consigue madera del cofre", "corta madera en tablas", "corta", "consigue", "hola", "recoge madera", "cortame la cuerda", "tala la conversación"):
    r.check(f"talar NO se dispara con: '{frase}'", a.interpretar_talar(frase) is None)

x = a.interpretar_pescar("pesca")
r.check("pescar: 'pesca' a secas -> 8 capturas en 16 bloques, sin plazo", x == {"cantidad": 8, "radio": 16, "minutos": 0})
r.check("pescar: 've a pescar' y 'ponte a pescar unos peces'", a.interpretar_pescar("ve a pescar") == x and a.interpretar_pescar("ponte a pescar unos peces") == x)
r.check("pescar: 'pesca 10 peces' -> 10", (a.interpretar_pescar("pesca 10 peces") or {}).get("cantidad") == 10)
x = a.interpretar_pescar("pesca durante 5 minutos")
r.check("pescar: 'pesca durante 5 minutos' -> plazo de 5 min y sin tope de capturas (64)", x and x["minutos"] == 5 and x["cantidad"] == 64)
x = a.interpretar_pescar("pesca 5 minutos en 20 bloques")
r.check("pescar: plazo y radio a la vez", x and x["minutos"] == 5 and x["radio"] == 20)
r.check("pescar: radio con tope de 32", a.interpretar_pescar("pesca en 100 bloques")["radio"] == 32)
r.check("pescar: capturas con tope de 64 y mínimo de 1", a.interpretar_pescar("pesca 500 peces")["cantidad"] == 64 and a.interpretar_pescar("pesca 0 peces")["cantidad"] == 1)
r.check("pescar: el plazo tiene tope de 20 min", a.interpretar_pescar("pesca 90 minutos")["minutos"] == 20)
for frase in ("pesca tonterias", "pesca y luego mina", "hola", "el pescado esta rico", "pescado frito"):
    r.check(f"pescar NO se dispara con: '{frase}'", a.interpretar_pescar(frase) is None)

x = a.interpretar_craftear("craftea 8 antorchas")
r.check("craftear: 'craftea 8 antorchas' -> 8 antorchas, verbo explícito", x == {"objeto": "antorchas", "cantidad": 8, "explicito": True})
x = a.interpretar_craftear("hazme un pico de hierro")
r.check("craftear: 'hazme un pico de hierro' -> 1 pico de hierro, verbo NO explícito (puede ser una obra)", x == {"objeto": "pico de hierro", "cantidad": 1, "explicito": False})
r.check("craftear: 'fabrica 2 hornos' -> 2", (a.interpretar_craftear("fabrica 2 hornos") or {}).get("cantidad") == 2)
r.check("craftear: 'una docena de palos' = 12 y 'media docena de antorchas' = 6", a.interpretar_craftear("craftea una docena de palos")["cantidad"] == 12 and a.interpretar_craftear("hazme media docena de antorchas")["cantidad"] == 6)
r.check("craftear: cantidad con tope de 256", a.interpretar_craftear("craftea 300 palos")["cantidad"] == 256)
r.check("craftear: 'con lo que tengas' y 'por favor' no forman parte del objeto", a.interpretar_craftear("Cobalt, hazte una espada de diamante con lo que tengas por favor")["objeto"] == "espada de diamante")
x = a.interpretar_craftear("craftea botania:mana_pool")
r.check("craftear: un id de mod con ':' se conserva entero y es explícito", x and x["objeto"] == "botania:mana_pool" and x["explicito"] is True)
x = a.interpretar_craftear("haz un camino a la base")
r.check("craftear: 'haz un camino a la base' se reconoce como 'haz X' pero NO es un objeto conocido ni explícito (quien llama lo deja pasar a la obra)", x and x["explicito"] is False and a.ids_de(x["objeto"]) is None)
r.check("craftear: 'crea una casa' igual", a.ids_de(a.interpretar_craftear("crea una casa")["objeto"]) is None)
for frase in ("haz", "craftea algo", "fabrica", "hola", "el pico se fabrica con hierro", "me gusta craftear"):
    r.check(f"craftear NO se dispara con: '{frase}'", a.interpretar_craftear(frase) is None)
r.check("ids: 'picos de hierro' (plural de la primera palabra) -> el pico, no el hierro", a.ids_de("picos de hierro") == "minecraft:iron_pickaxe")
r.check("ids: herramientas por material (5 x 5) y armaduras (6 x 5)", all(a.ids_de(f"{t} de {m}") == f"minecraft:{e}_{n}" for t, n in a._HERRAMIENTAS.items() for m, e in a._MATERIALES.items())
        and all(a.ids_de(f"{t} de {m}") == f"minecraft:{e}_{n}" for t, n in a._ARMADURAS.items() for m, e in a._MATERIALES_ARMADURA.items()))
r.check("ids: mesa de crafteo, horno, antorcha, cofre, caña de pescar", a.ids_de("mesa de crafteo") == "minecraft:crafting_table" and a.ids_de("horno") == "minecraft:furnace"
        and a.ids_de("antorchas") == "minecraft:torch" and a.ids_de("cofre") == "minecraft:chest" and a.ids_de("cañas de pescar") == "minecraft:fishing_rod")
r.check("ids: lo de siempre no cambia ('hierro' sigue siendo el material, 'palos' el palo)", "raw_iron" in a.ids_de("hierro") and a.ids_de("palos") == "minecraft:stick")

r.check("ids: 'semillas' -> sufijo seeds (no 'infernalium_seed')", a.ids_de("semillas").split(",")[0] == "seeds")
r.check("ids: 'la carne podrida' -> rotten_flesh", a.ids_de("la carne podrida") == "minecraft:rotten_flesh")
r.check("ids: 'carne' incluye cruda, cocida y podrida", all(x in a.ids_de("carne") for x in ("beef", "cooked_beef", "rotten_flesh")))
r.check("ids: plural 'diamantes'", a.ids_de("diamantes") == "minecraft:diamond")
r.check("ids: plural de una clave corta ('palos', 'telas' no)", a.ids_de("palos") == "minecraft:stick" and a.ids_de("los palos") == "minecraft:stick")
r.check("ids: 'hierro' = ítems (crudo, lingote, pepita), no la mena", "raw_iron" in a.ids_de("hierro") and "ore" not in a.ids_de("hierro"))
r.check("ids: 'trozos de carne de cerdo' -> reconoce la clave larga", "porkchop" in a.ids_de("trozos de carne de cerdo"))
r.check("ids: algo desconocido -> None (lo decide el traductor)", a.ids_de("infernalium") is None and a.ids_de("") is None)

r.terminar()
