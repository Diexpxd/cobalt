"""nox_inventario.py."""
import nox_voz
from nox_pro import _numero, entidades_de, hostiles, orden


def _corto(recurso):
    return str(recurso).split(":", 1)[-1]


_ALTO = {"diamond", "diamond_block", "netherite_ingot", "netherite_scrap", "netherite_block", "ancient_debris", "emerald", "emerald_block",
         "elytra", "totem_of_undying", "nether_star", "beacon", "shulker_shell", "golden_apple", "enchanted_golden_apple", "trident",
         "heart_of_the_sea", "dragon_egg", "dragon_head", "enchanted_book", "name_tag", "netherite_upgrade_smithing_template",
         "music_disc_pigstep", "sponge", "conduit", "nautilus_shell", "recovery_compass", "echo_shard", "disc_fragment_5"}
_MEDIO = {"gold_ingot", "raw_gold", "iron_ingot", "raw_iron", "copper_ingot", "redstone", "lapis_lazuli", "ender_pearl", "blaze_rod", "experience_bottle",
          "amethyst_shard", "quartz", "glowstone_dust", "slime_ball", "gold_block", "iron_block", "obsidian", "crying_obsidian", "ghast_tear", "coal", "diamond_horse_armor"}
RIPIO = {"cobblestone", "cobbled_deepslate", "dirt", "coarse_dirt", "rooted_dirt", "granite", "diorite", "andesite", "tuff", "netherrack", "gravel",
         "blackstone", "basalt", "calcite", "dripstone_block", "stone", "deepslate", "moss_block", "rotten_flesh", "spider_eye", "poisonous_potato"}


def valor_de_item(item_id, encantado=False):
    """3 = valioso (diamante, netherite, libros encantados, objetos encantados...), 2 = útil, 1 = común, 0 = ripio."""
    ruta = _corto(item_id).lower()
    if encantado or ruta in _ALTO or ruta.startswith(("netherite_", "diamond_")) or ruta.endswith("_shulker_box") or ruta == "shulker_box":
        return 3
    if ruta in _MEDIO or ruta.startswith("raw_") or ruta.endswith("_ingot") or ruta.endswith("_ore"):
        return 2
    if ruta in RIPIO:
        return 0
    return 1


class PreBuff:
    """Al ver un jefe (radar de 32 m, antes de que entre en combate) se beben las pociones tácticas que se tengan y no estén ya activas:"""

    BUFFS = ("strength", "speed", "resistance")
    FUEGO = "fire_resistance"
    PALABRAS_FUEGO = ("blaze", "wither", "ghast", "dragon", "ignis", "fire", "inferno", "hell", "nether", "magma")
    ENTRE_TRAGOS_S = 1.5
    REPETIR_S = 180.0
    DIST_MAX = 32.0

    def __init__(self):
        self.bebidos = {}   # id del jefe -> conjunto de buffs ya intentados
        self.desde = {}     # id del jefe -> cuándo se empezó a preparar
        self.t_trago = -1e9

    def actualizar(self, estado, entidades, ahora):
        if not estado.get("is_deployed") or estado.get("critical_hp"):
            return []
        jefes = [e for e in hostiles(entidades) if e.get("boss") and _numero(e.get("dist")) and e["dist"] <= self.DIST_MAX]
        if not jefes:
            return []
        jefe = min(jefes, key=lambda e: e["dist"])
        clave = jefe.get("id", jefe.get("name"))
        if clave in self.desde and ahora - self.desde[clave] > self.REPETIR_S:
            self.bebidos.pop(clave, None)
            self.desde.pop(clave, None)
        pociones = (estado.get("inventory") or {}).get("potions") or {}
        activos = {_corto(e) for e in (estado.get("effects") or [])}
        dimension = str(estado.get("dimension") or "")
        texto_jefe = f"{jefe.get('type', '')} {jefe.get('name', '')}".lower()
        necesarios = list(self.BUFFS)
        if "nether" in dimension or any(p in texto_jefe for p in self.PALABRAS_FUEGO):
            necesarios.append(self.FUEGO)
        hechos = self.bebidos.setdefault(clave, set())
        for buff in necesarios:
            if pociones.get(buff, 0) > 0 and buff not in activos and buff not in hechos:
                if ahora - self.t_trago < self.ENTRE_TRAGOS_S:
                    return []
                self.desde.setdefault(clave, ahora)
                hechos.add(buff)
                self.t_trago = ahora
                chat = f"Me preparo para {jefe.get('name', 'el jefe')}: poción de {buff.replace('_', ' ')}." if len(hechos) == 1 else None
                return [orden("use_item", chat, effect=buff)]
        return []


