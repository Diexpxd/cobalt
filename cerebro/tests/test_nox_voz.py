"""H1: la voz de Cobalt."""
import random
import os
import sys

from _cargar import Resultados, cargar_cerebro
import _frases_del_codigo as fc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_voz as v  # noqa: E402

r = Resultados()

buenas = ["Todo en orden por aquí. Dime qué necesitas.", "Cuidado: hay un creeper a punto de explotar a tu lado.", "Jefe Wither a la vista. Mantengo distancia y vuelo.",
          "Vamos a por el jefe. Yo voy por el aire.", "Derrotamos al jefe!", "Plano 'casa' cargado. Empiezo a construir en 'base'.", "Me emboscan al norte. Vida al 30%.",
          "Uso TNT solo si me lo pides.", "¿Me lo repites?", "Voy hacia ti."]
malas = {"¡Entendido, jefe! Plano cargado.": "trato servil", "Hola, jefe. Todo listo.": "trato servil", "¡Atención jefe! No hay hacha.": "trato servil", "A tus órdenes.": "fórmula servil",
         "Listos para lo que mandes.": "fórmula servil", "¡Perfecto! Hecho.": "confirmación exagerada", "¡Genial! ¡Qué bien! ¡Vamos!": "varias exclamaciones",
         "Hecho!!": "varias exclamaciones", "Voy " + chr(0x1F680): "emojis", "PELIGRO cerca": "mayúsculas", "Sí, señor.": "trato servil", "Como desees.": "fórmula servil",
         "x" * 300: "demasiado largo"}
r.check("el linter deja pasar la voz buena (incluido 'el jefe' enemigo y las siglas): " + str([t for t in buenas if v.linter_voz(t)]), not any(v.linter_voz(t) for t in buenas))
r.check("el linter caza cada tipo de frase que NO es de Cobalt: " + str([t[:25] for t in malas if not v.linter_voz(t)]), all(v.linter_voz(t) for t in malas))
r.check("distingue las reglas (trato servil, fórmula, confirmación, exclamaciones, emojis, mayúsculas, largo)",
        "trato servil" in v.linter_voz("¡Entendido, jefe!")[0] and any("exagerada" in p for p in v.linter_voz("¡Perfecto! Hecho.")) and any("mayúsculas" in p for p in v.linter_voz("PELIGRO cerca"))
        and any("largo" in p for p in v.linter_voz("x" * 300)))
r.check("los marcadores {x} de una plantilla no cuentan como texto", v.linter_voz("Plano '{plano}' cargado en '{lugar}'.") == [])
r.check("el linter tolera None y vacío", v.linter_voz(None) == [] and v.linter_voz("") == [])

r.check("TODAS las frases del banco pasan el linter (sin trato servil, sin gritos, sin emojis): " + str([(k, x) for k, vs in v.BANCO.items() for x in vs if v.linter_voz(x)]),
        not any(v.linter_voz(x) for vs in v.BANCO.values() for x in vs))
r.check("todas las claves tienen al menos una variante", all(len(vs) >= 1 for vs in v.BANCO.values()))
r.check("la persona cabe en el presupuesto del prompt (menos de 700 caracteres) y recoge el carácter: compañero, apoyo táctico, sin servilismo ni exageración",
        len(v.PERSONA) < 700 and all(x in v.PERSONA for x in ("compañero de aventuras", "apoyo táctico", "sin servilismo", "sin exageración")))
voz = v.Voz(random.Random(1))
vistas = [voz.frase("saludo") for _ in range(12)]
r.check("nunca repite la misma variante dos veces seguidas (suena menos a robot)", all(a != b for a, b in zip(vistas, vistas[1:])) and len(set(vistas)) == 3)
r.check("una frase con una sola variante se repite sin error", [voz.frase("sin_pico") for _ in range(3)] == [v.BANCO["sin_pico"][0]] * 3)
r.check("rellena los datos: plano y lugar", v.Voz(random.Random(0)).frase("plano_cargado", plano="casa", lugar="base") == "Plano 'casa' cargado. Empiezo a construir en 'base'.")
r.check("un dato que falta NO rompe: pone '?'", v.Voz().frase("plano_cargado", plano="x") == "Plano 'x' cargado. Empiezo a construir en '?'.")
try:
    v.frase("no_existe")
    r.check("una clave desconocida lanza KeyError", False)
except KeyError:
    r.check("una clave desconocida lanza KeyError", True)
r.check("la emboscada conserva el formato 'Vida al 30%.' que esperan los tests de protección", v.Voz().frase("emboscada", donde=" al norte", pct=30, quien=" Zombi.") == "Me emboscan al norte. Vida al 30%. Zombi.")

casos = [("¡Entendido, jefe! Voy a minar hierro.", "Voy a minar hierro."), ("Claro, jefe, ahora mismo.", "Claro, ahora mismo."), ("¡Perfecto! Me pongo con la tala.", "Me pongo con la tala."),
         ("Hecho " + chr(0x1F44D) + " ya está.", "Hecho ya está."), ("¡Genial! ¡Qué bien! ¡Vamos!", "Qué bien. Vamos."), ("PELIGRO cerca del creeper", "Peligro cerca del creeper"),
         ("Uso TNT si hace falta", "Uso TNT si hace falta"), ("hola, todo bien", "Hola, todo bien"), ("Voy hacia ti.", "Voy hacia ti."), ("¡Cuidado! Ese zombi viene por la izquierda.", "¡Cuidado! Ese zombi viene por la izquierda.")]
