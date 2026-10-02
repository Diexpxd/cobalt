"""Bloque G (Python): guardaespaldas, robo de aggro, asistencia al morir el jugador, creepers, SOS, triangulación y guardia por chat."""
import os
import sys

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_proteccion as pr  # noqa: E402
import nox_pro as np  # noqa: E402

r = Resultados()


def ent(id_, kind="hostile", x=0.0, y=64.0, z=0.0, dist=10.0, **kw):
    e = {"id": id_, "kind": kind, "type": "minecraft:zombie", "name": "Zombie", "x": x, "y": y, "z": z, "dist": dist, "boss": False,
         "ranged": False, "los": True, "approaching": False, "targets_player": False, "targets_bot": False}
    e.update(kw)
    return e


def jugador(x=0.0, y=64.0, z=0.0, hp=20.0, max_hp=20.0):
    return ent(1, "player", x, y, z, 0.0, owner=True, hp=hp, max_hp=max_hp, name="Steve")


def datos(*entidades, bot=(0.0, 64.0, 0.0)):
    return {"entities": list(entidades), "hazards": [], "bot": {"x": bot[0], "y": bot[1], "z": bot[2]}}


VIVO = {"is_deployed": True, "hp_pct": 100, "following": True}
GPS = {"x": 0, "y": 64, "z": 0, "dimension": "minecraft:overworld", "owner": {"x": 0, "y": 64, "z": 0, "hp": 20.0, "max_hp": 20.0, "alive": True}}

r.check("vida_dueno_pct: de entities.json y, si no, de gps.owner", pr.vida_dueno_pct({}, datos(jugador(hp=5, max_hp=20))) == 25.0
        and pr.vida_dueno_pct({"owner": {"hp": 10, "max_hp": 20}}, datos()) == 50.0 and pr.vida_dueno_pct({}, datos()) is None)
esq = ent(2, "hostile", dist=20, ranged=True, name="Skeleton")
jefe = ent(3, "hostile", dist=25, boss=True, name="Wither")
crip = ent(4, "hostile", dist=3, swelling=True, name="Creeper")
r.check("mayor_amenaza: jefe > creeper hinchándose > arquero con LoS > zombi cercano",
        pr.mayor_amenaza(datos(ent(9, dist=2), esq, jefe))["id"] == 3 and pr.mayor_amenaza(datos(ent(9, dist=2), esq, crip))["id"] == 4
        and pr.mayor_amenaza(datos(ent(9, dist=2), esq))["id"] == 2 and pr.mayor_amenaza(datos(ent(9, dist=2)))["id"] == 9 and pr.mayor_amenaza(datos()) is None)

g = pr.Guardaespaldas()
esq20 = ent(2, "hostile", x=20.0, y=64.0, z=0.0, dist=20, ranged=True, los=True, name="Skeleton")
o = g.actualizar(VIVO, GPS, datos(jugador(), esq20), 10.0)
sg = [x for x in o if x["action"] == "stand_ground"]
r.check("guardaespaldas: ante un arquero se pone ENTRE jugador y amenaza (a 3 del jugador, y+1) con radio 3", len(sg) == 1 and (sg[0]["x"], sg[0]["y"], sg[0]["z"]) == (3, 65, 0) and sg[0]["radius"] == 3)
r.check("guardaespaldas: avisa una sola vez", sum(1 for x in o if x["action"] == "ninguna") == 1)
r.check("guardaespaldas: no reajusta antes de 1.5 s", g.actualizar(VIVO, GPS, datos(jugador(), esq20), 10.5) == [])
esq_mov = dict(esq20, x=0.0, z=20.0)
o = g.actualizar(VIVO, GPS, datos(jugador(), esq_mov), 12.0)
sg = [x for x in o if x["action"] == "stand_ground"]
r.check("guardaespaldas: si la amenaza cambia de lado reajusta el puesto (ahora hacia +z)", len(sg) == 1 and (sg[0]["x"], sg[0]["z"]) == (0, 3) and not [x for x in o if x["action"] == "ninguna"])
r.check("guardaespaldas: la amenaza desaparece: a los 4 s restablece el seguimiento",
        g.actualizar(VIVO, GPS, datos(jugador()), 20.0) == [] and [x["action"] for x in g.actualizar(VIVO, GPS, datos(jugador()), 24.5)] == ["follow"])
