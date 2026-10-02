"""F2-5: memoria del jugador (parte pura): preferencias de avisos («no me avises del hambre»), notas («recuerda que…»), el perfil y el bloque de notas para el prompt."""
import random
import os
import sys

from _cargar import Resultados

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cerebro"))
import nox_perfil as pf  # noqa: E402

r = Resultados()
TODAS = list(pf.CATEGORIAS)

casos = {
    "no me avises del hambre": ("silenciar", ["hambre"]), "no me avises de la comida": ("silenciar", ["hambre"]), "No me avises del hambre, por favor": ("silenciar", ["hambre"]),
    "avísame menos": ("silenciar", TODAS), "Cobalt, avísame menos": ("silenciar", TODAS), "silencia los avisos": ("silenciar", TODAS), "deja de avisarme": ("silenciar", TODAS),
    "no me avises del clima": ("silenciar", ["mundo"]), "no me avises de la noche y la tormenta": ("silenciar", ["mundo"]), "no me avises del inventario y del hambre": ("silenciar", ["inventario", "hambre"]),
    "no me avises de la mochila": ("silenciar", ["inventario"]), "avísame menos del hambre": ("silenciar", ["hambre"]), "silencia los avisos del tiempo": ("silenciar", ["mundo"]),
    "no me avises de todo": ("silenciar", TODAS), "vuelve a avisarme": ("activar", TODAS), "avísame de nuevo": ("activar", TODAS), "reactiva los avisos": ("activar", TODAS),
    "vuelve a avisarme del hambre": ("activar", ["hambre"]), "activa los avisos de la noche": ("activar", ["mundo"]),
    "no me avises de los creepers": ("peligro", []), "no me avises del fuego": ("peligro", []), "no me avises del aire": ("peligro", []), "silencia los avisos de peligro": ("peligro", []),
    "vuelve a avisarme de los hostiles": ("peligro", []),
}
malos = {k: pf.interpretar_aviso(k) for k, v in casos.items() if pf.interpretar_aviso(k) != v}
r.check("interpretar_aviso: reconoce silenciar/activar con o sin tema, dedupe de temas, y los de peligro los rechaza: " + str(malos), not malos)
no = ["", "hola", "avísame cuando termines de minar", "no me avises de nada", "avísame menos de lo normal", "no me avises de la política", "silencia", "vuelve a avisarme dentro de una hora", "no me avises de que hay muchos zombis" + "x" * 100,
      "¿me avisas del hambre?", "avisos", None, 5, "x" * 300]
r.check("los límites documentados: 40 notas, 200 caracteres por nota, 4 como mínimo", pf.MAX_NOTAS == 40 and pf.MAX_CHARS_NOTA == 200 and pf.MIN_CHARS_NOTA == 4)
r.check("interpretar_aviso: un mensaje de más de 100 caracteres no se procesa aunque normalizado sería válido ('no me avises del hambre' + 100 espacios); con 20 espacios sí",
        pf.interpretar_aviso("no me avises del hambre" + " " * 100) is None and pf.interpretar_aviso("no me avises del hambre" + " " * 20) == ("silenciar", ["hambre"]))
r.check("interpretar_aviso: NO se activa con otras frases, temas desconocidos ni mensajes largos: " + str([x for x in no if pf.interpretar_aviso(x)]), not any(pf.interpretar_aviso(x) for x in no))

casos_n = {
    "recuerda que prefiero construir con piedra": ("guardar", "prefiero construir con piedra"), "Cobalt, recuerda que mi base está en el desierto.": ("guardar", "mi base está en el desierto"),
    "acuérdate de que soy zurdo": ("guardar", "de que soy zurdo"), "anota que uso pico de diamante": ("guardar", "uso pico de diamante"), "ten en cuenta que no me gustan los creepers": ("guardar", "no me gustan los creepers"),
    "Recuerda que la granja está al norte!": ("guardar", "la granja está al norte"), "qué recuerdas de mí": ("listar", None), "¿Qué sabes de mí?": ("listar", None), "mis notas": ("listar", None),
    "olvida 2": ("olvidar", 2), "borra la nota 3": ("olvidar", 3), "olvida nota 10": ("olvidar", 10), "olvida todo lo que recuerdas de mí": ("olvidar_todo", None), "borra mis notas": ("olvidar_todo", None),
}
malos = {k: pf.interpretar_nota(k) for k, v in casos_n.items() if pf.interpretar_nota(k) != v}
r.check("interpretar_nota: guardar, listar, olvidar N y olvidar todo: " + str(malos), not malos)
no = ["", "hola", "recuerda", "recuerda que", "recuerda que sí", "¿recuerdas que prefiero piedra?", "recuerdas mi base", "recuerda que ¿qué?", "olvida", "olvida 2 y 3", "olvida todo", "borra", "recuerda que " + "a" * 500,
      None, 7, "x" * 500]
