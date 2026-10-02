"""Bloque J (Python): avisos tácticos y mimetismo humano."""
import os
import random
import sys

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_social as so  # noqa: E402

r = Resultados()


def jugador(x=0.0, z=0.0, yaw=0.0, **kw):
    e = {"id": 1, "kind": "player", "owner": True, "x": x, "y": 64.0, "z": z, "dist": 0.0, "yaw": yaw, "name": "Steve"}
    e.update(kw)
    return e


def hostil(id_, x, z, tipo="minecraft:zombie", nombre="Zombie", **kw):
    e = {"id": id_, "kind": "hostile", "type": tipo, "name": nombre, "x": x, "y": 64.0, "z": z, "dist": 5.0, "approaching": False, "targets_player": False}
    e.update(kw)
    return e


def datos(*ents, hazards=None, bot=(0.0, 64.0, 0.0)):
    return {"entities": list(ents), "hazards": hazards or [], "bot": {"x": bot[0], "y": bot[1], "z": bot[2]}}


VIVO = {"is_deployed": True}

r.check("_detras: mirando al sur (yaw 0), un enemigo al norte está detrás y uno al sur delante", so._detras((0, 64, 0), 0.0, (0, 64, -5)) and not so._detras((0, 64, 0), 0.0, (0, 64, 5)))
r.check("_detras: mirando al oeste (yaw 90), el este (+x) está detrás", so._detras((0, 64, 0), 90.0, (5, 64, 0)) and not so._detras((0, 64, 0), 90.0, (-5, 64, 0)))
r.check("_detras: mirando al este (yaw -90), el oeste está detrás; mirando al norte (yaw 180), el sur",
        so._detras((0, 64, 0), -90.0, (-5, 64, 0)) and so._detras((0, 64, 0), 180.0, (0, 64, 5)))
r.check("_detras: a un lado (90° del frente) NO es 'detrás'; sin yaw o en la misma posición tampoco",
        not so._detras((0, 64, 0), 0.0, (5, 64, 0)) and not so._detras((0, 64, 0), None, (0, 64, -5)) and not so._detras((0, 64, 0), 0.0, (0, 64, 0)))

c = so.CalloutsTacticos()
o = c.actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(7, 0.0, -6.0, "minecraft:creeper", "Creeper")), 0.0)
r.check("callout: un creeper a 6 m a la espalda -> aviso con nombre y distancia", len(o) == 1 and o[0]["action"] == "ninguna" and "Creeper a tu espalda, a 6 bloques" in o[0]["chat_message"])
r.check("callout: el mismo creeper no se repite antes de 10 s, y sí después", c.actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(7, 0.0, -6.0, "minecraft:creeper", "Creeper")), 5.0) == []
        and len(c.actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(7, 0.0, -6.0, "minecraft:creeper", "Creeper")), 11.0)) == 1)
r.check("callout: un creeper DELANTE del jugador (lo ve) no se avisa", so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(7, 0.0, 6.0, "minecraft:creeper", "Creeper")), 0.0) == [])
r.check("callout: un creeper a 20 m no se avisa", so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(7, 0.0, -20.0, "minecraft:creeper", "Creeper")), 0.0) == [])
r.check("callout: un zombi a la espalda que SE ACERCA a 5 m -> aviso; si no se acerca ni le ataca, no",
        len(so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(8, 0.0, -5.0, approaching=True)), 0.0)) == 1
        and so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(8, 0.0, -5.0)), 0.0) == [])
o = so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(yaw=0.0), hostil(8, 0.0, -3.0, approaching=True), hostil(9, 0.0, -9.0, "minecraft:creeper", "Creeper")), 0.0)
r.check("callout: con un zombi y un creeper a la espalda avisa primero del CREEPER (1 aviso por ciclo de espalda)", len(o) == 1 and "Creeper" in o[0]["chat_message"])
o = so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(yaw=0.0, held="minecraft:diamond_pickaxe", held_dur_pct=4.0)), 0.0)
r.check("callout: la herramienta del jugador al 4 % -> 'Tu diamond pickaxe está a punto de romperse (4%)'", len(o) == 1 and "diamond pickaxe" in o[0]["chat_message"] and "4%" in o[0]["chat_message"])
cc = so.CalloutsTacticos()
cc.actualizar(VIVO, {}, datos(jugador(held="minecraft:iron_pickaxe", held_dur_pct=3.0)), 0.0)
r.check("callout: herramienta: cooldown de 2 min; al 50 % no avisa", cc.actualizar(VIVO, {}, datos(jugador(held="minecraft:iron_pickaxe", held_dur_pct=3.0)), 60.0) == []
        and len(cc.actualizar(VIVO, {}, datos(jugador(held="minecraft:iron_pickaxe", held_dur_pct=3.0)), 130.0)) == 1
        and so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(held="minecraft:iron_pickaxe", held_dur_pct=50.0)), 0.0) == [])
