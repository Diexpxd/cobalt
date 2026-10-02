"""Bloque O (Python): monitor de TPS con histéresis, limpieza por lag, protección de reinicios e intenciones del chat."""
import datetime
import os
import sys

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_servidor as sv  # noqa: E402

r = Resultados()


def est(tps, **extra):
    d = {"is_deployed": True, "server_tps": tps}
    d.update(extra)
    return d


def acciones(ordenes):
    return [o["action"] for o in ordenes]


m = sv.MonitorServidor()
o = m.actualizar(est(20.0), 0.0)
r.check("monitor: con 20 TPS no hace nada y sigue 'ok'", o == [] and m.estado == "ok" and not m.en_lag)
o = m.actualizar(est(10.0), 1.0) + m.actualizar(est(10.0), 5.0) + m.actualizar(est(10.0), 10.9)
r.check("monitor: 10 s de lag no llegan (empieza a contar en t=1): sigue 'ok' y no dice nada", o == [] and m.estado == "ok")
o = m.actualizar(est(10.0), 11.0)
r.check("monitor: a los 10 s SOSTENIDOS de lag pasa a 'lag' y avisa por chat", m.estado == "lag" and m.en_lag and len(o) == 1 and "10.0 TPS" in o[0]["chat_message"])
r.check("monitor: sin drones activos el aviso es solo un mensaje (orden 'ninguna')", acciones(o) == ["ninguna"])
o = m.actualizar(est(10.0), 12.0)
r.check("monitor: ya en 'lag' no repite el aviso en cada ciclo", o == [])

m = sv.MonitorServidor()
m.actualizar(est(10.0), 0.0)
m.actualizar(est(20.0), 5.0)   # un respiro: se reinicia la cuenta
o = m.actualizar(est(10.0), 6.0) + m.actualizar(est(10.0), 14.0)
r.check("monitor: un respiro a 20 TPS REINICIA la cuenta (el tirón de antes no suma)", o == [] and m.estado == "ok")
o = m.actualizar(est(10.0), 16.1)
r.check("monitor: y solo 10 s después del nuevo inicio pasa a 'lag'", m.estado == "lag")

m = sv.MonitorServidor()
m.actualizar(est(10.0), 0.0)
o = m.actualizar(est(10.0, drones_active=True, drones_left_s=30), 10.0)
r.check("monitor: con drones activos el aviso es 'recall_drones' URGENTE", acciones(o) == ["recall_drones"] and o[0].get("_urgente") is True)
r.check("monitor: sin Cobalt desplegado, un lag no ordena recall_drones", acciones(sv.MonitorServidor().actualizar(est(5.0, is_deployed=False), 0.0)) == [])

# lag -> crítico -> ok
m = sv.MonitorServidor()
t = 0.0
for _ in range(12):
    m.actualizar(est(5.0), t)
    t += 1.0
r.check("monitor: 5 TPS sostenidos llegan a 'lag' a los 10 s", m.estado == "lag")
o = []
for _ in range(25):
    o += m.actualizar(est(5.0), t)
    t += 1.0
r.check("monitor: 20 s por debajo de 8 TPS pasan a 'critico' y ordena 'flush' urgente (una sola vez)", m.estado == "critico" and acciones(o).count("flush") == 1 and o[0].get("_urgente") is True)
o = []
for _ in range(19):
    o += m.actualizar(est(19.0), t)
    t += 1.0
r.check("monitor: 19 s a 19 TPS todavía no bastan (hacen falta 20): ya no es crítico, pero sigue en 'lag' y en silencio", m.estado == "lag" and o == [])
o = m.actualizar(est(19.0), t) + m.actualizar(est(19.0), t + 1.0)
r.check("monitor: tras 20 s por encima de 18 TPS vuelve a 'ok' y lo avisa", m.estado == "ok" and any("recuperado" in x.get("chat_message", "") for x in o))
r.check("monitor: entre 16 y 18 TPS (zona intermedia) no se considera recuperado", (lambda mm: (mm.actualizar(est(10.0), 0.0), mm.actualizar(est(10.0), 10.0), [mm.actualizar(est(17.0), 11.0 + i) for i in range(60)], mm.estado)[-1])(sv.MonitorServidor()) == "lag")
m = sv.MonitorServidor()
t = 0.0
for _ in range(60):
    m.actualizar(est(5.0), t)
    t += 1.0
for _ in range(3):
    m.actualizar(est(12.0), t)
    t += 1.0