r.check("interpretar_nota: NO se activa con preguntas, frases incompletas, notas absurdamente largas ni con 'olvida' ambiguo: " + str([x for x in no if pf.interpretar_nota(x)]), not any(pf.interpretar_nota(x) for x in no))
acc, txt = pf.interpretar_nota('recuerda que {evil} [x] "comillas" `cmd` <b>hola</b> \\ fin')
r.check("una nota con llaves, corchetes, comillas, backticks o barras se sanea (sin esos caracteres): " + repr(txt), acc == "guardar" and not any(c in txt for c in '{}[]"`<>\\') and "evil" in txt and "fin" in txt)
r.check("saneado: una línea, sin control, con tope de largo", pf.saneado("a\nb\r\nc\td\x00e") == "a b c d e" and len(pf.saneado("x" * 500)) == pf.MAX_CHARS_NOTA and pf.saneado(None) == "" and pf.saneado("  ") == "")

p = pf.Perfil()
r.check("perfil vacío: nada silenciado ni anotado", p.silenciados == set() and p.notas == [] and p.a_dict() == {"silenciados": [], "notas": []})
p.silenciar(["hambre", "fuego", "aire", "peligro", "mundo"])
r.check("silenciar solo admite las categorías silenciables (fuego/aire/peligro no existen como opción)", p.silenciados == {"hambre", "mundo"})
p.activar(["mundo", "inventario", "otra"])
r.check("activar quita lo pedido y tolera lo que no estaba", p.silenciados == {"hambre"})
ok, t = p.agregar_nota("prefiero construir con piedra", 100.0)
r.check("agregar_nota: guarda con su hora", ok and t == "prefiero construir con piedra" and p.notas == [{"t": 100.0, "texto": "prefiero construir con piedra"}])
r.check("agregar_nota: la misma nota (aunque cambien mayúsculas) o casi igual NO se repite",
        p.agregar_nota("PREFIERO construir con piedra", 101.0)[0] is False and p.agregar_nota("prefiero construir con piedra siempre", 102.0)[0] is False and len(p.notas) == 1)
r.check("agregar_nota: una distinta sí; una demasiado corta o vacía no", p.agregar_nota("mi base está en el desierto", 103.0)[0] is True and p.agregar_nota("ok", 104.0)[0] is False and p.agregar_nota("", 105.0)[0] is False
        and p.agregar_nota(None, 106.0)[0] is False and len(p.notas) == 2)
q = pf.Perfil()
for i in range(pf.MAX_NOTAS + 10):
    q.agregar_nota(f"dato numero{i} sobre el jugador {'ab' * (i % 5)} particular{i}", float(i))
r.check(f"agregar_nota: como mucho {pf.MAX_NOTAS} notas; se tira la más antigua: {len(q.notas)}", len(q.notas) == pf.MAX_NOTAS and q.notas[0]["t"] == 10.0 and q.notas[-1]["t"] == float(pf.MAX_NOTAS + 9))
s = pf.Perfil(notas=[{"t": 1, "texto": "nota uno larga"}, {"t": 2, "texto": "nota dos larga"}, {"t": 3, "texto": "nota tres larga"}])
r.check("olvidar(n): quita la nota N (1 = primera), devuelve su texto y renumera", s.olvidar(2) == "nota dos larga" and [n["texto"] for n in s.notas] == ["nota uno larga", "nota tres larga"] and s.olvidar(2) == "nota tres larga")
r.check("olvidar: 0, fuera de rango, negativo, bool, texto o None -> None y no toca nada", all(s.olvidar(x) is None for x in (0, 5, -1, True, "1", None, 1.0)) and len(s.notas) == 1)
r.check("olvidar_todo devuelve cuántas había y deja vacío", s.olvidar_todo() == 1 and s.notas == [] and s.olvidar_todo() == 0)

d = {"silenciados": ["hambre", "fuego", 5, None, "mundo", "hambre"], "notas": [{"t": 5, "texto": "  una nota buena  "}, {"t": "x", "texto": "otra nota con tiempo raro"}, {"texto": 5}, "texto suelto", None, {"t": 1, "texto": "ab"},
                                                                          {"t": True, "texto": "nota con bool en t"}, {"t": float("nan"), "texto": "nota con nan en t"}, {"t": 2, "texto": "mala {llave} y\nsalto"}]}
c = pf.Perfil.desde_dict(d)
r.check("desde_dict: solo categorías conocidas (sin duplicados), notas válidas y saneadas, tiempo raro -> 0; lo demás se descarta: " + str([n["texto"] for n in c.notas]),
        c.silenciados == {"hambre", "mundo"} and [n["texto"] for n in c.notas] == ["una nota buena", "otra nota con tiempo raro", "nota con bool en t", "nota con nan en t", "mala llave y salto"]
        and [n["t"] for n in c.notas] == [5, 0, 0, 0, 2])