r.check("guardaespaldas: ya restablecido, no repite", g.actualizar(VIVO, GPS, datos(jugador()), 30.0) == [])
g2 = pr.Guardaespaldas()
r.check("guardaespaldas: un zombi (cuerpo a cuerpo) no lo activa", g2.actualizar(VIVO, GPS, datos(jugador(), ent(5, x=5.0, dist=5)), 0.0) == [])
r.check("guardaespaldas: un arquero SIN línea de vista no lo activa", g2.actualizar(VIVO, GPS, datos(jugador(), dict(esq20, los=False)), 0.0) == [])
r.check("guardaespaldas: en vida crítica no se expone", g2.actualizar(dict(VIVO, critical_hp=True), GPS, datos(jugador(), esq20), 0.0) == [])
r.check("guardaespaldas: una amenaza a más de 30 m del jugador no cuenta", g2.actualizar(VIVO, GPS, datos(jugador(), dict(esq20, x=60.0, dist=60)), 0.0) == [])
g3 = pr.Guardaespaldas()
o = g3.actualizar(dict(VIVO, following=False), GPS, datos(jugador(), jefe_pos := dict(jefe, x=15.0, z=0.0, dist=15)), 0.0)
g3.actualizar(dict(VIVO, following=False), GPS, datos(jugador()), 1.0)
r.check("guardaespaldas: ante un jefe (aunque no dispare) se activa; si NO seguía al jugador no fuerza el follow al terminar",
        any(x["action"] == "stand_ground" for x in o) and g3.actualizar(dict(VIVO, following=False), GPS, datos(jugador()), 10.0) == [])

gps_bajo = {"owner": {"x": 0, "y": 64, "z": 0, "hp": 3.0, "max_hp": 20.0, "alive": True}}
zomb = ent(7, dist=5, targets_player=True)
a = pr.RoboDeAggro()
o = a.actualizar(dict(VIVO, emp_ready=True), gps_bajo, datos(zomb), 0.0)
r.check("aggro: con el jugador al 15 % ataca al agresor por id: defend + shoot_plasma + EMP (cerca y no jefe), todo urgente",
        [x["action"] for x in o] == ["defend", "shoot_plasma", "special_power"] and o[0]["target_id"] == 7 and o[1]["target_id"] == 7 and all(x.get("_urgente") for x in o))
r.check("aggro: chat solo la primera vez; cooldown de 3 s", "chat_message" in o[0] and a.actualizar(dict(VIVO, emp_ready=True), gps_bajo, datos(zomb), 1.0) == [])
o = a.actualizar(dict(VIVO, emp_ready=True), gps_bajo, datos(zomb), 4.0)
r.check("aggro: la segunda vez sin chat", len(o) == 3 and "chat_message" not in o[0])
b = pr.RoboDeAggro()
o = b.actualizar(dict(VIVO, emp_ready=True), gps_bajo, datos(zomb, ent(9, dist=20, targets_player=True, boss=True, name="Wither")), 0.0)
r.check("aggro: entre un jefe y un zombi elige al JEFE y no usa el EMP contra jefes", o[0]["target_id"] == 9 and all(x["action"] != "special_power" for x in o))
c = pr.RoboDeAggro()
r.check("aggro: jugador al 50 % -> nada", c.actualizar(VIVO, {"owner": {"hp": 10, "max_hp": 20}}, datos(zomb), 0.0) == [])
r.check("aggro: nadie le ataca -> nada", c.actualizar(VIVO, gps_bajo, datos(ent(7, dist=5, targets_player=False)), 0.0) == [])
r.check("aggro: si Cobalt está en vida crítica no se expone", c.actualizar(dict(VIVO, critical_hp=True), gps_bajo, datos(zomb), 0.0) == [])
r.check("aggro: EMP solo si está listo", [x["action"] for x in pr.RoboDeAggro().actualizar(dict(VIVO, emp_ready=False), gps_bajo, datos(zomb), 0.0)] == ["defend", "shoot_plasma"])