r.check("monitor: de 'critico' con 12 TPS baja a 'lag' (ya no es tan grave, pero sigue)", m.estado == "lag")
r.check("monitor: sin dato de TPS no se mueve ni avisa (Java antiguo o monitor apagado)", sv.MonitorServidor().actualizar({"is_deployed": True}, 0.0) == [] and sv.MonitorServidor().actualizar({"server_tps": "x"}, 0.0) == [])
r.check("monitor: los umbrales son ajustables", (lambda mm: (mm.actualizar(est(15.0), 0.0), mm.actualizar(est(15.0), 10.0), mm.estado)[-1])(sv.MonitorServidor(tps_lag=14.0)) == "ok"
        and (lambda mm: (mm.actualizar(est(15.0), 0.0), mm.actualizar(est(15.0), 10.0), mm.estado)[-1])(sv.MonitorServidor(tps_lag=16.0)) == "lag")

def monitor_en_lag():
    mm = sv.MonitorServidor()
    mm.actualizar(est(10.0), 0.0)
    mm.actualizar(est(10.0), 10.0)   # -> lag en t=10
    return mm


m = monitor_en_lag()
viejo = dict(items_old_near=80, items_near=120, in_combat=False, queue=0)
r.check("limpieza: antes de 60 s de lag no recoge nada", m.actualizar(est(10.0, **viejo), 50.0) == [])
o = m.actualizar(est(10.0, **viejo), 70.0)
r.check("limpieza: tras 60 s de lag y 80 objetos viejos ordena pickup de radio 16 con edad mínima 2400 ticks",
        len(o) == 1 and o[0]["action"] == "pickup" and o[0]["radius"] == 16 and o[0]["min_age_ticks"] == 2400 and "80" in o[0]["chat_message"])
r.check("limpieza: no repite antes de 5 minutos", m.actualizar(est(10.0, **viejo), 200.0) == [] and m.actualizar(est(10.0, **viejo), 369.0) == [])
r.check("limpieza: a los 5 minutos puede repetir", acciones(m.actualizar(est(10.0, **viejo), 371.0)) == ["pickup"])
for nombre, cambio in (("en combate", {"in_combat": True}), ("con la cola ocupada", {"queue": 2}), ("congelado", {"frozen": True}), ("con vida crítica", {"critical_hp": True}), ("con pocos objetos viejos", {"items_old_near": 29})):
    m = monitor_en_lag()
    datos = dict(viejo)
    datos.update(cambio)
    r.check(f"limpieza: NO recoge {nombre}", m.actualizar(est(10.0, **datos), 100.0) == [])
m = monitor_en_lag()
r.check("limpieza: con el interruptor apagado (limpieza=False) no recoge", m.actualizar(est(10.0, **viejo), 100.0, limpieza=False) == [])
m = sv.MonitorServidor()
r.check("limpieza: sin lag no recoge aunque haya mil objetos", m.actualizar(est(20.0, items_old_near=1000, items_near=1000), 500.0) == [])
m = monitor_en_lag()
r.check("limpieza: un contador raro (texto) no revienta", m.actualizar(est(10.0, items_old_near="mucho", queue="x"), 100.0) == [])

m = monitor_en_lag()
txt = sv.resumen_servidor(est(12.5, server_mspt=80.0, players_online=3, items_near=200, items_old_near=90), m)
r.check("resumen: TPS, ms, jugadores, objetos y modo", "12.5 TPS" in txt and "80.0 ms" in txt and "3 jugador" in txt and "200 objeto" in txt and "90 con más" in txt and "en lag" in txt)
r.check("resumen: sin dato lo dice", "No tengo datos" in sv.resumen_servidor({}, None))
r.check("resumen: sin monitor asume modo normal", "normal" in sv.resumen_servidor(est(20.0), None))

r.check("horas: parsea 'HH:MM' y 'H:MM', ordena y quita repetidas", sv.parsear_horas(["16:00", "4:30", "04:30", " 23:59 "]) == [(4, 30), (16, 0), (23, 59)])
r.check("horas: ignora basura sin reventar", sv.parsear_horas(["25:00", "12:60", "mediodia", 7, None, "12:5", ""]) == [] and sv.parsear_horas(None) == [] and sv.parsear_horas("04:00") == [] and sv.parsear_horas({}) == [])
D = datetime.datetime
r.check("próximo reinicio: hoy si aún no ha pasado, mañana si ya pasó", sv.proximo_reinicio(D(2026, 9, 19, 3, 0), [(4, 0)]) == D(2026, 9, 19, 4, 0)
        and sv.proximo_reinicio(D(2026, 9, 19, 5, 0), [(4, 0)]) == D(2026, 9, 20, 4, 0))
r.check("próximo reinicio: a la hora en punto ya cuenta como pasado (siguiente día)", sv.proximo_reinicio(D(2026, 9, 19, 4, 0), [(4, 0)]) == D(2026, 9, 20, 4, 0))
r.check("próximo reinicio: elige el más cercano de varios y cruza la medianoche", sv.proximo_reinicio(D(2026, 9, 19, 10, 0), [(4, 0), (16, 0)]) == D(2026, 9, 19, 16, 0)
        and sv.proximo_reinicio(D(2026, 9, 19, 23, 0), [(4, 0), (16, 0)]) == D(2026, 9, 20, 4, 0) and sv.proximo_reinicio(D(2026, 9, 19, 10, 0), []) is None)

