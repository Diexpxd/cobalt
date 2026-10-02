"""Bloque H (Python): valor de objetos, pre-buff, purga con leche, triage de loot, aviso de durabilidad y recogida tras la muerte."""
import os
import sys

from _cargar import RAIZ, Resultados

sys.path.insert(0, os.path.join(RAIZ, "cerebro"))
import nox_inventario as inv  # noqa: E402
import nox_pro as np  # noqa: E402

r = Resultados()


def jefe(id_=3, dist=25.0, tipo="minecraft:wither", nombre="Wither"):
    return {"id": id_, "kind": "hostile", "boss": True, "dist": dist, "type": tipo, "name": nombre, "x": 0, "y": 0, "z": 0}


def datos(*ents, items=None):
    return {"entities": list(ents), "hazards": [], "items": items or []}


v = inv.valor_de_item
r.check("valor: diamante, netherite, libro encantado, shulker y algo encantado = 3", all(v(x) == 3 for x in ("minecraft:diamond", "netherite_ingot", "minecraft:enchanted_book", "minecraft:purple_shulker_box", "diamond_pickaxe", "minecraft:netherite_sword"))
        and v("minecraft:stick", True) == 3)
r.check("valor: lingotes, menas en bruto, redstone, ender pearl = 2", all(v(x) == 2 for x in ("iron_ingot", "raw_gold", "minecraft:redstone", "ender_pearl", "deepslate_iron_ore", "tin_ingot")))
r.check("valor: ripio (cobblestone, tierra, carne podrida) = 0; resto (madera, pan) = 1", v("minecraft:cobblestone") == 0 and v("dirt") == 0 and v("rotten_flesh") == 0
        and v("oak_log") == 1 and v("minecraft:bread") == 1)

pb = inv.PreBuff()
pociones = {"strength": 1, "speed": 2, "resistance": 1, "fire_resistance": 1}
est = {"is_deployed": True, "effects": [], "dimension": "minecraft:overworld", "inventory": {"potions": pociones}}
o = pb.actualizar(est, datos(jefe(3, 28.0, "minecraft:ender_dragon", "Ender Dragon")), 0.0)
r.check("prebuff: al ver un jefe a 28 m bebe fuerza primero (con aviso)", len(o) == 1 and o[0]["action"] == "use_item" and o[0]["effect"] == "strength" and "chat_message" in o[0])
r.check("prebuff: no bebe otra antes de 1.5 s", pb.actualizar(est, datos(jefe(3, 28.0, "minecraft:ender_dragon", "Ender Dragon")), 0.5) == [])
o2 = pb.actualizar(est, datos(jefe(3, 28.0, "minecraft:ender_dragon", "Ender Dragon")), 2.0)
o3 = pb.actualizar(est, datos(jefe(3, 28.0, "minecraft:ender_dragon", "Ender Dragon")), 4.0)
o4 = pb.actualizar(est, datos(jefe(3, 28.0, "minecraft:ender_dragon", "Ender Dragon")), 6.0)
r.check("prebuff: sigue con velocidad, resistencia y (jefe de fuego: dragón) resistencia al fuego, sin más chat",
        [o2[0]["effect"], o3[0]["effect"], o4[0]["effect"]] == ["speed", "resistance", "fire_resistance"] and "chat_message" not in o2[0])
r.check("prebuff: tras terminar no repite con el mismo jefe", pb.actualizar(est, datos(jefe(3, 28.0, "minecraft:ender_dragon", "Ender Dragon")), 10.0) == [])
o5 = pb.actualizar(est, datos(jefe(3, 28.0, "minecraft:ender_dragon", "Ender Dragon")), 200.0)
r.check("prebuff: 3 minutos después vuelve a prepararse", len(o5) == 1 and o5[0]["effect"] == "strength")
pb2 = inv.PreBuff()
est2 = dict(est, effects=["minecraft:strength", "minecraft:speed"], inventory={"potions": {"strength": 1, "speed": 1, "resistance": 1}})
r.check("prebuff: no bebe lo que ya tiene activo", pb2.actualizar(est2, datos(jefe(4, 20.0, "minecraft:warden", "Warden")), 0.0)[0]["effect"] == "resistance")
r.check("prebuff: sin la poción no la inventa; en el Overworld un jefe sin fuego no pide resistencia al fuego",
        inv.PreBuff().actualizar(dict(est, inventory={"potions": {"fire_resistance": 1}}), datos(jefe(5, 20.0, "minecraft:warden", "Warden")), 0.0) == [])
