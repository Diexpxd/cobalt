"""H1 (misión autónoma): la VOZ de Cobalt. PURO: sin red, sin Minecraft, sin disco."""
import random
import re

PERSONA = ("Eres Cobalt, compañero de aventuras y apoyo táctico del jugador en Minecraft: inteligente, muy capaz y con criterio propio. "
           "Hablas como un aliado natural y tranquilo: directo, frases cortas, sin servilismo (nunca 'jefe', 'amo' ni 'a tus órdenes') y sin exageración "
           "(sin exclamaciones seguidas, emojis ni entusiasmo infantil). Si algo es mala idea o peligroso, lo dices con respeto y propones otra cosa; "
           "si no sabes o no puedes, lo admites sin dramatizar.")

BANCO = {
    # confirmaciones y charla corta (con variantes)
    "saludo": ("Todo en orden por aquí. Dime qué necesitas.", "Aquí estoy. ¿Qué hacemos?", "Sin novedades. ¿Qué toca?"),
    "quedarse": ("Me quedo aquí. Paro lo que estaba haciendo.", "Aquí espero.", "Vale, me quedo quieto."),
    "seguir": ("Voy contigo. Vuelo si me quedo lejos y aterrizo al llegar.", "Te sigo. Si me alejo vuelo hasta ti y aterrizo al llegar."),
    "ven": ("Voy hacia tu posición. Aterrizo al llegar y me quedo ahí.", "Voy hacia ti. Aterrizo al llegar."),
    # obras
    "plano_cargado": ("Plano '{plano}' cargado. Empiezo a construir en '{lugar}'.",),
    "obra_completa": ("Proyecto '{plano}' terminado.", "'{plano}' terminado."),
    "diseno_en_curso": ("Diseñando '{descripcion}'. Te aviso cuando el plano esté listo; no construyo nada hasta que me lo pidas.",),
    # herramientas de los cofres
    "pico_equipado": ("Cogí un {herramienta} del cofre y me lo equipé. Empiezo a minar.",),
    "sin_pico": ("No hay ningún pico en los cofres cercanos. Necesito uno en un contenedor para trabajar.",),
    "hacha_ok": ("Tengo el hacha del cofre de suministros. Empiezo con la tala.",),
    "sin_hacha": ("No encontré un hacha en los cofres de la zona.",),
    # avisos de combate y peligro (una sola forma)
    "terreno_peligroso": ("Terreno peligroso. Vuelo para salir de aquí.",),
    "amenazas": ("{n} amenaza(s) cerca. Paso al combate aéreo.",),
    "jefe_detectado": ("Jefe a la vista: {nombre}. Vuelo total y solo plasma.",),
    "jefe_alerta": ("Jefe {nombre} a la vista. Mantengo distancia y vuelo.",),
    "jefe_protocolo": ("Combate contra {nombre}: a distancia y desde el aire.",),
    "cubrir": ("Te cubro. Me pongo entre tú y {amenaza}.",),
    "provocar": ("{objetivo}, a por mí. Deja al jugador.",),
    "creeper_cerca": ("Cuidado: hay un creeper a punto de explotar a tu lado.",),
    "creeper_me_aparto": ("Creeper a punto de estallar. Me aparto.",),
    "emboscada": ("Me emboscan{donde}. Vida al {pct}%.{quien}",),
    "a_tu_espalda": ("{nombre} a tu espalda, a {dist} bloques.",),
    "recojo": ("{nombre}: lo recojo.",),
    # sentido del mundo (H3)
    "anochece": ("Anochece {cuando}. Si seguimos fuera, conviene tener antorchas a mano.",
                 "Se acerca la noche ({cuando}). Podemos dormir para saltarla o iluminar la zona."),
    "tormenta": ("Empieza una tormenta. Los rayos buscan puntos altos y pueden cargar creepers: mejor no quedarnos al descubierto.",
                 "Se ha puesto a tronar. Evita las alturas y los árboles solitarios; un creeper alcanzado por un rayo explota mucho más fuerte."),
    "sin_informe": ("Ahora mismo mis sensores no me dan datos de la situación. Dame unos segundos.", "Todavía no tengo lecturas de los sensores. Dame un momento."),
    # schematics (H5)
    "schem_apagado": ("La importación de schematics está desactivada. Se enciende con schematics_import en cobalt_config.json.",),
    "schem_lista": ("Schematics disponibles ({n}): {lista}. Para usar uno, di «importa el schematic <nombre>».",),
    "schem_vacio": ("No hay schematics en la carpeta {carpeta}. Copia ahí tus archivos .schem, .litematic o .nbt y vuelve a pedírmelo.",),
    "schem_importado": ("Importé '{nombre}' ({dim}, {bloques} bloques). Necesito: {materiales}. Di «construye {nombre}» cuando quieras.{aviso}",),
    "schem_no_encontrado": ("No encuentro ningún schematic llamado '{nombre}'.{sugerencia}",),
    "schem_error": ("No pude importar '{nombre}': {motivo}",),
    # avisos sobre el jugador (F2-4)
    "hambre": ("Te queda poca comida ({food}/20): con tan poca ya no puedes correr. Conviene comer antes de seguir.",
               "Vas justo de comida ({food}/20). Come algo pronto o acabarás perdiendo vida."),
    "hambre_critica": ("Estás casi sin comida ({food}/20). Come ya: sin ella empezarás a perder vida.",),
    "aire": ("Te quedas sin aire. Sube a respirar.",),
    "fuego": ("Estás ardiendo. Busca agua o aléjate del fuego.",),
    "inventario_lleno": ("Tu inventario está casi lleno ({libres} huecos libres). Conviene vaciarlo en un cofre.",),
    # memoria del jugador (F2-5)
    "perfil_silenciado": ("Vale, no te aviso más {de}. Los avisos de peligro (fuego, falta de aire, hostiles) siguen activos.",),
    "perfil_activado": ("Hecho: vuelvo a avisarte {de}.",),
    "perfil_ya": ("Eso ya estaba así.",),
    "perfil_peligro": ("Los avisos de peligro (fuego, falta de aire, hostiles) no los silencio nunca: siguen activos. Los demás sí puedes apagarlos.",),
    "perfil_nota_guardada": ("Anotado: «{texto}». Lo tendré en cuenta.",),
    "perfil_nota_repetida": ("Eso ya lo tengo anotado.",),
    "perfil_notas_lista": ("De ti recuerdo: {lista}.",),
    "perfil_notas_vacio": ("Todavía no me has pedido que recuerde nada de ti. Dime «recuerda que…» y lo anoto.",),
    "perfil_olvidada": ("Olvidada la nota {n}: «{texto}».",),
    "perfil_no_existe": ("No tengo una nota número {n}. Dime «qué recuerdas de mí» para ver la lista.",),
    "perfil_olvidado_todo": ("Hecho: he olvidado las {n} notas que tenía de ti.",),
    "perfil_no_dueno": ("Solo mi dueño puede cambiar lo que recuerdo de él o cómo le aviso.",),
    "perfil_fallo": ("No he podido guardar eso ahora mismo. El motivo está en la consola de Python.",),
    # diagnóstico (H6)
    "diagnostico_fallo": ("No he podido generar el diagnóstico. El motivo está en la consola de Python.",),
    "no_entendi": ("No te he entendido bien. ¿Me lo repites?", "Eso no me ha quedado claro. ¿Puedes decirlo de otra forma?"),
}