m = pr.AsistenciaMuerteDueno()
gps_vivo = {"owner": {"x": 100.5, "y": 64, "z": 50.2, "hp": 20.0, "max_hp": 20.0, "alive": True}}
gps_muerto = {"owner": {"x": 0, "y": 64, "z": 0, "hp": 0.0, "max_hp": 20.0, "alive": False}}
r.check("asistencia: con el jugador vivo no hace nada", m.actualizar(VIVO, gps_vivo, 0.0) == [])
o = m.actualizar(VIVO, gps_muerto, 1.0)
r.check("asistencia: al morir el jugador va a donde estaba y monta guardia de 10 bloques (urgente)",
        [x["action"] for x in o] == ["go_to", "stand_ground"] and (o[0]["x"], o[0]["y"], o[0]["z"]) == (100, 64, 50) and o[1]["radius"] == 10 and all(x.get("_urgente") for x in o))
r.check("asistencia: mientras tanto no repite", m.actualizar(VIVO, gps_muerto, 5.0) == [])
gps_vuelve = {"owner": {"x": 98, "y": 64, "z": 50, "hp": 20.0, "max_hp": 20.0, "alive": True}}
r.check("asistencia: el jugador reaparece y vuelve a por sus cosas: espera 8 s y retoma el seguimiento",
        m.actualizar(VIVO, gps_vuelve, 20.0) == [] and [x["action"] for x in m.actualizar(VIVO, gps_vuelve, 29.0)] == ["follow"])
m2 = pr.AsistenciaMuerteDueno()
m2.actualizar(VIVO, gps_vivo, 0.0)
m2.actualizar(VIVO, gps_muerto, 1.0)
r.check("asistencia: si nadie vuelve, a los 5 minutos deja la guardia", [x["action"] for x in m2.actualizar(VIVO, gps_muerto, 400.0)] == ["follow"])
r.check("asistencia: sin datos del jugador o sin Cobalt desplegado -> nada", pr.AsistenciaMuerteDueno().actualizar(VIVO, {}, 0.0) == []
        and pr.AsistenciaMuerteDueno().actualizar({"is_deployed": False}, gps_vivo, 0.0) == [])
m3 = pr.AsistenciaMuerteDueno()
r.check("asistencia: si el jugador ya estaba muerto al empezar (sin posición previa) no inventa un punto", m3.actualizar(VIVO, gps_muerto, 0.0) == [])

ev = pr.EvasionCreeper()
crip4 = ent(5, x=4.0, y=64.0, z=0.0, dist=4, swelling=True, name="Creeper")
o = ev.actualizar(VIVO, GPS, datos(crip4, bot=(0.0, 64.0, 0.0)), 0.0)
r.check("creeper: hinchándose a 4 m -> se aparta 10 bloques en dirección opuesta (a x=-10, y+1), en vuelo y urgente",
        len(o) == 1 and o[0]["action"] == "go_to" and (o[0]["x"], o[0]["y"], o[0]["z"]) == (-10, 65, 0) and o[0]["movement_mode"] == "fly" and o[0].get("_urgente"))
r.check("creeper: cooldown de 2 s", ev.actualizar(VIVO, GPS, datos(crip4, bot=(0.0, 64.0, 0.0)), 1.0) == [] and len(ev.actualizar(VIVO, GPS, datos(crip4, bot=(0.0, 64.0, 0.0)), 2.5)) == 1)
ev2 = pr.EvasionCreeper()
o = ev2.actualizar(VIVO, GPS, datos(jugador(x=5.0), crip4, bot=(0.0, 64.0, 0.0)), 0.0)
r.check("creeper: si el jugador está a menos de 7 del creeper, se le avisa (una sola vez)", [x["action"] for x in o] == ["ninguna", "go_to"]
        and [x["action"] for x in ev2.actualizar(VIVO, GPS, datos(jugador(x=5.0), crip4, bot=(0.0, 64.0, 0.0)), 3.0)] == ["go_to"])
