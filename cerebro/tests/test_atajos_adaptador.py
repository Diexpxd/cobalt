"""Cableado de nox_atajos en cerebro.py (aplicar_cortocircuito): las frases que el jugador probó de verdad ('quédate', 'recoge la carne podrida', 'deja los cultivos en el"""
import io
import json
import os
import tempfile

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("STATUS_FILE", "nox_status.json"), ("GPS_FILE", "gps.json"), ("ENTIDADES_FILE", "entities.json")]:
    ns[var] = os.path.join(tmp, nombre)
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
llamadas_modelo = []
ns["traducir_material"] = lambda m: (llamadas_modelo.append(m), "iron_ore")[1]   # el modelo NO debe intervenir en lo que el diccionario ya sabe


def recargar():
    ns["_CONFIG_CACHE"]["t"] = 0.0


def cortocircuito(msg):
    recargar()
    return ns["aplicar_cortocircuito"](msg, "Steve")


def accion(msg):
    o = cortocircuito(msg)
    return o[0]["action"] if o else None


for frase, esperada in (("quédate", "stop"), ("Cobalt, detente por favor", "stop"), ("no me sigas", "stop"), ("espera un momento", "stop"), ("alto", "stop"),
                        ("sígueme por favor", "follow"), ("acompáñame", "follow"), ("ven aquí", "ven"), ("Cobalt, ven", "ven")):
    r.check(f"'{frase}' -> {esperada}", accion(frase) == esperada)
r.check("'para de decir tonterías' NO detiene a Cobalt", accion("para de decir tonterías") != "stop")
r.check("'espera, que te cuento algo' NO detiene a Cobalt", accion("espera, que te cuento algo") != "stop")

o = cortocircuito("recoge la carne podrida")
r.check("'recoge la carne podrida' -> pickup de rotten_flesh (no minar)", o and len(o) == 1 and o[0]["action"] == "pickup" and o[0]["material"] == "minecraft:rotten_flesh" and o[0]["radius"] == 16)
o = cortocircuito("tráeme la carne que tiré")
r.check("'tráeme la carne que tiré' -> pickup + give de carne", o and [x["action"] for x in o] == ["pickup", "give"] and "minecraft:beef" in o[0]["material"] and o[1]["material"] == o[0]["material"])
o = cortocircuito("recoge lo que tiré")
r.check("'recoge lo que tiré' -> pickup de todo", o and o[0]["action"] == "pickup" and o[0]["material"] == "cualquiera")
o = cortocircuito("recoge los diamantes en 20 bloques")
r.check("radio pedido", o and o[0]["radius"] == 20 and o[0]["material"] == "minecraft:diamond")
r.check("el modelo NO se usó para traducir lo que el diccionario ya sabe", llamadas_modelo == [])
r.check("'recoge la cosecha' sigue siendo la cosecha (harvest), no un pickup", accion("recoge la cosecha") == "harvest")

o = cortocircuito("deja los cultivos en el cofre")
r.check("'deja los cultivos en el cofre' -> store con la lista de cultivos", o and o[0]["action"] == "store" and "minecraft:wheat" in o[0]["material"] and "minecraft:carrot" in o[0]["material"])
o = cortocircuito("guarda las semillas en el cofre")
r.check("'guarda las semillas' -> store con sufijo seeds", o and o[0]["action"] == "store" and "seeds" in o[0]["material"].split(","))

o = cortocircuito("tala un árbol")
r.check("'tala un árbol' -> chop_wood de unos 8 troncos", o and len(o) == 1 and o[0]["action"] == "chop_wood" and o[0]["amount"] == 8 and o[0]["radius"] == 16)
o = cortocircuito("consigue 40 de madera en 24 bloques")
r.check("'consigue 40 de madera en 24 bloques' -> chop_wood con cantidad y radio", o and o[0]["action"] == "chop_wood" and o[0]["amount"] == 40 and o[0]["radius"] == 24)
r.check("'corta madera en tablas' NO tala", accion("corta madera en tablas") != "chop_wood")
io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({"tala": False}))
r.check("tala=false: 'tala un árbol' ya no es un atajo", accion("tala un árbol") != "chop_wood")
io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({}))

o = cortocircuito("ve a pescar")
r.check("'ve a pescar' -> fish de 8 capturas en 16 bloques", o and len(o) == 1 and o[0]["action"] == "fish" and o[0]["amount"] == 8 and o[0]["radius"] == 16 and "minutes" not in o[0])
o = cortocircuito("pesca durante 5 minutos")
r.check("'pesca durante 5 minutos' -> fish con plazo (minutes)", o and o[0]["action"] == "fish" and o[0]["minutes"] == 5)
r.check("'pesca tonterías' NO es un atajo", accion("pesca tonterías") != "fish")
io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({"pesca": False}))
r.check("pesca=false: 've a pescar' ya no es un atajo", accion("ve a pescar") != "fish")
io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({}))

o = cortocircuito("craftea 8 antorchas")
r.check("'craftea 8 antorchas' -> craft de 8 minecraft:torch, sin usar el modelo", o and len(o) == 1 and o[0]["action"] == "craft" and o[0]["amount"] == 8 and o[0]["material"] == "minecraft:torch" and llamadas_modelo == [])
o = cortocircuito("hazme un pico de hierro")
r.check("'hazme un pico de hierro' (objeto conocido) -> craft de minecraft:iron_pickaxe", o and o[0]["action"] == "craft" and o[0]["material"] == "minecraft:iron_pickaxe" and o[0]["amount"] == 1)
o = cortocircuito("fabricame 3 picos de hierro")
r.check("'fabricame 3 picos de hierro' -> 3 picos (no el hierro)", o and o[0]["action"] == "craft" and o[0]["material"] == "minecraft:iron_pickaxe" and o[0]["amount"] == 3)
o = cortocircuito("craftea botania:mana_pool")
r.check("un id de mod se envía tal cual (sin traducir con el modelo)", o and o[0]["action"] == "craft" and o[0]["material"] == "botania:mana_pool" and llamadas_modelo == [])
o = cortocircuito("hazme 64 tablones")
r.check("'hazme 64 tablones' -> craft de 'planks' (Java elige la madera que pueda fabricar)", o and o[0]["action"] == "craft" and o[0]["material"] == "planks" and o[0]["amount"] == 64)
io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({"crafteo": False}))
r.check("crafteo=false: 'craftea 8 antorchas' ya no es un atajo", accion("craftea 8 antorchas") != "craft")
io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({}))

io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps({"atajos_chat": False}))
r.check("atajos_chat=false: 'quédate' ya no se reconoce", accion("quédate") != "stop")
r.check("atajos_chat=false: 'alto' (la frase exacta de siempre) sigue funcionando", accion("alto") == "stop")
r.check("atajos_chat=false: 'recoge la carne podrida' ya no es un atajo", accion("recoge la carne podrida") != "pickup")

fuente = io.open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro", "cerebro.py"), encoding="utf-8").read()
linea = fuente[fuente.index("VALORES DE ACCI"):].split("\n")[0]
r.check("el prompt del planificador permite 'pickup'", "'pickup'" in linea)
r.check("el prompt del planificador permite 'chop_wood' (talar)", "'chop_wood'" in linea)
r.check("el prompt del planificador permite 'fish' (pescar)", "'fish'" in linea)
r.check("el prompt del planificador permite 'craft' (fabricar) y ya no dice que no sabe craftear", "'craft'" in linea and "NO sabes fabricar" not in fuente)

r.terminar()
