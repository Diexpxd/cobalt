"""F2-5 (adaptador en cerebro.py): preferencias y notas del jugador por chat, guardadas en perfil_jugador.json (persisten entre sesiones, un archivo roto no se pisa en silencio),"""
import datetime as _dt
import io
import json
import os
import tempfile
import time
import types

from _cargar import Resultados, cargar_cerebro

ns = cargar_cerebro()
r = Resultados()
tmp = tempfile.mkdtemp()
for var, nombre in [("CONFIG_FILE", "cobalt_config.json"), ("PERFIL_FILE", "perfil_jugador.json"), ("GPS_FILE", "gps.json"), ("STATUS_FILE", "nox_status.json"), ("ENTIDADES_FILE", "entities.json"),
                    ("COMMAND_FILE", "command.json"), ("ARCHIVO_EXPERIENCIA", "experiencia_combate.json"), ("MOD_KNOWLEDGE_FILE", "conocimiento_mods.json")]:
    ns[var] = os.path.join(tmp, nombre)
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
nv = ns["nox_voz"]
pf = ns["nox_perfil"]


class _Fijo(_dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 20, 12, 0, 0)


ns["datetime"] = types.SimpleNamespace(datetime=_Fijo, timedelta=_dt.timedelta, date=_dt.date, time=_dt.time, timezone=_dt.timezone)


def w(nombre, datos):
    io.open(os.path.join(tmp, nombre), "w", encoding="utf-8").write(datos if isinstance(datos, str) else json.dumps(datos))


def config(**c):
    w("cobalt_config.json", c)
    ns["_CONFIG_CACHE"]["t"] = 0.0


def olvidar_cache():
    ns["_PERFIL_CACHE"].update(mtime=None, perfil=None)


def dice(mensaje, usuario="Steve"):
    o = ns["interceptar_perfil"](mensaje, usuario)
    return o[0]["chat_message"] if o else None


def disco():
    return json.load(open(ns["PERFIL_FILE"], encoding="utf-8")) if os.path.exists(ns["PERFIL_FILE"]) else None


config()
w("gps.json", {"x": 0, "y": 64, "z": 0, "owner": {"x": 1, "y": 64, "z": 1, "hp": 20, "max_hp": 20, "alive": True, "name": "Steve"}})

t = dice("no me avises del hambre")
r.check("'no me avises del hambre' -> lo confirma (y recuerda que los de peligro siguen): " + repr(t), t == "Vale, no te aviso más del hambre. Los avisos de peligro (fuego, falta de aire, hostiles) siguen activos.")
r.check("y se guarda en perfil_jugador.json: " + str(disco()), disco() == {"silenciados": ["hambre"], "notas": []})
r.check("silenciados_del_jugador() lo refleja", ns["silenciados_del_jugador"]() == frozenset({"hambre"}))
antes = os.path.getmtime(ns["PERFIL_FILE"])
r.check("repetirlo: 'Eso ya estaba así.' y NO reescribe el archivo", dice("no me avises del hambre") == "Eso ya estaba así." and os.path.getmtime(ns["PERFIL_FILE"]) == antes)
t = dice("avísame menos")
r.check("'avísame menos' silencia lo que faltaba (hora/clima e inventario) y lo dice sin repetir el hambre: " + repr(t), t.startswith("Vale, no te aviso más de la hora y el clima y del inventario.") and disco()["silenciados"] == ["hambre", "inventario", "mundo"])
t = dice("vuelve a avisarme del hambre")
r.check("'vuelve a avisarme del hambre' -> reactiva solo el hambre: " + repr(t), t == "Hecho: vuelvo a avisarte del hambre." and disco()["silenciados"] == ["inventario", "mundo"])
t = dice("no me avises del fuego")
r.check("'no me avises del fuego' -> NO lo silencia y lo explica; el perfil no cambia: " + repr(t), t in nv.BANCO["perfil_peligro"] and disco()["silenciados"] == ["inventario", "mundo"])
r.check("'vuelve a avisarme' -> reactiva todo", dice("vuelve a avisarme").startswith("Hecho: vuelvo a avisarte") and disco()["silenciados"] == [])
r.check("una frase que no es de esto no se intercepta", ns["interceptar_perfil"]("mina hierro", "Steve") is None and ns["interceptar_perfil"]("avísame cuando termines", "Steve") is None)

