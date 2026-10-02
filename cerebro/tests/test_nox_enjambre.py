"""Enjambre de drones (Python): cuándo pedirlo automáticamente y las órdenes por chat."""
import os
import sys

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_enjambre as en  # noqa: E402

r = Resultados()


def hostil(id_, dist=10.0, **kw):
    e = {"id": id_, "kind": "hostile", "name": "Zombie", "dist": dist, "boss": False, "targets_player": False}
    e.update(kw)
    return e


def jugador(hp=20.0, max_hp=20.0):
    return {"id": 1, "kind": "player", "owner": True, "hp": hp, "max_hp": max_hp, "x": 0, "y": 64, "z": 0, "dist": 0.0}


def datos(*ents):
    return {"entities": list(ents), "hazards": []}


LISTO = {"is_deployed": True, "drones_ready": True, "drones_active": False, "hp_pct": 100}

m = en.motivo_de_despliegue
r.check("motivo: un jefe a 25 m", m(LISTO, {}, datos(hostil(2, 25.0, boss=True, name="Wither"))) == "jefe Wither")
r.check("motivo: un jefe a 40 m aún no", m(LISTO, {}, datos(hostil(2, 40.0, boss=True))) is None)
r.check("motivo: 4 enemigos a <= 16 m (horda)", m(LISTO, {}, datos(*[hostil(i, 10.0) for i in range(4)])) == "4 enemigos cerca")
r.check("motivo: 3 enemigos no son horda; 4 pero a 20 m tampoco", m(LISTO, {}, datos(*[hostil(i, 10.0) for i in range(3)])) is None
        and m(LISTO, {}, datos(*[hostil(i, 20.0) for i in range(4)])) is None)
r.check("motivo: el jugador por debajo del 50 % con un enemigo atacándole", m(LISTO, {}, datos(jugador(hp=6.0), hostil(2, 12.0, targets_player=True))) == "el jugador está en peligro")
r.check("motivo: jugador herido pero NADIE le ataca -> nada", m(LISTO, {}, datos(jugador(hp=6.0), hostil(2, 12.0))) is None)
r.check("motivo: jugador sano con un enemigo atacándole -> nada", m(LISTO, {}, datos(jugador(hp=18.0), hostil(2, 12.0, targets_player=True))) is None)
r.check("motivo: jugador en peligro medido por gps.owner cuando no está en entities.json", m(LISTO, {"owner": {"hp": 4.0, "max_hp": 20.0}}, datos(hostil(2, 12.0, targets_player=True))) == "el jugador está en peligro")
r.check("motivo: Cobalt en combate con < 50 % de vida y 2+ enemigos cerca", m(dict(LISTO, in_combat=True, hp_pct=40), {}, datos(hostil(1, 8.0), hostil(2, 9.0))) == "Cobalt está en apuros")
r.check("motivo: Cobalt con poca vida pero SIN combate, o con 1 solo enemigo -> nada", m(dict(LISTO, in_combat=False, hp_pct=40), {}, datos(hostil(1, 8.0), hostil(2, 9.0))) is None
        and m(dict(LISTO, in_combat=True, hp_pct=40), {}, datos(hostil(1, 8.0))) is None)
r.check("motivo: prioridad = el jefe gana a la horda", m(LISTO, {}, datos(*[hostil(i, 8.0) for i in range(5)], hostil(9, 20.0, boss=True, name="Warden"))) == "jefe Warden")
r.check("motivo: sin enemigos / datos raros -> nada", m(LISTO, {}, datos()) is None and m(LISTO, {}, {}) is None and m(LISTO, {}, {"entities": ["x", {"kind": "hostile"}]}) is None)

d = en.DespliegueDrones()
horda = datos(*[hostil(i, 8.0) for i in range(5)])
o = d.actualizar(LISTO, {}, horda, 0.0)
r.check("auto: con una horda y el enjambre listo pide 'deploy_drones' (urgente, sin chat propio: Java avisa)", len(o) == 1 and o[0]["action"] == "deploy_drones" and o[0].get("_urgente") and "chat_message" not in o[0])
r.check("auto: no insiste durante 5 s", d.actualizar(LISTO, {}, horda, 3.0) == [] and len(d.actualizar(LISTO, {}, horda, 5.5)) == 1)
r.check("auto: si Java dice que NO está listo (enfriamiento de 4 min) no pide nada", en.DespliegueDrones().actualizar(dict(LISTO, drones_ready=False, drones_cooldown_s=200), {}, horda, 0.0) == [])
r.check("auto: si ya hay drones activos no pide más", en.DespliegueDrones().actualizar(dict(LISTO, drones_active=True), {}, horda, 0.0) == [])
r.check("auto: Cobalt congelado (OMEGA) o sin desplegar -> nada", en.DespliegueDrones().actualizar(dict(LISTO, frozen=True), {}, horda, 0.0) == []
        and en.DespliegueDrones().actualizar(dict(LISTO, is_deployed=False), {}, horda, 0.0) == [])
r.check("auto: sin motivo no pide nada aunque esté listo", en.DespliegueDrones().actualizar(LISTO, {}, datos(hostil(1, 5.0)), 0.0) == [])
r.check("auto: un estado sin 'drones_ready' (Java antiguo) NO dispara nada", en.DespliegueDrones().actualizar({"is_deployed": True}, {}, horda, 0.0) == [])
r.check("auto: entidades None no revientan", en.DespliegueDrones().actualizar(LISTO, {}, None, 0.0) == [])
r.check("auto: recuerda el último motivo (para trazas)", d.ultimo_motivo == "5 enemigos cerca")

ie = en.interpretar_enjambre
r.check("chat: 'despliega los drones', 'Cobalt, lanza el enjambre', 'suelta a los drones' -> deploy", all(ie(x) == "deploy" for x in ("despliega los drones", "Cobalt, lanza el enjambre", "suelta a los drones", "por favor activa los drones")))
r.check("chat: 'drones', 'enjambre', 'refuerzos', 'apoyo aéreo' sueltos -> deploy", all(ie(x) == "deploy" for x in ("drones", "¡Enjambre!", "refuerzos", "apoyo aéreo", "drones ya")))
r.check("chat: 'retira los drones', 'recoge el enjambre', 'drones fuera' -> recall", all(ie(x) == "recall" for x in ("retira los drones", "recoge el enjambre", "Cobalt, guarda los drones", "drones fuera", "cancela los drones")))
r.check("chat: frases que solo MENCIONAN los drones NO disparan nada", all(ie(x) is None for x in ("los drones de Create son geniales", "ayer vi un enjambre de abejas", "hola cobalt", "", None, "mina hierro")))
o = en.ordenes_por_chat("deploy", "Steve")
r.check("chat: deploy -> orden deploy_drones dirigida al usuario", o[0]["action"] == "deploy_drones" and o[0]["target"] == "Steve")
o = en.ordenes_por_chat("recall", "Steve")
r.check("chat: recall -> orden recall_drones con aviso; tipo desconocido -> nada", o[0]["action"] == "recall_drones" and "Retiro" in o[0]["chat_message"] and en.ordenes_por_chat("x", "Steve") == [])

r.terminar()
