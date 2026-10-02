"""H2: memoria que se usa (nox_memoria.py)."""
import copy
import json
import os
import sys
import time

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_memoria as m  # noqa: E402

r = Resultados()

r.check("normalizar quita acentos y mayúsculas", m.normalizar("Ñandú Cañón ÁÉÍÓÚ") == "nandu canon aeiou")
r.check("tokens: sin palabras vacías ni palabras de 1-2 letras, con plural recortado", m.tokens("Los creepers de la base y el reactor") == ["creeper", "base", "reactor"])
r.check("tokens: conserva 'ae2' (2 letras con cifra) y descarta 'de', 'el'", "ae2" in m.tokens("el AE2 de Applied") and "de" not in m.tokens("el AE2 de Applied"))
r.check("tokens: 'conduits' y 'conduit' dan la misma raíz (consulta y documento coinciden), 'acciones' -> 'accion', 'reactores' -> 'reactor'",
        m.tokens("conduits")[0] == m.tokens("conduit")[0] and m.tokens("acciones") == ["accion"] and m.tokens("reactores") == ["reactor"])
r.check("tokens tolera None, vacío y símbolos", m.tokens(None) == [] and m.tokens("") == [] and m.tokens("¡¿?!") == [])
r.check("jaccard: iguales = 1, disjuntos = 0, mitad = 1/3", m.jaccard("a b".split(), "a b".split()) == 1 and m.jaccard("a".split(), "b".split()) == 0 and abs(m.jaccard("a b".split(), "b c".split()) - 1 / 3) < 1e-9)
r.check("jaccard con vacíos = 0 (no divide por cero)", m.jaccard([], ["a"]) == 0 and m.jaccard([], []) == 0)

basura = ["Lo siento, pero no puedo proporcionar un resumen sobre un modo de Minecraft sin acceso a internet. El texto que me proporcionaste solo indica que no hay conexión.",
          "No tengo acceso a información sobre ese mod, así que no puedo darte un resumen útil de ello ahora mismo.", "Como modelo de lenguaje, no puedo verificar datos actuales de ese mod de Minecraft.",
          "No se encontró información suficiente sobre este mod en los fragmentos que recibí de internet.", "corto", "", None, 5, "x" * 1000,
          "No encontré nada claro sobre el tema en los resultados de búsqueda que se me han dado hoy."]
buenos = ["Los conduits de Ender IO son el sistema de transporte central, utilizados para items, energía, líquidos y señales de redstone. Reemplazan los tubos tradicionales.",
          "Ars Nouveau es un mod de Minecraft que añade un sistema de magia avanzado con glifos para crear hechizos y escribas automatizados.",
          "El reactor de fisión de Mekanism necesita combustible, refrigerante y una carcasa de acero multibloque para funcionar sin sobrecalentarse."]
r.check("es_basura detecta disculpas, negativas, textos cortos/largos y tipos raros: " + str([b for b in basura if not m.es_basura(b)]), all(m.es_basura(b) for b in basura))
r.check("es_basura NO marca un resumen real: " + str([b[:30] for b in buenos if m.es_basura(b)]), not any(m.es_basura(b) for b in buenos))

est = {"2026-09-01 10:00": {"tema": "Mekanism reactor", "resumen": buenos[2]},
       "2026-09-02 10:00": {"tema": "Mekanism reactor", "resumen": buenos[2] + " Además requiere un puerto de salida."},   # casi igual: se funde
       "2026-09-03 10:00": {"tema": "Mekanism reactor", "resumen": basura[0]},                                                  # basura: fuera
       "2026-09-04 10:00": {"tema": "Mekanism reactor", "resumen": "Los cables de energía universales de Mekanism transportan energía entre máquinas y almacenes muy grandes."},
       "2026-09-05 10:00": {"tema": "Mekanism reactor", "resumen": "El generador solar de Mekanism produce energía durante el día y necesita un cable hasta el almacén de energía."},
       "2026-09-06 10:00": {"tema": "Ender IO", "resumen": buenos[0]}, "2026-09-09 10:00": {"tema": "Ender IO", "resumen": buenos[0] + " Son muy configurables."},
       "2026-09-07 10:00": "no soy un dict", "2026-09-08 10:00": {"tema": "", "resumen": buenos[1]}}
docs = m.documentos_de_estudio(est)
temas = [d.tema for d in docs]
r.check("estudio: sin basura, sin repetidos, máximo 2 por tema, ignora entradas mal formadas: " + str([(d.tema, d.texto[:25]) for d in docs]),
        temas.count("Mekanism reactor") == 2 and temas.count("Ender IO") == 1 and len(docs) == 3)
