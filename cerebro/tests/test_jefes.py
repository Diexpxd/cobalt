"""Pruebas del Bloque D (jefes): claves, migración de estrategias, aprendizaje de derrotas y aviso del protocolo de jefe."""
import io
import json
import os
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("STATUS_FILE", "nox_status.json"), ("TERRENO_FILE", "terreno_sensor.json"), ("VISION_FILE", "vision.json"),
                    ("COMMAND_FILE", "command.json"), ("CONFIG_FILE", "cobalt_config.json"),
                    ("ARCHIVO_ESTRATEGIAS", "estrategias_jefes.json"), ("ARCHIVO_DERROTA", "derrota_jefe.json")]:
    ns[var] = os.path.join(tmp, nombre)


def w(nombre, contenido):
    io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(contenido if isinstance(contenido, str) else json.dumps(contenido))


def leer(nombre):
    return json.load(io.open(os.path.join(tmp, nombre), encoding="utf-8"))


def cmd():
    p = ns["COMMAND_FILE"]
    if not os.path.exists(p):
        return None
    d = json.load(io.open(p, encoding="utf-8"))
    os.remove(p)
    return d


def config(**kw):
    w("cobalt_config.json", kw)
    ns["_CONFIG_CACHE"]["t"] = 0.0


def estado(**kw):
    e = {"is_deployed": True, "is_dead": False, "regen_minutes": 0, "updated_ms": int(time.time() * 1000)}
    e.update(kw)
    w("nox_status.json", e)


def mem():
    return {"ultimo_terreno": 0.0, "ultimo_radar": 0.0, "ultimo_chat_combate": 0.0, "terreno_activo": False, "combate_activo": False}


config()

nk = ns["normalizar_clave_jefe"]
for entrada, esperado in [("entity.minecraft.zombie", "zombie"), ("entity_minecraft_zombie", "zombie"), ("minecraft:ender_dragon", "ender_dragon"),
                          ("Ender Dragon", "ender_dragon"), ("cataclysm:Ignis", "ignis"), ("entity.cataclysm.netherite_monstrosity", "netherite_monstrosity"),
                          ("Ñandú Gigante", "nandu_gigante"), ("  Wither  ", "wither"), ("", "")]:
    r.check(f"clave {entrada!r} -> {esperado!r}", nk(entrada) == esperado)

r.check("sin archivo: 0 cambios", ns["migrar_claves_estrategias"]() == 0)
w("estrategias_jefes.json", {"ignis": {"tactica": "a"}, "entity_minecraft_zombie": {"tactica": "z"}, "ender_golem": {"tactica": "g"}})
r.check("renombra 1 clave heredada", ns["migrar_claves_estrategias"]() == 1)
datos = leer("estrategias_jefes.json")
r.check("'entity_minecraft_zombie' pasó a 'zombie' conservando su contenido", "zombie" in datos and datos["zombie"] == {"tactica": "z"} and "entity_minecraft_zombie" not in datos)
r.check("las demás entradas quedan intactas", datos["ignis"] == {"tactica": "a"} and datos["ender_golem"] == {"tactica": "g"})
r.check("crea la copia .bak con el contenido ORIGINAL", "entity_minecraft_zombie" in leer("estrategias_jefes.json.bak"))
r.check("es idempotente (segunda pasada: 0 cambios)", ns["migrar_claves_estrategias"]() == 0)
w("estrategias_jefes.json", {"zombie": {"tactica": "nuevo"}, "entity_minecraft_zombie": {"tactica": "viejo"}})
ns["migrar_claves_estrategias"]()
datos = leer("estrategias_jefes.json")
r.check("colisión: no se pierde NINGUNA entrada", len(datos) == 2 and datos["zombie"] == {"tactica": "nuevo"} and {"tactica": "viejo"} in datos.values())
w("estrategias_jefes.json", '{"roto": ')
r.check("archivo roto: no lo toca ni lanza excepción", ns["migrar_claves_estrategias"]() == 0 and open(ns["ARCHIVO_ESTRATEGIAS"], encoding="utf-8").read() == '{"roto": ')