tnt = {"type": "tnt", "x": 1, "y": 64, "z": 1, "dist": 2.0}
o = so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(x=1.0, z=1.0), hazards=[tnt]), 0.0)
r.check("callout: TNT a 2 bloques de Cobalt con el jugador al lado -> aviso", len(o) == 1 and "TNT expuesta" in o[0]["chat_message"] and "2 bloques" in o[0]["chat_message"])
ct = so.CalloutsTacticos()
ct.actualizar(VIVO, {}, datos(jugador(), hazards=[tnt]), 0.0)
r.check("callout: la misma trampa no se repite en 60 s", ct.actualizar(VIVO, {}, datos(jugador(), hazards=[tnt]), 30.0) == [] and len(ct.actualizar(VIVO, {}, datos(jugador(), hazards=[tnt]), 70.0)) == 1)
r.check("callout: trampas lejanas (5 m), o inofensivas (fuego), o con el jugador a 20 m de Cobalt -> nada",
        so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(), hazards=[dict(tnt, dist=5.0)]), 0.0) == [] and so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(), hazards=[{"type": "fire", "dist": 1.0}]), 0.0) == []
        and so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(x=20.0, z=20.0), hazards=[tnt]), 0.0) == [])
o = so.CalloutsTacticos().actualizar(VIVO, {}, datos(jugador(yaw=0.0, held="minecraft:stone_pickaxe", held_dur_pct=2.0), hostil(7, 0.0, -6.0, "minecraft:creeper", "Creeper"),
                                                    hazards=[tnt, {"type": "cobweb", "x": 3, "y": 64, "z": 3, "dist": 3.0}]), 0.0)
r.check("callout: como mucho 2 avisos por ciclo", len(o) == 2)
r.check("callout: sin desplegar, sin datos o entidades raras -> nada", so.CalloutsTacticos().actualizar({"is_deployed": False}, {}, datos(hostil(1, 0, -5)), 0.0) == []
        and so.CalloutsTacticos().actualizar(VIVO, {}, None, 0.0) == [] and so.CalloutsTacticos().actualizar(VIVO, {}, {"entities": ["x", {"kind": "hostile"}], "hazards": ["y", None]}, 0.0) == [])

mim = so.Mimetismo(random.Random(1))
tranq = {"is_deployed": True, "movement_mode": "walk", "on_ground": True}
cerca = datos(jugador(dist=4.0))
r.check("mimetismo: el primer ciclo solo programa el siguiente gesto", mim.actualizar(tranq, cerca, 0.0) == [] and mim.proximo is not None and 20.0 <= mim.proximo <= 45.0)
r.check("mimetismo: antes de tocarle no hace nada", mim.actualizar(tranq, cerca, mim.proximo - 1.0) == [])
gestos = []
t = 0.0
for _ in range(60):
    t = mim.proximo
    gestos += [x["action"] for x in mim.actualizar(tranq, cerca, t)]
r.check("mimetismo: en 60 gestos hay miradas y saltitos, y NADA más", set(gestos) == {"look_at", "hop"} and gestos.count("look_at") > gestos.count("hop") > 0)
r.check("mimetismo: los gestos se separan entre 20 y 45 s", 20.0 <= mim.proximo - t <= 45.0)
m2 = so.Mimetismo(random.Random(2))
m2.actualizar(tranq, cerca, 0.0)
o = m2.actualizar(dict(tranq, movement_mode="fly"), cerca, m2.proximo)
r.check("mimetismo: volando solo mira (nunca salta)", len(o) == 1 and o[0]["action"] == "look_at" and 2 <= o[0]["seconds"] <= 4)
m3 = so.Mimetismo(random.Random(3))
m3.actualizar(tranq, datos(), 0.0)
o = m3.actualizar(tranq, datos(), m3.proximo)
r.check("mimetismo: sin jugador cerca no mira; caminando da un saltito", len(o) == 1 and o[0]["action"] == "hop")
m4 = so.Mimetismo(random.Random(4))
m4.actualizar(dict(tranq, movement_mode="fly"), datos(), 0.0)
r.check("mimetismo: volando y sin jugador cerca no hace nada", m4.actualizar(dict(tranq, movement_mode="fly"), datos(), m4.proximo) == [])
for ocupado in ({"in_combat": True}, {"task": "mine:iron_ore 1/8"}, {"guarding": True}, {"frozen": True}, {"critical_hp": True}, {"fleeing": True}, {"boss_mode": True}, {"is_deployed": False}):
    mm = so.Mimetismo(random.Random(5))
    mm.actualizar(tranq, cerca, 0.0)
    r.check(f"mimetismo: no actúa con {list(ocupado)[0]}={list(ocupado.values())[0]} y reinicia el reloj", mm.actualizar(dict(tranq, **ocupado), cerca, mm.proximo) == [] and mm.proximo is None)

ic = so.interpretar_cosecha
r.check("cosecha: 'cosecha', 'Cobalt, cosecha los cultivos', 'recoge la cosecha' -> radio por defecto (12)", ic("cosecha") == 12 and ic("Cobalt, cosecha los cultivos") == 12 and ic("Recoge la cosecha") == 12)
r.check("cosecha: 'cosecha en 20 bloques' -> 20; se limita a 3-24", ic("cosecha en 20 bloques") == 20 and ic("cosecha en 100 bloques") == 24 and ic("cosecha en 1 bloques") == 3)
r.check("cosecha: 'por favor recolecta los cultivos' y 'cosechar' también", ic("por favor recolecta los cultivos") == 12 and ic("cosechar") == 12)
r.check("cosecha: una frase que solo MENCIONA la cosecha NO dispara nada", ic("la cosecha de trigo fue buena") is None and ic("ayer hicimos una cosecha enorme") is None
        and ic("mina hierro") is None and ic("") is None and ic(None) is None and ic("planta trigo") is None)

r.terminar()