r.check("de dos resúmenes casi iguales (los MÁS RECIENTES) solo queda uno: el más nuevo", [d.texto for d in docs if d.tema == "Ender IO"] == [buenos[0] + " Son muy configurables."])
r.check("de los 2 de Mekanism conserva los MÁS RECIENTES (solar y cables) y descarta el reactor viejo",
        {d.texto[:20] for d in docs if d.tema == "Mekanism reactor"} == {"El generador solar d", "Los cables de energí"})
r.check("estudio no-dict o vacío -> lista vacía", m.documentos_de_estudio(None) == [] and m.documentos_de_estudio([]) == [] and m.documentos_de_estudio({}) == [])

corpus = {"2026-09-01 10:00": {"tema": "Mekanism reactor", "resumen": buenos[2]}, "2026-09-02 10:00": {"tema": "Ender IO conduits", "resumen": buenos[0]},
          "2026-09-03 10:00": {"tema": "Ars Nouveau spells", "resumen": buenos[1]}}
idx = m.Indice(m.documentos_de_estudio(corpus))
def mejor(q):
    res = idx.buscar(q)
    return res[0][1].tema if res else None
r.check("cada consulta sobre un mod devuelve SU tema: reactor->Mekanism, conduits->Ender IO, hechizos->Ars Nouveau",
        mejor("cómo funciona el reactor de fisión de Mekanism") == "Mekanism reactor" and mejor("para qué sirven los conduits de Ender IO") == "Ender IO conduits" and mejor("qué hechizos hay en Ars Nouveau") == "Ars Nouveau spells")
r.check("consulta sin nada que ver -> nada (mejor callar que meter ruido)", idx.buscar("mina hierro por favor") == [] and idx.buscar("hola cobalt cómo estás") == [] and idx.buscar("") == [] and idx.buscar(None) == [])
r.check("índice vacío -> nada", m.Indice([]).buscar("reactor") == [])
flojo = m.Documento("a", "t", "solo cables", ("cable", "energia", "relleno", "relleno2"), 1.0, 0)
fuerte = m.Documento("b", "t", "reactor y cables", ("reactor", "fision", "cable", "combustible"), 1.0, 1)
otro = m.Documento("c", "t", "nada", ("hierro", "cofre", "base", "mina"), 1.0, 2)
orden = [d.clave for _, d in m.Indice([flojo, fuerte, otro]).buscar("reactor fision cable", k=3, minimo=0.01)]
r.check("el resultado con MÁS coincidencias va primero aunque esté después en la lista de documentos: " + str(orden), orden == ["b", "a"])
r.check("el umbral funciona: con minimo muy alto no devuelve nada", idx.buscar("reactor de Mekanism", minimo=1000) == [])
raro = m.Indice([m.Documento(f"d{i}", "t", "x", ("comun", "raro") if i == 0 else ("comun",), 1.0, i) for i in range(10)])
r.check("las palabras raras pesan más que las comunes (idf): una en 1 de 10 documentos vale MÁS que una en los 10", raro.idf("raro") > raro.idf("comun") and raro.idf("raro") > 1.5)
r.check("el umbral escala con el tamaño de la memoria: idf_max crece con el número de documentos", raro.idf_max() > m.Indice(raro.docs[:3]).idf_max() > 0)
r.check("k limita los resultados", len(idx.buscar("mod energia reactor conduits hechizos", k=1, minimo=0.1)) == 1)

b = m.bloque_conocimiento("cómo funciona el reactor de fisión de Mekanism", corpus)
r.check("bloque: viñeta con el tema entre corchetes y el resumen: " + repr(b[:70]), b.startswith("- [Mekanism reactor] El reactor de fisión") and b.count("\n") == 0)
r.check("bloque: '' si nada es relevante", m.bloque_conocimiento("sígueme", corpus) == "" and m.bloque_conocimiento("reactor", None) == "")
largo = {"2026-09-01 10:00": {"tema": "Mekanism", "resumen": "reactor " * 100}}
bl = m.bloque_conocimiento("reactor Mekanism", largo, minimo=0.1)
r.check("un resumen largo se recorta a ~300 caracteres con '...'", bl.endswith("...") and len(bl) < 360)
dos = {**corpus, "2026-09-04 10:00": {"tema": "Mekanism cables", "resumen": "Los cables de energía universales de Mekanism transportan energía entre máquinas y almacenes muy grandes."}}
r.check("respeta el tope de caracteres: con 60 no cabe ninguna viñeta", m.bloque_conocimiento("Mekanism energía reactor cables", dos, max_chars=60, minimo=0.1) == "")
r.check("puede incluir lecciones tácticas relevantes", "creeper" in m.bloque_conocimiento("qué hago con el creeper que se acerca", {}, ["Ante un creeper mantén distancia y usa el plasma antes de que se acerque."], minimo=0.1))

