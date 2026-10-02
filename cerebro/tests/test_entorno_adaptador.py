"""H4 (adaptador en cerebro.py): el prompt del modelo recibe la SITUACIÓN ACTUAL leída de los sensores; el jugador puede pedir un informe por chat y se responde sin"""
import io
import json
import os
import tempfile
import time

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("STATUS_FILE", "nox_status.json"), ("GPS_FILE", "gps.json"), ("ENTIDADES_FILE", "entities.json"),
                    ("ARCHIVO_EXPERIENCIA", "experiencia_combate.json"), ("MOD_KNOWLEDGE_FILE", "conocimiento_mods.json")]:
    ns[var] = os.path.join(tmp, nombre)
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
nv = ns["nox_voz"]

import datetime as _dt  # noqa: E402
import types  # noqa: E402


class _Fijo(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 20, 12, 0, 0)


ns["datetime"] = types.SimpleNamespace(datetime=_Fijo, timedelta=_dt.timedelta, date=_dt.date, time=_dt.time, timezone=_dt.timezone)


def w(nombre, datos):
    io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(json.dumps(datos))


def quitar(nombre):
    p = os.path.join(tmp, nombre)
    if os.path.exists(p):
        os.remove(p)


def config(**c):
    w("cobalt_config.json", c)
    ns["_CONFIG_CACHE"]["t"] = 0.0


def sensores(hora=15000, hostiles=(), vivo=True, hp_jugador=18.0):
    w("nox_status.json", {"is_deployed": True, "is_dead": False, "updated_ms": time.time() * 1000, "hp": 20.0, "max_hp": 20.0})
    w("gps.json", {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 3, "y": 64, "z": 4, "hp": hp_jugador, "max_hp": 20.0, "alive": True},
                   "mundo": {"day_time": hora, "raining": False, "thundering": False, "has_skylight": True, "sky": True, "light": 15}})
    d = {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "entities": list(hostiles)}
    if vivo:
        d["bot"] = {"x": 0, "y": 64, "z": 0}
    w("entities.json", d)


ZOMBI = {"id": 5, "kind": "hostile", "type": "minecraft:zombie", "name": "Zombie", "dist": 7.0, "targets_player": True}


def prompt(**kw):
    return ns["generar_prompt_maestro"]("visión", "terreno", "feedback", "", "", "tech", "waypoints", **kw)


config()
sin = prompt()
r.check("sin 'entorno' el prompt es el de siempre (sin bloque de situación)", "SITUACIÓN ACTUAL" not in sin and prompt(entorno="") == sin)
con = prompt(entorno="- Jugador a 5 bloques, vida 18/20.")
i_sit, i_mem, i_reglas = con.find("SITUACIÓN ACTUAL"), con.find("MEMORIA Y EXPERIENCIA"), con.find("REGLAS ESTRICTAS")
r.check("con entorno: el bloque aparece, con sus datos, antes de la memoria y de las reglas", 0 < i_sit < i_mem < i_reglas and "- Jugador a 5 bloques, vida 18/20." in con)
BLOQUE = "\n=== SITUACIÓN ACTUAL (sensores en vivo; úsala solo si viene al caso) ===\n- Jugador a 5 bloques, vida 18/20.\n" + "=" * 43
r.check("y con entorno el resto del prompt no cambia: quitando el bloque queda EXACTAMENTE el prompt de antes", con.replace(BLOQUE, "", 1) == sin and BLOQUE in con)
config(ollama_num_ctx=4096)
enorme = prompt(entorno="\n".join(f"- hecho número {i} con bastante texto de relleno para gastar sitio" for i in range(400)))
r.check(f"un resumen enorme pasa por el presupuesto y el prompt sigue cabiendo ({len(enorme)} <= {ns['presupuesto_prompt_chars']()})", len(enorme) <= ns["presupuesto_prompt_chars"]())
config()

sensores(hostiles=[ZOMBI])
t = ns["texto_entorno_para_prompt"]()
r.check("lee estado, gps y entidades: jugador, hostil que va a por él y la hora del juego: " + t.replace("\n", " | "),
        "Jugador a 5 bloques, vida 18/20." in t and "Zombie a 7 bloques" in t and "1 va a por el jugador" in t and "Es de noche (21:00)" in t)
config(entorno_en_prompt=False)
r.check("entorno_en_prompt=false: vacío", ns["texto_entorno_para_prompt"]() == "")
config(sensor_entidades=False)
t2 = ns["texto_entorno_para_prompt"]()
r.check("con el sensor de entidades apagado NO se afirma que esté despejado ni se cita ningún hostil, pero sí el resto: " + t2.replace("\n", " | "),
        "hostiles" not in t2.lower() and "Zombie" not in t2 and "Jugador a 5 bloques" in t2)
