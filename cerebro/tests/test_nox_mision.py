"""Bloque I (Python): interpretación de misiones con plazo, su seguimiento hasta la base y la purga de waypoints automáticos."""
import os
import sys

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_mision as mi  # noqa: E402

r = Resultados()
im = mi.interpretar_mision

r.check("misión: 'Consigue 64 de hierro o regresa en 10 minutos'", im("Consigue 64 de hierro o regresa en 10 minutos") == {"cantidad": 64, "material": "iron_ore", "minutos": 10})
r.check("misión: 'mina 8 diamantes en 5 min'", im("mina 8 diamantes en 5 min") == {"cantidad": 8, "material": "diamond_ore", "minutos": 5})
r.check("misión: 'Cobalt, tráeme 32 de carbón y vuelve a la base en 15 minutos'", im("Cobalt, tráeme 32 de carbón y vuelve a la base en 15 minutos") == {"cantidad": 32, "material": "coal_ore", "minutos": 15})
r.check("misión: orden inversa 'en 20 minutos consigue 16 de oro y regresa'", im("en 20 minutos consigue 16 de oro y regresa") == {"cantidad": 16, "material": "gold_ore", "minutos": 20})
r.check("misión: id de Minecraft escrito tal cual", im("mina 10 de deepslate_iron_ore en 7 minutos") == {"cantidad": 10, "material": "deepslate_iron_ore", "minutos": 7})
r.check("misión: 'lapis lázuli' con acento y 'cualquiera'", im("consigue 20 de lapis lázuli en 5 minutos")["material"] == "lapis_ore" and im("mina 30 de cualquiera en 5 minutos")["material"] == "cualquiera")
r.check("misión: etiqueta universal: 'forge ores iron' -> forge:ores/iron y 'c ores' -> c:ores",
        im("consigue 20 de forge ores iron en 5 minutos")["material"] == "forge:ores/iron" and im("mina 10 de c ores en 5 minutos")["material"] == "c:ores")
r.check("misión: la cantidad se limita a 64 y el plazo a 60 min", im("consigue 500 de hierro en 999 minutos") == {"cantidad": 64, "material": "iron_ore", "minutos": 60})
r.check("misión: sin plazo NO es una misión (lo procesa el LLM normal)", im("mina 10 de hierro") is None and im("consigue 64 de hierro") is None)
r.check("misión: material desconocido -> None (no se inventa un id)", im("consigue 10 de unobtainium en 5 minutos") is None)
r.check("misión: frases normales -> None", all(im(x) is None for x in ("hola cobalt", "construye una casa en 5 minutos", "", None, "en 5 minutos nos vemos")))
r.check("misión: cantidad 0 o plazo 0 -> None", im("consigue 0 de hierro en 5 minutos") is None and im("consigue 5 de hierro en 0 minutos") is None)

WP = {"base": {"x": 100, "y": 64, "z": -50}}
mis = {"cantidad": 64, "material": "iron_ore", "minutos": 10}
m = mi.MisionTemporal()
o = m.ordenes_de_inicio(mis)
r.check("misión: la orden de inicio es un 'mine' con material, cantidad y plazo en minutos", len(o) == 1 and o[0]["action"] == "mine" and o[0]["material"] == "iron_ore"
        and o[0]["amount"] == 64 and o[0]["minutes"] == 10 and "iron" in o[0]["chat_message"])
m.iniciar(mis, 1000.0)
r.check("misión: sin feedback y dentro de plazo no hace nada", m.actualizar({}, {}, None, WP, 1100.0) == [])
fb_viejo = {"status": "success", "mined": 64, "mtime": 500.0}
r.check("misión: un feedback ANTERIOR al inicio se ignora", m.actualizar({}, {}, fb_viejo, WP, 1200.0) == [])
fb = {"status": "success", "mined": 64, "wanted": 64, "mtime": 1500.0}
o = m.actualizar({}, {"x": 300, "y": 20, "z": 300}, fb, WP, 1500.0)
r.check("misión cumplida: avisa el resultado y ordena volver a la base (go_to fly)", len(o) == 1 and o[0]["action"] == "go_to" and (o[0]["x"], o[0]["y"], o[0]["z"]) == (100, 64, -50)
        and "cumplida" in o[0]["chat_message"] and "64/64" in o[0]["chat_message"] and o[0]["movement_mode"] == "fly")