jr = ns["jefes_en_radar"]
r.check("jefes_en_radar: extrae el nombre del jefe", jr("Radar de Hostiles (32m): 2 detectados - [JEFE] Ender Dragon (20.0m), Zombi (5.0m)") == ["Ender Dragon"])
r.check("jefes_en_radar: sin jefes -> []", jr("Radar de Hostiles (32m): 1 detectados - Zombi (5.0m)") == [])
r.check("jefes_en_radar: dos jefes", jr("Radar de Hostiles (32m): 2 detectados - [JEFE] Wither (10.0m), [JEFE] Warden (12.5m*)") == ["Wither", "Warden"])
w("estrategias_jefes.json", {"ignis": {"mensaje_alerta": "¡Ignis!"}, "ender_golem": {"mensaje_alerta": "¡Golem!"}, "zom": {"mensaje_alerta": "no"}})
ep = ns["estrategia_para_jefe"]
r.check("estrategia por nombre del radar ('Ignis')", ep("Ignis")["mensaje_alerta"] == "¡Ignis!")
r.check("estrategia con espacios ('Ender Golem')", ep("Ender Golem")["mensaje_alerta"] == "¡Golem!")
r.check("jefe sin estrategia -> None", ep("Warden") is None)
r.check("las claves cortas (<4 letras) no coinciden por subcadena ('zom' no casa con 'Zombi')", ep("Zombi") is None)

w("terreno_sensor.json", "Terreno seguro.")
JEFE_CERCA = "Radar de Hostiles (32m): 5 detectados - [JEFE] Ignis (12.0m), Zombi (1.0m), Zombi (2.0m), Zombi (3.0m), Zombi (4.0m)"
w("vision.json", JEFE_CERCA)
estado(emp_ready=True)
m = mem()
ns["ciclo_reflejos"](m, ahora=1000.0)
c = cmd()
r.check("con jefe: solo defend + shoot_plasma (SIN special_power aunque haya 4 cerca)", [o["action"] for o in c] == ["defend", "shoot_plasma"])
r.check("con jefe: el aviso usa la estrategia recordada", c[0].get("chat_message") == "¡Ignis!")
ns["ciclo_reflejos"](m, ahora=1010.0)
c = cmd()
r.check("el aviso del mismo jefe no se repite antes de 5 min (pero el combate sí continúa)", c and c[0]["action"] == "defend" and "chat_message" not in c[0])
ns["ciclo_reflejos"](m, ahora=1400.0)
c = cmd()
r.check("pasados 5 min el aviso vuelve", c and "chat_message" in c[0])

w("vision.json", "Radar de Hostiles (32m): 1 detectados - [JEFE] Warden (10.0m)")
m = mem()
ns["ciclo_reflejos"](m, ahora=2000.0)
c = cmd()
r.check("jefe sin estrategia guardada: mensaje genérico con su nombre", "Warden" in c[0]["chat_message"] and "solo plasma" in c[0]["chat_message"])

config(modo_jefe=False)
w("vision.json", JEFE_CERCA)
m = mem()
ns["ciclo_reflejos"](m, ahora=3000.0)
c = cmd()
r.check("interruptor modo_jefe=false: vuelve el comportamiento normal (con special_power)", [o["action"] for o in c] == ["defend", "shoot_plasma", "special_power"])
config()

llamadas = {"web": [], "nube": 0}


def web(consulta):
    llamadas["web"].append(consulta)
    return "El Wither es débil al daño a distancia."


RESPUESTA = 'Claro, aquí tienes:\n```json\n{"tactica": "Mantén distancia", "movement_mode_obligatorio": "fly", "accion_recomendada": "shoot_plasma", "mensaje_alerta": "¡Wither!"}\n```'


def nube(prompt, timeout_s=8.0, rol=None):
    llamadas["nube"] += 1
    return RESPUESTA


ns["buscar_en_internet"] = web
ns["consultar_gemini_o_fallback"] = nube
w("estrategias_jefes.json", {})