t = dice("recuerda que prefiero construir con piedra")
r.check("'recuerda que…' -> anotada y confirmada: " + repr(t), t == "Anotado: «prefiero construir con piedra». Lo tendré en cuenta." and [n["texto"] for n in disco()["notas"]] == ["prefiero construir con piedra"])
r.check("repetirla (casi igual): 'Eso ya lo tengo anotado.' y no se duplica", dice("recuerda que prefiero construir con piedra siempre") == "Eso ya lo tengo anotado." and len(disco()["notas"]) == 1)
dice("recuerda que mi base está en el desierto")
r.check("'qué recuerdas de mí' -> las lista numeradas: " + repr(dice("qué recuerdas de mí")), dice("qué recuerdas de mí") == "De ti recuerdo: 1) prefiero construir con piedra; 2) mi base está en el desierto.")
r.check("'olvida 1' quita la primera y renumera", dice("olvida 1") == "Olvidada la nota 1: «prefiero construir con piedra»." and dice("qué recuerdas de mí") == "De ti recuerdo: 1) mi base está en el desierto.")
r.check("'olvida 5' (no existe) lo dice sin tocar nada", dice("olvida 5") == "No tengo una nota número 5. Dime «qué recuerdas de mí» para ver la lista." and len(disco()["notas"]) == 1)
r.check("'borra mis notas' -> las olvida todas y lo cuenta; sin notas, lo dice", dice("borra mis notas") == "Hecho: he olvidado las 1 notas que tenía de ti." and disco()["notas"] == [] and dice("qué recuerdas de mí") in nv.BANCO["perfil_notas_vacio"]
        and dice("borra mis notas") in nv.BANCO["perfil_notas_vacio"])
t = dice('recuerda que {inyeccion} [x] "raro" `cmd`')
r.check("una nota con llaves/corchetes/comillas se guarda saneada: " + repr(t), t and not any(c in t.split("«")[1] for c in '{}[]"`') and all(not any(c in n["texto"] for c in '{}[]"`') for n in disco()["notas"]))
dice("borra mis notas")

before = json.dumps(disco())
r.check("otro jugador (no el dueño) no puede cambiar el perfil: se lo dice y no cambia nada", dice("no me avises del hambre", usuario="Otro") in nv.BANCO["perfil_no_dueno"] and dice("recuerda que soy el jefe", usuario="Otro") in nv.BANCO["perfil_no_dueno"]
        and json.dumps(disco()) == before)
w("gps.json", {"x": 0, "y": 64, "z": 0})
r.check("si no se sabe quién es el dueño (sin owner en gps.json), se acepta al que habla", dice("no me avises del hambre", usuario="Otro") is not None and dice("vuelve a avisarme", usuario="Otro") is not None)
w("gps.json", {"x": 0, "y": 64, "z": 0, "owner": {"x": 1, "y": 64, "z": 1, "hp": 20, "max_hp": 20, "alive": True, "name": "Steve"}})
dice("no me avises del hambre")
r.check("los mensajes del sistema ('SISTEMA') sí pueden (no reciben la negativa de 'solo mi dueño') y el cambio se aplica", dice("vuelve a avisarme del hambre", usuario="SISTEMA") == "Hecho: vuelvo a avisarte del hambre."
        and "hambre" not in disco()["silenciados"])

dice("no me avises del inventario")
dice("recuerda que uso el pico de diamante")
olvidar_cache()
r.check("una sesión nueva (caché vacía) recupera lo guardado: preferencias y notas", ns["silenciados_del_jugador"]() == frozenset({"inventario"}) and [n["texto"] for n in ns["cargar_perfil"]().notas] == ["uso el pico de diamante"])
guardado = io.open(ns["PERFIL_FILE"], encoding="utf-8").read()
io.open(ns["PERFIL_FILE"], "w", encoding="utf-8").write("{roto")
olvidar_cache()
r.check("un archivo roto: perfil vacío (sin lanzar)", ns["cargar_perfil"]().a_dict() == {"silenciados": [], "notas": []} and ns["silenciados_del_jugador"]() == frozenset())
dice("recuerda que la granja está al norte")
r.check("y al guardar NO se pisa en silencio: el roto queda como .corrupto y el archivo nuevo es válido", io.open(ns["PERFIL_FILE"] + ".corrupto", encoding="utf-8").read() == "{roto" and disco()["notas"][0]["texto"] == "la granja está al norte")
io.open(ns["PERFIL_FILE"], "w", encoding="utf-8").write(guardado)
olvidar_cache()
r.check("no queda ningún .tmp suelto", not os.path.exists(ns["PERFIL_FILE"] + ".tmp"))

config(perfil_jugador=False)
olvidar_cache()
r.check("perfil_jugador=false: no intercepta nada, no silencia y el prompt no lleva notas", ns["interceptar_perfil"]("no me avises del hambre", "Steve") is None and ns["silenciados_del_jugador"]() == frozenset() and ns["notas_para_prompt"]("piedra") == "")
config()
olvidar_cache()