r.check("creeper: sin hincharse o a 12 m no hace nada", pr.EvasionCreeper().actualizar(VIVO, GPS, datos(dict(crip4, swelling=False)), 0.0) == []
        and pr.EvasionCreeper().actualizar(VIVO, GPS, datos(dict(crip4, dist=12)), 0.0) == [])
r.check("creeper: exactamente encima de Cobalt no da NaN (elige una dirección)", (lambda o: len(o) == 1 and isinstance(o[0]["x"], int))(pr.EvasionCreeper().actualizar(VIVO, GPS, datos(dict(crip4, x=0.0, dist=0.5), bot=(0.0, 64.0, 0.0)), 0.0)))

s = pr.AlertaSOS()
gps_p = {"x": 10.7, "y": 30, "z": -4.2}
s.actualizar({"is_deployed": True, "hp_pct": 100}, gps_p, datos(), 0.0)
o = s.actualizar({"is_deployed": True, "hp_pct": 55}, gps_p, datos(ent(1, dist=3, name="Zombie"), ent(2, dist=5, name="Zombie"), ent(3, dist=9, name="Skeleton")), 4.0)
r.check("SOS: una caída de 45 puntos en 4 s avisa con coordenadas, vida y atacantes (sin repetir nombres)",
        len(o) == 1 and "[10, 30, -4]" in o[0]["chat_message"] and "55%" in o[0]["chat_message"] and "Me atacan 3: Zombie, Skeleton" in o[0]["chat_message"] and o[0].get("_urgente"))
r.check("SOS: cooldown de 60 s", s.actualizar({"is_deployed": True, "hp_pct": 10}, gps_p, datos(), 10.0) == [])
s2 = pr.AlertaSOS()
s2.actualizar({"is_deployed": True, "hp_pct": 100}, gps_p, datos(), 0.0)
r.check("SOS: una bajada lenta (100 -> 60 en 20 s) NO alerta", s2.actualizar({"is_deployed": True, "hp_pct": 80}, gps_p, datos(), 10.0) == []
        and s2.actualizar({"is_deployed": True, "hp_pct": 60}, gps_p, datos(), 20.0) == [])
r.check("SOS: sin datos de vida o no desplegado -> nada", s2.actualizar({"is_deployed": True}, gps_p, datos(), 30.0) == [] and s2.actualizar({"is_deployed": False, "hp_pct": 1}, gps_p, datos(), 31.0) == [])

esq30 = ent(3, x=30.0, y=64.0, z=0.0, dist=30, ranged=True, name="Skeleton")
zomb_lado = ent(4, x=0.0, y=64.0, z=20.0, dist=20, name="Zombie")
e1, m1, p1 = pr.triangular_agresor({"projectile": True, "sx": 30.5, "sz": 0.2}, datos(esq30, zomb_lado))
r.check("triangulación: si Java informa el origen, se identifica al tirador (método 'conocido')", e1 and e1["id"] == 3 and m1 == "conocido")
flecha = {"projectile": True, "dx": 5.0, "dz": 0.0, "dvx": -1.5, "dvz": 0.0}
e2, m2_, p2 = pr.triangular_agresor(flecha, datos(esq30, zomb_lado))
r.check("triangulación: sin origen conocido, proyecta la flecha hacia atrás y halla al esqueleto en su línea (no al zombi de lado)", e2 and e2["id"] == 3 and m2_ == "triangulado")
e3, m3_, p3 = pr.triangular_agresor(flecha, datos(zomb_lado))
r.check("triangulación: si nadie queda en la línea, informa la DIRECCIÓN de donde vino (punto a 20 m hacia +x)", e3 is None and m3_ == "direccion" and p3 == (25.0, 0.0))
r.check("triangulación: un enemigo DETRÁS del punto de impacto (por donde iba la flecha) no cuenta", pr.triangular_agresor(flecha, datos(ent(8, x=-30.0, dist=30, ranged=True)))[0] is None)
r.check("triangulación: sin proyectil o con velocidad nula -> nada", pr.triangular_agresor({"projectile": False}, datos(esq30)) == (None, None, None)
        and pr.triangular_agresor(dict(flecha, dvx=0.0), datos(esq30)) == (None, None, None) and pr.triangular_agresor(None, datos()) == (None, None, None))