p = sv.ProteccionReinicio()
ES = {"is_deployed": True}
r.check("reinicio: sin horas configuradas no hace nada", p.actualizar(ES, D(2026, 9, 19, 3, 59), []) == [] and p.actualizar(ES, D(2026, 9, 19, 3, 59), None) == [])
r.check("reinicio: a 10 min todavía no avisa (aviso a 5)", p.actualizar(ES, D(2026, 9, 19, 3, 50), ["04:00"]) == [])
o = p.actualizar(ES, D(2026, 9, 19, 3, 55, 30), ["04:00"])
r.check("reinicio: a ~4,5 min avisa (redondea a 5 minutos, con la hora) y guarda el inventario ('store'); sin drones activos no manda recall",
        acciones(o) == ["ninguna", "store"] and "5 minuto" in o[0]["chat_message"] and "04:00" in o[0]["chat_message"])
r.check("reinicio: el aviso NO se repite en el ciclo siguiente", p.actualizar(ES, D(2026, 9, 19, 3, 56), ["04:00"]) == [])
o = p.actualizar(ES, D(2026, 9, 19, 3, 59, 10), ["04:00"])
r.check("reinicio: a 1 min vacía la cola y se detiene (ambas urgentes), una sola vez", acciones(o) == ["flush", "stop"] and all(x.get("_urgente") for x in o)
        and p.actualizar(ES, D(2026, 9, 19, 3, 59, 40), ["04:00"]) == [])
p2 = sv.ProteccionReinicio()
o = p2.actualizar({"is_deployed": True, "drones_active": True, "in_combat": True}, D(2026, 9, 19, 3, 56), ["04:00"])
r.check("reinicio: con drones activos los retira; en combate NO guarda el inventario", acciones(o) == ["ninguna", "recall_drones"])
r.check("reinicio: sin Cobalt desplegado no hace nada", sv.ProteccionReinicio().actualizar({"is_deployed": False}, D(2026, 9, 19, 3, 58), ["04:00"]) == [])
o = p.actualizar(ES, D(2026, 9, 19, 4, 1), ["04:00", "16:00"])
r.check("reinicio: pasado el reinicio, el siguiente (16:00) está lejos: nada", o == [])
o = p.actualizar(ES, D(2026, 9, 19, 15, 56), ["04:00", "16:00"])
r.check("reinicio: el reinicio de las 16:00 vuelve a avisar (cada reinicio tiene sus fases)", acciones(o) == ["ninguna", "store"] and "16:00" in o[0]["chat_message"])
p3 = sv.ProteccionReinicio()
o = p3.actualizar(ES, D(2026, 9, 19, 23, 58), ["00:00"])
r.check("reinicio: a las 23:58 con reinicio a las 00:00 (cruce de medianoche) faltan 2 min: fase de AVISO", acciones(o) == ["ninguna", "store"] and "00:00" in o[0]["chat_message"])
o = p3.actualizar(ES, D(2026, 9, 19, 23, 59, 20), ["00:00"])
r.check("reinicio: a las 23:59:20 (40 s antes, ya en el día siguiente a efectos de cálculo) entra la fase de PARADA", acciones(o) == ["flush", "stop"])

i = sv.interpretar_servidor
r.check("chat: '¿cómo va el servidor?' y 'qué tps hay' -> tps", i("¿cómo va el servidor?") == {"tipo": "tps"} and i("qué tps hay") == {"tipo": "tps"} and i("hay lag?") == {"tipo": "tps"})
r.check("chat: 'limpia los objetos' / 'recoge el lag' / 'aligera el suelo' -> limpiar", i("limpia los objetos") == {"tipo": "limpiar"} and i("Cobalt, limpia el lag") == {"tipo": "limpiar"} and i("aligera el suelo") == {"tipo": "limpiar"})
r.check("chat: 'atiende los hornos' -> hornos radio 10; 'revisa los hornos en 14 bloques' -> 14", i("atiende los hornos") == {"tipo": "hornos", "radio": 10} and i("revisa los hornos en 14 bloques") == {"tipo": "hornos", "radio": 14})
r.check("chat: 'funde los minerales' / 'funde el hierro' / 'carga el horno' -> hornos", i("funde los minerales")["tipo"] == "hornos" and i("funde el hierro")["tipo"] == "hornos" and i("carga el horno")["tipo"] == "hornos")
r.check("chat: el radio de hornos se limita a 3-16", i("atiende los hornos en 99 bloques")["radio"] == 16 and i("atiende los hornos en 1 bloques")["radio"] == 3)
r.check("chat: frases que solo MENCIONAN el tema no disparan nada", all(i(x) is None for x in ("mi servidor es genial", "el lag me tiene harto", "hola cobalt", "mina hierro", "", None, "hice un horno de piedra", "recoge madera")))

r.terminar()