r.check("desde_dict: algo que no es un dict o con tipos raros -> perfil vacío", all(pf.Perfil.desde_dict(x).a_dict() == {"silenciados": [], "notas": []} for x in (None, [], "x", 5, {"silenciados": "x"}, {"notas": {"a": 1}})))
ida_vuelta = pf.Perfil.desde_dict(c.a_dict())
r.check("a_dict/desde_dict: ida y vuelta sin cambios y a_dict devuelve copias", ida_vuelta.a_dict() == c.a_dict() and c.a_dict()["notas"] is not c.notas and c.a_dict()["notas"][0] is not c.notas[0])
muchas = pf.Perfil.desde_dict({"notas": [{"t": i, "texto": f"nota número {i} de prueba"} for i in range(200)]})
r.check("desde_dict: un archivo con 200 notas se queda con las últimas " + str(pf.MAX_NOTAS), len(muchas.notas) == pf.MAX_NOTAS and muchas.notas[-1]["t"] == 199)

pn = pf.Perfil(notas=[{"t": 1, "texto": "prefiero construir con piedra y madera oscura"}, {"t": 2, "texto": "mi base está en el desierto al norte"}, {"t": 3, "texto": "no me gustan los creepers"},
                      {"t": 4, "texto": "uso siempre el pico de diamante"}])
r.check("bloque_notas: sin perfil, sin notas o algo que no es un perfil -> ''", pf.bloque_notas(pf.Perfil()) == "" and pf.bloque_notas(None) == "" and pf.bloque_notas("x") == "")
b = pf.bloque_notas(pn, "construye una casa de piedra")
r.check("bloque_notas: con una consulta, la nota RELEVANTE (piedra) va primero y luego las más recientes: " + repr(b.split(chr(10))[:2]), b.split("\n")[0] == "- prefiero construir con piedra y madera oscura" and b.split("\n")[1] == "- uso siempre el pico de diamante")
b0 = pf.bloque_notas(pn, "")
r.check("bloque_notas: sin consulta, las más recientes primero y todas caben", b0.split("\n") == ["- uso siempre el pico de diamante", "- no me gustan los creepers", "- mi base está en el desierto al norte", "- prefiero construir con piedra y madera oscura"])
r.check("bloque_notas: respeta k y max_chars sin cortar una nota por la mitad", len(pf.bloque_notas(pn, "", k=2).split("\n")) == 2 and all(len(l) <= 60 for l in pf.bloque_notas(pn, "", max_chars=60).split("\n")) and pf.bloque_notas(pn, "", max_chars=10) == ""
        and len(pf.bloque_notas(pn, "", max_chars=60)) <= 60)
r.check("bloque_notas: no repite una nota que ya salió por relevancia", len(set(pf.bloque_notas(pn, "piedra desierto creepers pico").split("\n"))) == len(pf.bloque_notas(pn, "piedra desierto creepers pico").split("\n")))

r.check("texto_notas: numeradas como 'olvida N'", pf.texto_notas(pf.Perfil(notas=[{"t": 1, "texto": "nota uno larga"}, {"t": 2, "texto": "nota dos larga"}])) == "1) nota uno larga; 2) nota dos larga")
largo = pf.Perfil(notas=[{"t": i, "texto": f"una nota de relleno número {i} bastante larga para llenar"} for i in range(20)])
tn = pf.texto_notas(largo, max_chars=120)
mostradas = tn.count(") ")
resto = int(tn.rsplit(" y ", 1)[1].split()[0])
r.check("texto_notas: si no caben todas, dice cuántas faltan (mostradas + faltan = 20) y no pasa del tope aprox.: " + tn, tn.endswith(" más") and mostradas + resto == 20 and len(tn) <= 140)
r.check("texto_notas: sin notas -> ''", pf.texto_notas(pf.Perfil()) == "")

rng = random.Random(4)
cosas = [None, True, 0, -1, 1e30, float("nan"), "x", "{}", "recuerda que hola mundo", "no me avises del hambre", [], {}, {"texto": "algo largo aquí", "t": 1}, [{"texto": "otra cosa larga"}], "\x00\n\t", "a" * 600]
fallos = []
for _ in range(4000):
    try:
        x = rng.choice(cosas)
        pf.interpretar_aviso(x)
        pf.interpretar_nota(x)
        pf.saneado(x)
        pr = pf.Perfil.desde_dict({"silenciados": rng.choice([[], cosas, "x", None]), "notas": rng.choice([[], cosas, {"a": 1}, None])} if rng.random() < 0.8 else rng.choice(cosas))
        pr.agregar_nota(rng.choice(cosas), rng.random())
        pr.olvidar(rng.choice(cosas))
        pr.silenciar(rng.choice([[], cosas]))
        pr.activar(rng.choice([[], cosas]))
        assert isinstance(pf.bloque_notas(pr, rng.choice(cosas)), str) and isinstance(pf.texto_notas(pr), str) and pr.a_dict() == pf.Perfil.desde_dict(pr.a_dict()).a_dict()
    except Exception as ex:  # noqa: BLE001
        fallos.append(repr(ex))
r.check("fuzz (4000 combinaciones basura): nunca lanza y el perfil sobrevive a guardar y cargar: " + str(fallos[:2]), not fallos)

r.terminar()