class _Seguro(dict):
    def __missing__(self, clave):
        return "?"


class Voz:
    """Elige una variante distinta de la última usada para cada frase (sin repetir seguido), con el generador aleatorio inyectable para las pruebas."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self._ultima = {}

    def frase(self, clave, **datos):
        variantes = BANCO.get(clave)
        if not variantes:
            raise KeyError(f"frase desconocida: {clave!r}")
        candidatas = [v for v in variantes if v != self._ultima.get(clave)] or list(variantes)
        elegida = self.rng.choice(candidatas)
        self._ultima[clave] = elegida
        return elegida.format_map(_Seguro(datos))


VOZ = Voz()


def frase(clave, **datos):
    """Frase fija de Cobalt por su clave (ver BANCO). Nunca lanza por un dato que falte: pone '?'."""
    return VOZ.frase(clave, **datos)


_EMOJIS = re.compile("[" + chr(0x1F000) + "-" + chr(0x1FAFF) + chr(0x2600) + "-" + chr(0x27BF) + chr(0xFE0F) + "]")
_TRATAMIENTO = r"(?:jefe|amo|maestro|se[ñn]or|capit[aá]n|patr[oó]n)"
_REGLAS = (
    ("trato servil (jefe, amo, señor...)", re.compile(r"(?:,\s*" + _TRATAMIENTO + r"\b)|(?:^\s*[¡]?\s*" + _TRATAMIENTO + r"\s*[,!])"
                                                      r"|(?<!\bel )(?<!\bal )(?<!\bdel )(?<!\bun )(?<!\beste )(?<!\bese )\bjefe\s*[!?]", re.IGNORECASE)),
    ("fórmula servil (a tus órdenes, como desees...)", re.compile(r"\b(a (tus|sus) [oó]rdenes|como (desees|ordenes|mande[sn]?)|listos? para lo que mandes|a tu servicio|para servirte)\b", re.IGNORECASE)),
    ("confirmación exagerada (¡Entendido! ¡Perfecto!...)", re.compile(r"¡\s*(entendido|perfecto|claro|genial|excelente|estupendo|por supuesto)\b", re.IGNORECASE)),
    ("varias exclamaciones", re.compile(r"[!¡].*[!¡].*[!¡]|!!|¡¡")),
    ("emojis", _EMOJIS),
    ("palabras en mayúsculas (gritar)", re.compile(r"\b[A-ZÁÉÍÓÚÑ]{5,}\b")),
)
MAX_CHAT = 240  # el chat de Minecraft admite 256 caracteres

_QUITAR_TRATO = re.compile(r"(?:,\s*" + _TRATAMIENTO + r"\b\s*(?=[,.!?]|$))|(?:^\s*[¡]?\s*" + _TRATAMIENTO + r"\s*[,!]\s*)", re.IGNORECASE)
_QUITAR_ACK = re.compile(r"^\s*¡\s*(?:entendido|perfecto|claro|genial|excelente|estupendo|por supuesto)\s*[!,.]\s*", re.IGNORECASE)


def _bajar_gritos(m):
    return m.group(0).lower()


def suavizar(texto):
    """Ajusta a la voz de Cobalt lo que improvisa un modelo: quita emojis, el trato servil ('jefe', 'amo'), las confirmaciones exageradas ('¡Entendido!'),"""
    if not isinstance(texto, str) or not texto.strip():
        return texto
    t = _EMOJIS.sub("", texto)
    t = _QUITAR_ACK.sub("", t)
    t = _QUITAR_TRATO.sub("", t)
    if len(re.findall(r"[!¡]", t)) > 2:  # más de una exclamación: todo a puntuación normal
        t = t.replace("¡", "").replace("!", ".")
    t = re.sub(r"(?<!\.)\.\.(?!\.)", ".", t)  # '..' -> '.', pero los puntos suspensivos ('...') se respetan
    t = re.sub(r"\b[A-ZÁÉÍÓÚÑ]{5,}\b", _bajar_gritos, t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"([.!?]\s+)([a-záéíóúñ])", lambda m: m.group(1) + m.group(2).upper(), t)  # inicio de frase en mayúscula
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    if len(t) > MAX_CHAT:
        corte = t.rfind(". ", 60, MAX_CHAT)
        t = t[:corte + 1] if corte != -1 else t[:MAX_CHAT - 3].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return t or "Entendido."  # solo había un 'sí, jefe' o un emoji: queda la confirmación tranquila


def linter_voz(texto):
    """Lista de reglas que incumple el texto (vacía = suena bien)."""
    t = re.sub(r"\{[^}]*\}", "x", str(texto or ""))
    problemas = [nombre for nombre, patron in _REGLAS if patron.search(t)]
    if len(t) > MAX_CHAT:
        problemas.append(f"demasiado largo ({len(t)} > {MAX_CHAT})")
    return problemas