r.check("cardinales: +x este, +z sur, -x oeste, -z norte", [pr._cardinal(10, 0), pr._cardinal(0, 10), pr._cardinal(-10, 0), pr._cardinal(0, -10)] == ["este", "sur", "oeste", "norte"])
t = pr.Triangulacion()
est_dano = dict(VIVO, last_damage=flecha)
o = t.actualizar(est_dano, GPS, datos(esq30, bot=(0.0, 64.0, 0.0)), 0.0)
r.check("Triangulacion: contraataca al tirador localizado (defend + shoot_plasma por id), urgente", [x["action"] for x in o] == ["defend", "shoot_plasma"] and o[0]["target_id"] == 3 and all(x.get("_urgente") for x in o))
r.check("Triangulacion: el mismo daño no se procesa dos veces", t.actualizar(est_dano, GPS, datos(esq30, bot=(0.0, 64.0, 0.0)), 5.0) == [])
t2 = pr.Triangulacion()
o = t2.actualizar(est_dano, GPS, datos(zomb_lado, bot=(0.0, 64.0, 0.0)), 0.0)
r.check("Triangulacion: sin tirador visible avisa de la dirección ('este')", len(o) == 1 and "este" in o[0]["chat_message"] and "no veo al tirador" in o[0]["chat_message"])
r.check("Triangulacion: sin last_damage o sin desplegar -> nada", t2.actualizar(VIVO, GPS, datos(), 50.0) == [] and t2.actualizar({"is_deployed": False, "last_damage": flecha}, GPS, datos(), 60.0) == [])

r.check("chat: 'Cobalt, cúbreme que voy a minar' -> cubrir", pr.interpretar_guardia("Cobalt, cúbreme que voy a minar") == "cubrir")
r.check("chat: 'modo torreta' y 'monta guardia' -> torreta", pr.interpretar_guardia("modo torreta") == "torreta" and pr.interpretar_guardia("monta guardia aquí") == "torreta")
r.check("chat: 'deja de guardar' y 'ya terminé de minar' -> seguir", pr.interpretar_guardia("deja de guardar") == "seguir" and pr.interpretar_guardia("ya terminé de minar") == "seguir")
r.check("chat: frases normales -> None", all(pr.interpretar_guardia(x) is None for x in ("hola", "mina hierro", "sígueme", "", None)))
o = pr.ordenes_guardia("cubrir", {"owner": {"x": 10.9, "y": 64.0, "z": -3.1}})
r.check("guardia: 'cubrir' -> stand_ground en la posición del jugador (radio 10)", o[0]["action"] == "stand_ground" and (o[0]["x"], o[0]["y"], o[0]["z"]) == (10, 64, -4) and o[0]["radius"] == 10)
r.check("guardia: 'cubrir' sin posición del jugador -> guardia donde está; 'torreta' y 'seguir'", "x" not in pr.ordenes_guardia("cubrir", {})[0] and pr.ordenes_guardia("torreta", {})[0]["radius"] == 12
        and pr.ordenes_guardia("seguir", {})[0]["action"] == "follow" and pr.ordenes_guardia("nada", {}) == [])
r.check("orden(): urgente=True añade la marca _urgente; por defecto no", np.orden("x", urgente=True)["_urgente"] is True and "_urgente" not in np.orden("x"))

r.terminar()