lec = ["Si estás en el agua cambia a 'swim' para nadar.", "Ante un creeper aléjate y ataca desde lejos.", "Guarda el hierro en el cofre de la base.", "El Wither se combate desde el aire."]
p = m.priorizar_lecciones(lec, "hay un creeper cerca")
r.check("las lecciones relevantes pasan al FINAL (el recorte por presupuesto conserva el final) y no se pierde ninguna: " + str(p), p[-1] == lec[1] and sorted(p) == sorted(lec))
r.check("sin consulta o sin coincidencias el orden no cambia", m.priorizar_lecciones(lec, "") == lec and m.priorizar_lecciones(lec, "qué hora es") == lec and m.priorizar_lecciones([], "creeper") == [])
r.check("tolera elementos raros", m.priorizar_lecciones([None, 5, "  ", "Ante un creeper aléjate"], "creeper") == ["Ante un creeper aléjate"])

base = {"2026-09-01 10:00": {"tema": "Mekanism reactor", "resumen": buenos[2]}}
copia = copy.deepcopy(base)
n, acc = m.guardar_estudio(base, "Mekanism reactor", basura[0], "2026-09-02 10:00")
r.check("guardar_estudio: una negativa se DESCARTA y no cambia nada", acc == "descartado" and n == base)
n, acc = m.guardar_estudio(base, "Mekanism reactor", buenos[2] + " Además requiere un puerto.", "2026-09-05 10:00")
r.check("un resumen casi igual del mismo tema REEMPLAZA al anterior (no se acumulan 23 repetidos): " + acc, acc == "reemplazado" and len(n) == 1 and "2026-09-05 10:00" in n and "2026-09-01 10:00" not in n)
n, acc = m.guardar_estudio(base, "Ender IO", buenos[0], "2026-09-06 10:00")
r.check("otro tema se guarda aparte", acc == "guardado" and len(n) == 2)
n, acc = m.guardar_estudio(base, "Ender IO", buenos[2], "2026-09-06 10:00")
r.check("el MISMO texto en OTRO tema no se funde (es otro conocimiento)", acc == "guardado" and len(n) == 2)
r.check("guardar_estudio no modifica el diccionario original", base == copia)
mismo_minuto, _ = m.guardar_estudio(base, "Ender IO", buenos[0], "2026-09-01 10:00")
r.check("dos estudios de temas distintos en el MISMO minuto no se pisan (antes el segundo borraba al primero): " + str(sorted(mismo_minuto)),
        len(mismo_minuto) == 2 and mismo_minuto["2026-09-01 10:00"]["tema"] == "Mekanism reactor" and mismo_minuto["2026-09-01 10:00 #2"]["tema"] == "Ender IO")
tercero, _ = m.guardar_estudio(mismo_minuto, "Ars Nouveau", buenos[1], "2026-09-01 10:00")
r.check("y un tercero en el mismo minuto recibe '#3'", sorted(tercero) == ["2026-09-01 10:00", "2026-09-01 10:00 #2", "2026-09-01 10:00 #3"])
reemplazo, acc2 = m.guardar_estudio(base, "Mekanism reactor", buenos[2] + " Además requiere un puerto.", "2026-09-01 10:00")
r.check("reemplazar en el mismo minuto reutiliza la misma clave (sin '#2' sobrante)", acc2 == "reemplazado" and list(reemplazo) == ["2026-09-01 10:00"])
docs_minuto = m.documentos_de_estudio(mismo_minuto)
r.check("las claves con sufijo '#n' se leen bien y cuentan como más recientes que la base del minuto", {d.tema for d in docs_minuto} == {"Mekanism reactor", "Ender IO"})
r.check("sin tema -> descartado", m.guardar_estudio(base, "", buenos[0], "x")[1] == "descartado" and m.guardar_estudio(base, None, buenos[0], "x")[1] == "descartado")
tema_x = {}
distintos = ["Los sensores de proximidad detectan jugadores cercanos y emiten una señal de redstone hacia los bloques adyacentes del sistema.", "Las tuberías de vacío transportan objetos entre cofres grandes mediante filtros de etiquetas configurables por el jugador.",
            "El generador geotérmico quema lava líquida para producir energía constante sin ningún combustible sólido añadido a la máquina.", "Las baterías de plomo almacenan energía y se recargan rápidamente conectadas a los paneles solares del techo.",
            "Los teletransportadores de mercancías necesitan una plataforma de destino sincronizada con la frecuencia elegida en el panel.", "Las prensas de compactación convierten minerales en placas que sirven para fabricar carcasas metálicas resistentes."]
for i, txt in enumerate(distintos):
    tema_x, _ = m.guardar_estudio(tema_x, "Tema X", txt, f"2026-09-{i + 1:02d} 10:00", max_por_tema=5)