r.check("prebuff: en el Nether sí pide resistencia al fuego", inv.PreBuff().actualizar(dict(est, dimension="minecraft:the_nether", inventory={"potions": {"fire_resistance": 1}}),
                                                                                       datos(jefe(5, 20.0, "minecraft:warden", "Warden")), 0.0)[0]["effect"] == "fire_resistance")
r.check("prebuff: jefe a 40 m, sin jefe, en vida crítica o sin desplegar -> nada", inv.PreBuff().actualizar(est, datos(jefe(6, 40.0)), 0.0) == [] and inv.PreBuff().actualizar(est, datos(), 0.0) == []
        and inv.PreBuff().actualizar(dict(est, critical_hp=True), datos(jefe(6, 20.0)), 0.0) == [] and inv.PreBuff().actualizar(dict(est, is_deployed=False), datos(jefe(6, 20.0)), 0.0) == [])

pg = inv.PurgaDebuffs()
con_leche = {"is_deployed": True, "inventory": {"milk": 1}}
o = pg.actualizar(dict(con_leche, effects_bad=["minecraft:wither"]), 0.0)
r.check("purga: Wither + leche -> bebe leche (urgente, por material milk_bucket)", len(o) == 1 and o[0]["action"] == "use_item" and o[0]["material"] == "milk_bucket" and o[0].get("_urgente"))
r.check("purga: cooldown de 20 s", pg.actualizar(dict(con_leche, effects_bad=["minecraft:wither"]), 5.0) == [] and len(pg.actualizar(dict(con_leche, effects_bad=["minecraft:poison"]), 25.0)) == 1)
r.check("purga: un solo efecto leve (lentitud) NO gasta la leche (quitaría también los buffs)", inv.PurgaDebuffs().actualizar(dict(con_leche, effects_bad=["minecraft:slowness"]), 0.0) == [])
r.check("purga: dos efectos dañinos SÍ", len(inv.PurgaDebuffs().actualizar(dict(con_leche, effects_bad=["minecraft:slowness", "minecraft:weakness"]), 0.0)) == 1)
r.check("purga: un efecto dañino de un MOD SÍ (antídoto genérico)", len(inv.PurgaDebuffs().actualizar(dict(con_leche, effects_bad=["tox:radiation"]), 0.0)) == 1)
r.check("purga: un efecto leve en vida crítica SÍ", len(inv.PurgaDebuffs().actualizar(dict(con_leche, effects_bad=["minecraft:slowness"], critical_hp=True), 0.0)) == 1)
r.check("purga: sin leche, sin efectos o sin desplegar -> nada", inv.PurgaDebuffs().actualizar({"is_deployed": True, "inventory": {"milk": 0}, "effects_bad": ["minecraft:wither"]}, 0.0) == []
        and inv.PurgaDebuffs().actualizar(con_leche, 0.0) == [] and inv.PurgaDebuffs().actualizar(dict(con_leche, is_deployed=False, effects_bad=["minecraft:wither"]), 0.0) == [])

tr = inv.TriageLoot()
diamante = {"id": 50, "item": "minecraft:diamond", "count": 3, "enchanted": False, "dist": 6.0, "x": 1, "y": 64, "z": 1}
libro = {"id": 51, "item": "minecraft:enchanted_book", "count": 1, "enchanted": True, "dist": 9.0}
palo = {"id": 52, "item": "minecraft:stick", "count": 2, "enchanted": False, "dist": 2.0}
hueco = {"is_deployed": True, "inventory": {"full": False}}
o = tr.actualizar(hueco, datos(items=[palo, diamante]), 0.0)
r.check("triage: con hueco recoge el diamante por su id (ignora el palo)", len(o) == 1 and o[0]["action"] == "pickup" and o[0]["entity_id"] == 50)
r.check("triage: no reintenta el mismo objeto antes de 20 s", tr.actualizar(hueco, datos(items=[diamante]), 5.0) == [])
r.check("triage: pasados 20 s vuelve a intentarlo, máximo 3 veces en total", len(tr.actualizar(hueco, datos(items=[diamante]), 25.0)) == 1 and len(tr.actualizar(hueco, datos(items=[diamante]), 50.0)) == 1
        and tr.actualizar(hueco, datos(items=[diamante]), 100.0) == [])