r.check("misión: en el regreso no repite antes de 10 s", m.actualizar({}, {"x": 250, "y": 30, "z": 200}, None, WP, 1505.0) == [])
o = m.actualizar({}, {"x": 250, "y": 30, "z": 200}, None, WP, 1512.0)
r.check("misión: pasados 10 s reitera el go_to (sin chat)", len(o) == 1 and o[0]["action"] == "go_to" and "chat_message" not in o[0])
o = m.actualizar({}, {"x": 102, "y": 64, "z": -48}, None, WP, 1530.0)
r.check("misión: al llegar a 6 bloques de la base termina y avisa", len(o) == 1 and "Llegué a la base" in o[0]["chat_message"] and m.activa is None)

m2 = mi.MisionTemporal()
m2.iniciar(mis, 0.0)
o = m2.actualizar({}, {}, {"status": "partial", "mined": 20, "detalle": "tiempo agotado (10 min)", "mtime": 700.0}, WP, 700.0)
r.check("misión incompleta: dice cuánto logró y por qué, y vuelve", "sin completar" in o[0]["chat_message"] and "20/64" in o[0]["chat_message"] and "tiempo agotado" in o[0]["chat_message"] and o[-1]["action"] == "go_to")
m3 = mi.MisionTemporal()
m3.iniciar(mis, 0.0)
r.check("misión: pasado el plazo + 90 s de gracia sin informe de Java -> flush, stop y vuelve", m3.actualizar({}, {}, None, WP, 600.0 + 89.0) == []
        and [x["action"] for x in m3.actualizar({}, {}, None, WP, 600.0 + 91.0)] == ["flush", "stop", "go_to"])
m4 = mi.MisionTemporal()
m4.iniciar(mis, 0.0)
o = m4.actualizar({}, {}, {"status": "success", "mined": 64, "mtime": 10.0}, {}, 10.0)
r.check("misión sin waypoint 'base': lo dice, se queda y termina (no inventa una base)", len(o) == 1 and o[0]["action"] == "ninguna" and "waypoint 'base'" in o[0]["chat_message"] and m4.activa is None)
m5 = mi.MisionTemporal()
m5.iniciar(mis, 0.0)
m5.actualizar({}, {}, {"status": "success", "mined": 64, "mtime": 10.0}, WP, 10.0)
o = m5.actualizar({}, {"x": 900, "y": 10, "z": 900}, None, WP, 10.0 + 250.0)
r.check("misión: si en 4 minutos no llega a la base, se rinde con aviso", len(o) == 1 and "No logré llegar" in o[0]["chat_message"] and m5.activa is None)
r.check("misión: sin misión activa no hace nada", mi.MisionTemporal().actualizar({}, {}, fb, WP, 0.0) == [])

AHORA = 1_800_000_000_000
DIA = 24 * 3600 * 1000
wps = {"base": {"x": 0, "y": 64, "z": 0}, "mina": {"x": 1, "y": 1, "z": 1}, "zona_industrial": {"x": 2, "y": 2, "z": 2}}
for i in range(6):  # 6 muertes, de hace 10 días a hace 1 hora
    wps[f"muerte_nox_{AHORA - (10 - i * 2) * DIA + (AHORA % 7)}"] = {"x": i, "y": 0, "z": 0}
wps[f"muerte_nox_{AHORA - 3600 * 1000}"] = {"x": 9, "y": 0, "z": 0}
wps["inventario_nox_abc"] = {"x": 0, "y": 0, "z": 0}
borrar = mi.waypoints_a_purgar(wps, AHORA)
mias = {"base", "mina", "zona_industrial"}
r.check("purga: NUNCA toca los waypoints del jugador ni los de formato desconocido", not (set(borrar) & mias) and "inventario_nox_abc" not in borrar)
muertes = sorted((n for n in wps if n.startswith("muerte_nox_")), key=lambda n: int(n.split("_")[-1]), reverse=True)
r.check("purga: conserva las 3 muertes más recientes aunque sean viejas y borra las demás si pasan de 24 h", set(borrar) == set(muertes[3:]) - {n for n in muertes[3:] if AHORA - int(n.split("_")[-1]) <= DIA}
        and not (set(borrar) & set(muertes[:3])) and len(borrar) >= 1)
r.check("purga: nada que borrar si todo es reciente", mi.waypoints_a_purgar({f"muerte_nox_{AHORA - 1000 * i}": {} for i in range(10)}, AHORA) == [])
r.check("purga: con 3 o menos automáticos no se borra ninguno por viejos que sean", mi.waypoints_a_purgar({f"muerte_nox_{AHORA - 30 * DIA - i}": {} for i in range(3)}, AHORA) == [])
r.check("purga: entradas raras no revientan", mi.waypoints_a_purgar(None, AHORA) == [] and mi.waypoints_a_purgar({1: 2, "muerte_nox_": 3, "muerte_nox_x": 4}, AHORA) == [])

r.terminar()