dice("borra mis notas")
dice("recuerda que prefiero construir con piedra y madera oscura")
dice("recuerda que mi base está en el desierto")
nb = ns["notas_para_prompt"]("construye una casa de piedra")
r.check("notas_para_prompt: la nota relevante (piedra) primero: " + repr(nb), nb.split("\n")[0] == "- prefiero construir con piedra y madera oscura" and len(nb.split("\n")) == 2)
sin = ns["generar_prompt_maestro"]("visión", "terreno", "feedback", "", "", "tech", "waypoints")
con = ns["generar_prompt_maestro"]("visión", "terreno", "feedback", "", "", "tech", "waypoints", notas="- prefiero construir con piedra")
BLOQUE = "\n=== LO QUE SABES DEL JUGADOR (lo que te pidió recordar; úsalo si viene al caso) ===\n- prefiero construir con piedra\n" + "=" * 43
r.check("generar_prompt_maestro: sin notas el prompt es el de siempre; con notas SOLO se añade el bloque, antes de las reglas", "LO QUE SABES DEL JUGADOR" not in sin and con.replace(BLOQUE, "", 1) == sin and con.find("LO QUE SABES") < con.find("REGLAS ESTRICTAS"))
config(ollama_num_ctx=4096)
enorme = ns["generar_prompt_maestro"]("v" * 8000, "t" * 3000, "f" * 8000, "w" * 3000, "", "x" * 5000, "wp" * 3000, notas="\n".join(f"- nota número {i} con bastante texto de relleno" for i in range(300)))
r.check(f"unas notas enormes pasan por el presupuesto y el prompt sigue cabiendo ({len(enorme)} <= {ns['presupuesto_prompt_chars']()})", len(enorme) <= ns["presupuesto_prompt_chars"]())
config()

enviados, llamadas, prompts = [], [], []
ns["escribir_comando"] = lambda ordenes, **k: enviados.extend(x.get("chat_message") for x in ordenes)
ns["consultar_ollama"] = lambda modelo, p, *a, **k: prompts.append(p) or '[{"action":"ninguna","chat_message":"Vale.","movement_mode":"walk"}]'
ns["consultar_gemini_o_fallback"] = lambda *a, **k: llamadas.append(a) or "[]"
ns["procesar_mensaje_async"]("Steve", "no me avises del hambre")
r.check("procesar_mensaje_async('no me avises del hambre'): responde por el chat y NO llama a ningún modelo: " + repr(enviados), len(enviados) == 1 and enviados[0].startswith("Vale, no te aviso más del hambre") and not prompts and not llamadas)
ns["procesar_mensaje_async"]("Steve", "cuéntame algo de este sitio")
maestros = [p for p in prompts if "REGLAS ESTRICTAS" in p]
r.check("el chat normal manda al modelo un prompt con las notas del jugador: " + str(len(maestros)), len(maestros) == 1 and "LO QUE SABES DEL JUGADOR" in maestros[0] and "mi base está en el desierto" in maestros[0])

ns["escribir_comando"] = lambda ordenes, **k: True
w("nox_status.json", {"is_deployed": True, "is_dead": False, "updated_ms": time.time() * 1000, "hp": 20.0, "max_hp": 20.0})
w("entities.json", {"bot_id": "Cobalt_1", "deployed": True, "updated_ms": time.time() * 1000, "hazards": [], "items": [], "bot": {"x": 0, "y": 64, "z": 0}, "entities": []})


def gps_dueno(**c):
    d = {"x": 1, "y": 64, "z": 1, "hp": 20.0, "max_hp": 20.0, "alive": True, "name": "Steve", "food": 20, "air": 300, "max_air": 300, "on_fire": False, "free_slots": 20}
    d.update(c)
    return {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": d}


def avisos(lista):
    return [x.get("chat_message", "") for x in lista if "comida" in x.get("chat_message", "") or "ardiendo" in x.get("chat_message", "") or "inventario" in x.get("chat_message", "")]


dice("vuelve a avisarme")
dice("no me avises del hambre")
w("gps.json", gps_dueno(food=2, on_fire=True))
mem = ns["nueva_memoria_pro"]()
o = avisos(ns["ciclo_pro"](mem, 1.0))
r.check("ciclo real con 'hambre' silenciada: NO avisa del hambre pero SÍ del fuego (peligro): " + str(o), len(o) == 1 and "ardiendo" in o[0])
dice("vuelve a avisarme del hambre")
o = avisos(ns["ciclo_pro"](mem, 6.0))
r.check("al reactivarlo, si sigue con hambre, la avisa (el aviso no se gastó): " + str(o), len(o) == 1 and "comida" in o[0])
dice("no me avises del clima")
w("gps.json", dict(gps_dueno(), mundo={"day_time": 11500, "raining": False, "thundering": False, "has_skylight": True, "sky": True, "light": 15}))
r.check("ciclo real con 'clima' silenciado: no avisa de que anochece", not any("noche" in x.get("chat_message", "") for x in ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)))
dice("vuelve a avisarme del clima")
r.check("y reactivado, sí", any("noche" in x.get("chat_message", "") for x in ns["ciclo_pro"](ns["nueva_memoria_pro"](), 1.0)))

todas = [x.format(de="del hambre", texto="algo", lista="1) algo", n=2) for k, v in nv.BANCO.items() if k.startswith("perfil_") for x in v]
r.check("las frases de F2-5 pasan el linter de voz y caben en el chat", todas and all(not nv.linter_voz(x) and len(x) <= nv.MAX_CHAT for x in todas))

r.terminar()