for entrada, esperado in casos:
    r.check(f"suavizar({entrada!r}) -> {esperado!r} (obtuvo {v.suavizar(entrada)!r})", v.suavizar(entrada) == esperado)
r.check("suavizar es IDEMPOTENTE (aplicarlo dos veces = una vez) en todos los casos y en el recorte largo",
        all(v.suavizar(v.suavizar(e)) == v.suavizar(e) for e, _ in casos) and v.suavizar(v.suavizar("palabra " * 80)) == v.suavizar("palabra " * 80))
r.check("lo suavizado pasa el linter (salvo que fuera largo)", all(not v.linter_voz(v.suavizar(e)) for e, _ in casos))
r.check("una exclamación normal se respeta ('¡Cuidado!')", "¡Cuidado!" in v.suavizar("¡Cuidado! Ese zombi viene."))
r.check("lo largo se recorta a 240 en una frase completa o con '...'", len(v.suavizar("Esta es una frase larga. " * 30)) <= 240 and v.suavizar("Esta es una frase larga. " * 30).endswith("."))
r.check("si solo había una confirmación servil o un emoji, queda un 'Entendido.' tranquilo (nunca un mensaje vacío)", v.suavizar("¡Entendido, jefe!") == "Entendido." and v.suavizar(chr(0x1F44D)) == "Entendido.")
r.check("tolera None, vacío y tipos raros sin lanzar", v.suavizar(None) is None and v.suavizar("") == "" and v.suavizar(5) == 5)

todas = fc.todas()
r.check(f"el escáner encuentra las frases del jugador en el código ({len(todas)}; debe haber más de 40)", len(todas) > 40)
problemas = sorted({(a, ln, s[:70], tuple(v.linter_voz(s))) for a, ln, s in todas if v.linter_voz(s)})
r.check("NINGUNA frase del código para el jugador tiene trato servil, fórmulas serviles, confirmaciones exageradas, gritos ni emojis: " + str(problemas[:4]), not problemas)

ns = cargar_cerebro()
prompt = ns["generar_prompt_maestro"]("visión", "terreno", "feedback", "", "", "tech", "waypoints")
r.check("el prompt del modelo local abre con la personalidad de Cobalt (aliado natural, sin 'jefe' ni exclamaciones)", prompt.startswith(v.PERSONA) and "sin servilismo" in prompt)
r.check("y conserva sus capacidades y las reglas de JSON (nada roto)", "vuelo, natación y combate" in prompt and "ARRAY JSON PURO" in prompt)
r.check("las frases fijas del adaptador salen del banco (sin la vieja 'jefe')", "jefe" not in ns["frase"]("saludo").lower() and ns["frase"]("saludo") in v.BANCO["saludo"])

import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

tmp = tempfile.mkdtemp()
ns["CONFIG_FILE"] = os.path.join(tmp, "cobalt_config.json")
ns["STATUS_FILE"] = os.path.join(tmp, "nox_status.json")
io.open(ns["STATUS_FILE"], "w", encoding="utf-8").write(json.dumps({"is_deployed": True, "is_dead": False, "updated_ms": time.time() * 1000}))
ns["registrar_mensaje_disco_python"] = lambda *a, **k: None
enviados = []
ns["escribir_comando"] = lambda ordenes: enviados.extend(o.get("chat_message") for o in ordenes)
respuesta_modelo = json.dumps([{"action": "ninguna", "chat_message": "¡Entendido, jefe! " + chr(0x1F680) + " Voy a minar el hierro, PRONTO"}])
ns["consultar_ollama"] = lambda modelo, prompt: "NO" if "requiere internet" in prompt else respuesta_modelo


def configurar(**c):
    io.open(ns["CONFIG_FILE"], "w", encoding="utf-8").write(json.dumps(c))
    ns["_CONFIG_CACHE"]["t"] = 0.0


configurar()
ns["procesar_mensaje_async"]("Steve", "mina hierro por favor")
r.check("voz_natural (por defecto): 'Entendido, jefe' + emoji + gritos del modelo llegan como 'Voy a minar el hierro, pronto': " + repr(enviados), enviados == ["Voy a minar el hierro, pronto"])
enviados.clear()
configurar(voz_natural=False)
ns["procesar_mensaje_async"]("Steve", "mina hierro por favor")
r.check("voz_natural=false: el texto del modelo pasa TAL CUAL (interruptor para volver al comportamiento anterior)", len(enviados) == 1 and "jefe" in enviados[0] and "PRONTO" in enviados[0])
enviados.clear()
configurar()
ns["procesar_mensaje_async"]("Steve", "hola cobalt, ¿cómo estás?")
r.check("el saludo reflejo sale del banco de voz (sin 'jefe' ni 'listos para lo que mandes'): " + repr(enviados), len(enviados) == 1 and enviados[0] in v.BANCO["saludo"])

r.terminar()