config()
sensores(vivo=False)
r.check("sensor de entidades caído (sin posición del bot): no dice 'Sin hostiles cerca'", "Sin hostiles" not in ns["texto_entorno_para_prompt"]())
sensores()
r.check("sensor vivo y sin hostiles: 'Sin hostiles cerca.'", "Sin hostiles cerca." in ns["texto_entorno_para_prompt"]())
for n in ("nox_status.json", "gps.json", "entities.json"):
    quitar(n)
r.check("sin ningún archivo de sensores: '' (el prompt queda como antes) y no lanza", ns["texto_entorno_para_prompt"]() == "")
io.open(os.path.join(tmp, "gps.json"), "w", encoding="utf-8").write("{roto")
r.check("con gps.json a medio escribir: '' y no lanza", ns["texto_entorno_para_prompt"]() == "")
quitar("gps.json")
lee_original = ns["leer_estado_cobalt"]


def _roto():
    raise RuntimeError("sensor roto")


ns["leer_estado_cobalt"] = _roto
r.check("si la lectura de un sensor lanza, el bloque del prompt queda vacío (el chat sigue funcionando)", ns["texto_entorno_para_prompt"]() == "")
ns["leer_estado_cobalt"] = lee_original

sensores(hostiles=[ZOMBI])
o = ns["aplicar_cortocircuito"]("situación", "Steve")
r.check("'situación' -> orden de solo chat con el informe real: " + repr(o), o and len(o) == 1 and o[0]["action"] == "ninguna" and o[0]["target"] == "Steve"
        and o[0]["chat_message"].startswith("Jugador a 5 bloques, vida 18/20. Hostiles cerca: 1 (el más cercano, Zombie a 7 bloques): 1 va a por el jugador.") and "Es de noche" in o[0]["chat_message"])
r.check("'Cobalt, ¿cómo estamos?' también", (ns["aplicar_cortocircuito"]("Cobalt, ¿cómo estamos?", "Steve") or [{}])[0].get("chat_message", "").startswith("Jugador a 5 bloques"))
o = ns["aplicar_cortocircuito"]("explícame la situación económica de Mekanism", "Steve")
r.check("una pregunta larga sobre otra 'situación' NO es un informe (va al modelo)", not o or "Jugador a" not in (o[0].get("chat_message") or ""))
config(informe_situacion=False)
o = ns["aplicar_cortocircuito"]("situación", "Steve")
r.check("informe_situacion=false: el atajo no responde", not o or "Jugador a" not in (o[0].get("chat_message") or ""))
config()
for n in ("nox_status.json", "gps.json", "entities.json"):
    quitar(n)
o = ns["aplicar_cortocircuito"]("informe", "Steve")
r.check("sin sensores el informe lo admite con una frase del banco (no inventa): " + repr(o), o and o[0]["chat_message"] in nv.BANCO["sin_informe"])

ns["leer_estado_cobalt"] = _roto
o = ns["aplicar_cortocircuito"]("situación", "Steve")
r.check("si la lectura de un sensor lanza, el informe lo admite con una frase del banco (no rompe el chat): " + repr(o), o and o[0]["chat_message"] in nv.BANCO["sin_informe"])
ns["leer_estado_cobalt"] = lee_original

sensores(hostiles=[ZOMBI])
enviados, llamadas = [], []
ns["escribir_comando"] = lambda ordenes: enviados.extend(x.get("chat_message") for x in ordenes)
ns["consultar_ollama"] = lambda *a, **k: llamadas.append(a) or "[]"
ns["consultar_gemini_o_fallback"] = lambda *a, **k: llamadas.append(a) or "[]"
ns["procesar_mensaje_async"]("Steve", "situación")
r.check("procesar_mensaje_async('situación'): responde por el chat con el informe y no llama a ningún modelo: " + repr(enviados) + " " + str(len(llamadas)),
        len(enviados) == 1 and enviados[0].startswith("Jugador a 5 bloques") and not llamadas)

prompts = []
ns["consultar_ollama"] = lambda modelo, p, *a, **k: prompts.append(p) or '[{"action":"ninguna","chat_message":"Vale.","movement_mode":"walk"}]'
ns["procesar_mensaje_async"]("Steve", "cuéntame algo de este sitio")
maestros = [x for x in prompts if "REGLAS ESTRICTAS" in x]
r.check("el chat normal manda al modelo un prompt maestro CON la situación actual: " + str(len(maestros)), len(maestros) == 1 and "SITUACIÓN ACTUAL" in maestros[0] and "Zombie a 7 bloques" in maestros[0])
prompts.clear()
config(entorno_en_prompt=False)
ns["procesar_mensaje_async"]("Steve", "cuéntame algo de este sitio")
maestros = [x for x in prompts if "REGLAS ESTRICTAS" in x]
r.check("con entorno_en_prompt=false el prompt maestro del chat no lleva la situación", len(maestros) == 1 and "SITUACIÓN ACTUAL" not in maestros[0])

r.terminar()