lleno = {"is_deployed": True, "inventory": {"full": True, "junk": {"cobblestone": 40, "dirt": 100, "gravel": 3}}}
o = inv.TriageLoot().actualizar(lleno, datos(items=[libro]), 0.0)
r.check("triage: inventario LLENO -> suelta el ripio más abundante (tierra, máx. 64) y luego recoge el libro encantado",
        [x["action"] for x in o] == ["drop", "pickup"] and o[0]["material"] == "dirt" and o[0]["amount"] == 64 and o[1]["entity_id"] == 51)
r.check("triage: lleno y sin ripio que soltar -> solo avisa (no inventa)", (lambda x: len(x) == 1 and x[0]["action"] == "ninguna")(inv.TriageLoot().actualizar({"is_deployed": True, "inventory": {"full": True, "junk": {}}}, datos(items=[libro]), 0.0)))
r.check("triage: entre dos objetos valiosos elige el más cercano de igual valor", inv.TriageLoot().actualizar(hueco, datos(items=[dict(diamante, id=60, dist=10.0), dict(diamante, id=61, dist=4.0)]), 0.0)[0]["entity_id"] == 61)
r.check("triage: en combate, sin datos, a más de 12 m o sin desplegar -> nada", inv.TriageLoot().actualizar(dict(hueco, in_combat=True), datos(items=[diamante]), 0.0) == []
        and inv.TriageLoot().actualizar(hueco, datos(), 0.0) == [] and inv.TriageLoot().actualizar(hueco, datos(items=[dict(diamante, dist=14.0)]), 0.0) == []
        and inv.TriageLoot().actualizar(dict(hueco, is_deployed=False), datos(items=[diamante]), 0.0) == [] and inv.TriageLoot().actualizar(hueco, None, 0.0) == [])
r.check("triage: objetos con datos raros no revientan", inv.TriageLoot().actualizar(hueco, {"items": [{"id": "x"}, "basura", {"id": 1, "dist": 1}]}, 0.0) == [])

ad = inv.AvisoDurabilidad()
o = ad.actualizar({"inventory": {"fragile": ["diamond_pickaxe", "iron_sword"]}}, 0.0)
r.check("durabilidad: avisa de UNA herramienta frágil por ciclo", len(o) == 1 and "diamond pickaxe" in o[0]["chat_message"])
o = ad.actualizar({"inventory": {"fragile": ["diamond_pickaxe", "iron_sword"]}}, 1.0)
r.check("durabilidad: el siguiente ciclo avisa de la otra; luego ya no (5 min)", len(o) == 1 and "iron sword" in o[0]["chat_message"] and ad.actualizar({"inventory": {"fragile": ["diamond_pickaxe", "iron_sword"]}}, 2.0) == []
        and len(ad.actualizar({"inventory": {"fragile": ["diamond_pickaxe"]}}, 400.0)) == 1)
r.check("durabilidad: sin herramientas frágiles o sin inventario -> nada", ad.actualizar({"inventory": {"fragile": []}}, 999.0) == [] and ad.actualizar({}, 999.0) == [])

rec = np.RecuperacionMuerte()
vivo, muerto = {"is_deployed": True, "is_dead": False}, {"is_deployed": False, "is_dead": True}
rec.actualizar(vivo, {"x": 10, "y": 64, "z": 10, "dimension": "minecraft:overworld"}, 0.0)
rec.actualizar(muerto, {}, 1.0)
rec.actualizar(vivo, {"x": 0, "y": 70, "z": 0, "dimension": "minecraft:overworld"}, 2.0)
o = rec.actualizar(vivo, {"x": 11, "y": 64, "z": 10, "dimension": "minecraft:overworld"}, 3.0)
r.check("muerte: al llegar avisa Y recoge todo lo que haya alrededor (pickup radio 16)", [x["action"] for x in o] == ["ninguna", "pickup"] and o[1]["radius"] == 16 and "Llegué" in o[0]["chat_message"])

r.terminar()