w("derrota_jefe.json", {"jefe": "Wither", "id": "minecraft:wither", "es_jefe": True, "motivo": "derrota", "ts": 1})
ns["autoaprender_de_derrota"]()
datos = leer("estrategias_jefes.json")
r.check("jefe nuevo: investiga y guarda la estrategia bajo la clave normalizada 'wither'", "wither" in datos and datos["wither"]["tactica"] == "Mantén distancia")
r.check("...con valores validados y el nombre real", datos["wither"]["accion_recomendada"] == "shoot_plasma" and datos["wither"]["nombre"] == "Wither")
r.check("consume derrota_jefe.json", not os.path.exists(ns["ARCHIVO_DERROTA"]))
r.check("la consulta web usa el NOMBRE legible", llamadas["web"] == ["Minecraft Wither boss strategy weakness guide"])

llamadas["web"].clear(); llamadas["nube"] = 0
w("derrota_jefe.json", {"jefe": "Zombi", "id": "minecraft:zombie", "es_jefe": False, "motivo": "derrota", "ts": 2})
ns["autoaprender_de_derrota"]()
r.check("un ZOMBI que mata a Cobalt NO gasta búsquedas ni nube (antes se guardaba como 'jefe')", llamadas["web"] == [] and llamadas["nube"] == 0)
r.check("...ni añade estrategias", "zombie" not in leer("estrategias_jefes.json"))
r.check("...y consume el archivo igualmente", not os.path.exists(ns["ARCHIVO_DERROTA"]))

w("derrota_jefe.json", {"jefe": "entity.minecraft.zombie"})
ns["autoaprender_de_derrota"]()
r.check("formato ANTIGUO con un zombi: no se investiga", llamadas["web"] == [])
w("derrota_jefe.json", {"jefe": "entity.minecraft.wither"})
ns["autoaprender_de_derrota"]()
r.check("formato ANTIGUO con un jefe conocido (wither): sí se investiga", len(llamadas["web"]) == 1)

llamadas["web"].clear()
w("derrota_jefe.json", {"jefe": "Ignis", "id": "cataclysm:ignis", "es_jefe": True, "motivo": "huida", "ts": 3})
ns["autoaprender_de_derrota"]()
r.check("una HUIDA ante un jefe también se aprende (clave 'ignis' sin el prefijo del mod)", "ignis" in leer("estrategias_jefes.json"))

ns["consultar_gemini_o_fallback"] = lambda p, timeout_s=8.0, rol=None: "lo siento, no puedo darte JSON"
w("estrategias_jefes.json", {})
w("derrota_jefe.json", {"jefe": "Warden", "id": "minecraft:warden", "es_jefe": True, "motivo": "derrota", "ts": 4})
ns["autoaprender_de_derrota"]()
r.check("respuesta del LLM sin JSON: no se rompe ni guarda basura", leer("estrategias_jefes.json") == {})

ns["consultar_gemini_o_fallback"] = lambda p, timeout_s=8.0, rol=None: '{"tactica": 5, "movement_mode_obligatorio": "teletransporte", "accion_recomendada": "explotar"}'
w("derrota_jefe.json", {"jefe": "Warden", "id": "minecraft:warden", "es_jefe": True, "motivo": "derrota", "ts": 5})
ns["autoaprender_de_derrota"]()
e = leer("estrategias_jefes.json")["warden"]
r.check("valores inválidos del LLM se sustituyen por los seguros (fly / shoot_plasma)", e["movement_mode_obligatorio"] == "fly" and e["accion_recomendada"] == "shoot_plasma" and isinstance(e["tactica"], str))

config(registro_derrotas_jefe=False)
llamadas["web"].clear()
w("derrota_jefe.json", {"jefe": "Wither", "id": "minecraft:wither", "es_jefe": True, "motivo": "derrota", "ts": 6})
ns["autoaprender_de_derrota"]()
r.check("interruptor registro_derrotas_jefe=false: no investiga y NO consume el archivo", llamadas["web"] == [] and os.path.exists(ns["ARCHIVO_DERROTA"]))
config()

w("derrota_jefe.json", '{"jefe": "Wit')
ns["autoaprender_de_derrota"]()
r.check("derrota_jefe.json corrupto: no lanza excepción", True)

r.terminar()
