"""Auxiliar de pruebas: extrae, por análisis estático (AST), las frases que el código le DICE al jugador (no los prompts para el modelo ni los logs)."""
import ast
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVOS = ["cerebro.py", "nox_pro.py", "nox_proteccion.py", "nox_inventario.py", "nox_social.py", "nox_mision.py", "nox_servidor.py", "nox_enjambre.py", "nox_obra.py", "nox_mundo.py"]
CLAVES = {"chat_message", "mensaje_alerta"}
VARIABLES = {"respuesta_nox", "texto_fin", "msg_respuesta", "chat"}


def _cadenas(nodo):
    salida = []

    def visitar(n):
        if isinstance(n, ast.JoinedStr):
            salida.append("".join(v.value if isinstance(v, ast.Constant) else "x" for v in n.values))
            return
        if isinstance(n, ast.Constant):
            if isinstance(n.value, str):
                salida.append(n.value)
            return
        if isinstance(n, ast.Call) and ((isinstance(n.func, ast.Name) and n.func.id == "frase") or (isinstance(n.func, ast.Attribute) and n.func.attr == "frase")):
            return  # las frases del banco de voz ya están comprobadas por sus propias pruebas
        for hijo in ast.iter_child_nodes(n):
            visitar(hijo)

    visitar(nodo)
    return salida


def frases(archivo):
    ruta = os.path.join(RAIZ, "cerebro", archivo)
    arbol = ast.parse(open(ruta, encoding="utf-8").read())
    encontradas = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value in CLAVES:
                    encontradas += [(n.lineno, s) for s in _cadenas(v)]
        elif isinstance(n, ast.Call):
            nombre = n.func.id if isinstance(n.func, ast.Name) else (n.func.attr if isinstance(n.func, ast.Attribute) else "")
            if nombre == "orden":
                if len(n.args) >= 2:
                    encontradas += [(n.lineno, s) for s in _cadenas(n.args[1])]
                for kw in n.keywords:
                    if kw.arg == "chat":
                        encontradas += [(n.lineno, s) for s in _cadenas(kw.value)]
            elif nombre == "append" and isinstance(n.func.value, ast.Name) and n.func.value.id == "avisos" and n.args:
                encontradas += [(n.lineno, s) for s in _cadenas(n.args[0])]
            elif nombre == "get" and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value in CLAVES and len(n.args) > 1:
                encontradas += [(n.lineno, s) for s in _cadenas(n.args[1])]
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id in VARIABLES:
                    encontradas += [(n.lineno, s) for s in _cadenas(n.value)]
                elif isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value in CLAVES:
                    encontradas += [(n.lineno, s) for s in _cadenas(n.value)]
    return sorted(set(encontradas))


def todas():
    return [(a, ln, s) for a in ARCHIVOS for ln, s in frases(a)]