class PurgaDebuffs:
    """Con un efecto GRAVE (Wither, Veneno, dos o más efectos dañinos, cualquiera de un mod, o cualquiera estando en vida crítica) y un cubo"""

    GRAVES = {"wither", "poison"}
    COOLDOWN_S = 20.0

    def __init__(self):
        self.t_ultimo = -1e9

    def actualizar(self, estado, ahora):
        malos = list(estado.get("effects_bad") or [])
        if not malos or not estado.get("is_deployed"):
            return []
        if (estado.get("inventory") or {}).get("milk", 0) <= 0 or ahora - self.t_ultimo < self.COOLDOWN_S:
            return []
        nombres = [_corto(m) for m in malos]
        de_mod = any(not str(m).startswith("minecraft:") for m in malos)
        grave = any(n in self.GRAVES for n in nombres) or len(nombres) >= 2 or de_mod or bool(estado.get("critical_hp"))
        if not grave:
            return []
        self.t_ultimo = ahora
        return [orden("use_item", f"Me purgo con leche ({', '.join(nombres)}).", material="milk_bucket", urgente=True)]


class TriageLoot:
    """Si hay algo valioso (valor 3) tirado a <= 12 m: con hueco lo recoge; con el inventario lleno primero suelta ripio (el más abundante,"""

    RADIO = 12.0
    COOLDOWN_S = 20.0
    MAX_INTENTOS = 3

    def __init__(self):
        self.intento = {}
        self.cuenta = {}

    def actualizar(self, estado, entidades, ahora):
        if not estado.get("is_deployed") or estado.get("in_combat") or not isinstance(entidades, dict):
            return []
        objetos = [o for o in (entidades.get("items") or []) if isinstance(o, dict) and _numero(o.get("id")) and _numero(o.get("dist")) and o.get("item")]
        cand = [o for o in objetos if valor_de_item(o["item"], o.get("enchanted")) >= 3 and o["dist"] <= self.RADIO
                and ahora - self.intento.get(o["id"], -1e9) >= self.COOLDOWN_S and self.cuenta.get(o["id"], 0) < self.MAX_INTENTOS]
        if not cand:
            return []
        mejor = max(cand, key=lambda o: (valor_de_item(o["item"], o.get("enchanted")), -o["dist"]))
        self.intento[mejor["id"]] = ahora
        self.cuenta[mejor["id"]] = self.cuenta.get(mejor["id"], 0) + 1
        nombre = _corto(mejor["item"])
        inv = estado.get("inventory") or {}
        salida = []
        if inv.get("full"):
            ripio = {k: v for k, v in (inv.get("junk") or {}).items() if _numero(v) and v > 0}
            if not ripio:
                return [orden("ninguna", f"Hay {nombre} en el suelo, pero mi inventario está lleno y no tengo ripio que soltar.")]
            elegido, cantidad = max(ripio.items(), key=lambda kv: kv[1])
            salida.append(orden("drop", material=elegido, amount=int(min(64, cantidad))))
        salida.append(orden("pickup", nox_voz.frase("recojo", nombre=nombre), entity_id=int(mejor["id"]), radius=int(self.RADIO)))
        return salida


class AvisoDurabilidad:
    """Java ya no usa una herramienta con menos del 5 % de durabilidad; aquí se avisa por chat (una vez cada 5 minutos por objeto)."""

    REPETIR_S = 300.0

    def __init__(self):
        self.avisado = {}

    def actualizar(self, estado, ahora):
        for nombre in (estado.get("inventory") or {}).get("fragile") or []:
            if ahora - self.avisado.get(nombre, -1e9) >= self.REPETIR_S:
                self.avisado[nombre] = ahora
                return [orden("ninguna", f"Mi {_corto(nombre).replace('_', ' ')} está a punto de romperse: dejo de usarla.")]
        return []
