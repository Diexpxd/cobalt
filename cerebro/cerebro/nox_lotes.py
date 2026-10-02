"""Colocación por lotes (F2-3). PURO: sin red, sin Minecraft, sin disco."""
MAX_LOTE = 64
TAM_DEFECTO = 48
MOTIVOS_CONOCIDOS = ("no_material", "ocupado", "invalido", "bloque_invalido", "error")


def _entero(x):
    return isinstance(x, int) and not isinstance(x, bool)


def tam_valido(tam):
    """El tamaño de lote pedido, acotado a [1, MAX_LOTE]; lo que no sea un número da el de por defecto."""
    if isinstance(tam, bool) or not isinstance(tam, (int, float)) or tam != tam:
        return TAM_DEFECTO
    return max(1, min(MAX_LOTE, int(tam)))


def partir_en_lotes(elementos, tam=TAM_DEFECTO):
    """Lista -> lista de listas de como mucho 'tam' elementos, conservando el orden. Sin elementos -> []."""
    n = tam_valido(tam)
    lista = list(elementos) if isinstance(elementos, (list, tuple)) else []
    return [lista[i:i + n] for i in range(0, len(lista), n)]


def orden_lote(bloques):
    """La orden de Java para un lote. 'bloques' son dicts con x, y, z, block y opcionalmente state."""
    limpios = []
    for b in bloques:
        e = {"x": b["x"], "y": b["y"], "z": b["z"], "block": b["block"]}
        if b.get("state"):
            e["state"] = b["state"]
        limpios.append(e)
    return {"action": "place_blocks", "blocks": limpios, "movement_mode": "walk"}


def interpretar_resumen(data, enviados):
    """El resumen de Java -> {'colocados': [índices], 'fallos': {índice: motivo}} o None si no es fiable."""
    if not isinstance(data, dict) or not _entero(enviados) or enviados < 1:
        return None
    if data.get("status") not in ("success", "partial", "failed"):
        return None
    placed, total, lista = data.get("placed"), data.get("total"), data.get("failed")
    if not _entero(placed) or not _entero(total) or not isinstance(lista, list):
        return None
    if total != enviados or data.get("failed_more"):
        return None
    fallos = {}
    for f in lista:
        if not isinstance(f, dict) or not _entero(f.get("i")) or not 0 <= f["i"] < enviados or f["i"] in fallos:
            return None
        motivo = f.get("reason")
        fallos[f["i"]] = motivo if motivo in MOTIVOS_CONOCIDOS else "error"
    if placed + len(fallos) != total:
        return None
    if (data["status"] == "success") != (not fallos and placed == total):
        return None
    if data["status"] == "failed" and placed != 0:
        return None
    if data["status"] == "partial" and not 0 < placed < total:
        return None
    return {"colocados": [i for i in range(enviados) if i not in fallos], "fallos": fallos}


def agrupar_fallos(fallos, bloques):
    """({índice: motivo}, lista de bloques enviados) -> {'no_material': {'minecraft:stone': [índices]}, 'otros': [índices]}. Solo lo que falta de material se puede arreglar reabasteciendo."""
    sin_material, otros = {}, []
    for i, motivo in sorted(fallos.items()):
        if motivo == "no_material":
            sin_material.setdefault(bloques[i]["block"], []).append(i)
        else:
            otros.append(i)
    return {"no_material": sin_material, "otros": otros}