r.check("máximo 5 entradas por tema: se tiran las más antiguas (quedan las 5 recientes): " + str(sorted(tema_x))[:80], len(tema_x) == 5 and "2026-09-01 10:00" not in tema_x and "2026-09-06 10:00" in tema_x)
total = {}
for i, txt in enumerate(distintos):
    total, _ = m.guardar_estudio(total, f"Tema {i}", txt, f"2026-09-{i + 1:02d} 10:00", max_total=4)
r.check("tope total (4): se tiran las más antiguas de todo el archivo", len(total) == 4 and "2026-09-01 10:00" not in total and "2026-09-06 10:00" in total)

l1, ok1 = m.agregar_leccion([], "Ante un creeper aléjate y ataca desde lejos.")
r.check("agregar_leccion: una lección nueva se añade", ok1 and len(l1) == 1)
l2, ok2 = m.agregar_leccion(l1, "ante un creeper aléjate y ataca desde lejos.")
r.check("igual sin distinguir mayúsculas -> no se duplica", not ok2 and l2 == l1)
l3, ok3 = m.agregar_leccion(l1, "Ante un creeper, aléjate y ataca desde lejos siempre.")
r.check("casi idéntica (Jaccard >= 0.75) -> no se duplica", not ok3 and len(l3) == 1)
l4, ok4 = m.agregar_leccion(l1, "Guarda el hierro en el cofre de la base.")
r.check("distinta -> se añade", ok4 and len(l4) == 2)
r.check("vacía o None -> no se añade; el original no cambia", m.agregar_leccion(l1, "   ")[1] is False and m.agregar_leccion(l1, None)[1] is False and len(l1) == 1)
r.check("una lección sin palabras significativas ('Sí.') igual se detecta repetida por el texto, sin mayúsculas", m.agregar_leccion(["Sí."], "sí.")[1] is False and m.agregar_leccion(["Sí."], "No.")[1] is True)
r.check("tope de 3: se tiran las más antiguas", m.agregar_leccion(["uno dos tres", "cuatro cinco seis", "siete ocho nueve"], "diez once doce", maximo=3)[0] == ["cuatro cinco seis", "siete ocho nueve", "diez once doce"])

ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conocimiento_mods.json")
if os.path.exists(ruta):
    real = json.load(open(ruta, encoding="utf-8"))
    t0 = time.time()
    docs_r = m.documentos_de_estudio(real)
    idx_r = m.Indice(docs_r)
    consultas = {"cómo funciona el reactor de fisión de Mekanism": "Mekanism", "qué son los conduits de Ender IO": "Ender IO", "cómo automatizo el almacenamiento con Applied Energistics": "Applied Energistics",
                 "dónde está el jefe Ignis de Cataclysm": "Cataclysm", "cómo hago un tren con Create": "Create", "hechizos de Ars Nouveau": "Ars Nouveau"}
    fallos = {q: [x.tema[:25] for _, x in idx_r.buscar(q)][:1] for q, t in consultas.items() if not idx_r.buscar(q) or t not in idx_r.buscar(q)[0][1].tema}
    r.check(f"REAL ({len(real)} entradas -> {len(docs_r)} documentos útiles): cada consulta de un mod devuelve el tema correcto {fallos}", not fallos and len(real) > 20)
    ruido = ["hola cobalt cómo estás", "mina hierro por favor", "sígueme", "qué hora es", "construye una casa de piedra", "cuánta vida tiene el warden", "ven aquí", "guarda este lugar como base"]
    r.check("REAL: la charla y las órdenes normales NO recuperan nada (0 ruido en el prompt): " + str([q for q in ruido if idx_r.buscar(q)]), not any(idx_r.buscar(q) for q in ruido))
    basura_real = [v["resumen"] for v in real.values() if m.es_basura(v.get("resumen"))]
    r.check(f"REAL: detecta {len(basura_real)} negativas/relleno guardadas como conocimiento (incluida la de 'sin acceso a internet')", len(basura_real) >= 5 and any("sin acceso a internet" in x.lower() for x in basura_real))
    r.check(f"REAL: de {len(real)} entradas quedan {len(docs_r)} documentos, como máximo 2 por tema", len(docs_r) < len(real) / 3 and max(sum(1 for d in docs_r if d.tema == t) for t in {d.tema for d in docs_r}) <= 2)
    r.check(f"REAL: índice + 6 consultas en {1000 * (time.time() - t0):.0f} ms (rápido: se reconstruye en cada petición si hace falta)", time.time() - t0 < 1.5)
    bl = m.bloque_conocimiento("cómo funciona el reactor de fisión de Mekanism", real)
    r.check("REAL: el bloque del prompt cabe en 600 caracteres y habla de Mekanism: " + repr(bl[:80]), 0 < len(bl) <= 600 and "Mekanism" in bl)
else:
    print("SKIP  (no está conocimiento_mods.json)")

r.terminar()
