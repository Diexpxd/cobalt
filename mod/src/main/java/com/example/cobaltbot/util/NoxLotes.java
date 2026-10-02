package com.example.cobaltbot.util;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonPrimitive;

import java.util.ArrayList;
import java.util.List;

/** Colocación por LOTES: Python manda hasta MAX_LOTE bloques en una sola orden ("place_blocks") y Java responde. */
public final class NoxLotes {
    public static final int MAX_LOTE = 64;
    public static final int MAX_FALLOS = 64;
    public static final int MAX_TEXTO = 300;

    private NoxLotes() {}

    public record Bloque(int i, int x, int y, int z, String block, String state) {}

    public record Fallo(int i, String motivo) {}

    /** Total = cuántos elementos se miran (máximo MAX_LOTE); ignorados = los que sobran; bloques = los válidos. */
    public record Parseado(int total, int ignorados, List<Bloque> bloques, List<Fallo> fallos) {}

    private static Integer entero(JsonObject o, String clave) {
        JsonElement e = o.get(clave);
        if (e == null || !e.isJsonPrimitive()) return null;
        JsonPrimitive p = e.getAsJsonPrimitive();
        if (!p.isNumber()) return null;
        double d = p.getAsDouble();
        if (Double.isNaN(d) || Double.isInfinite(d) || d != Math.rint(d) || Math.abs(d) > 3.0E7D) return null; // coordenadas de Minecraft: enteros dentro del mundo
        return (int) d;
    }

    private static String texto(JsonObject o, String clave) {
        JsonElement e = o.get(clave);
        if (e == null || !e.isJsonPrimitive() || !e.getAsJsonPrimitive().isString()) return "";
        String s = e.getAsString().strip();
        return s.length() <= MAX_TEXTO ? s : "";
    }

    public static Parseado parsear(JsonElement blocks) {
        List<Bloque> validos = new ArrayList<>();
        List<Fallo> fallos = new ArrayList<>();
        if (blocks == null || !blocks.isJsonArray()) return new Parseado(0, 0, validos, fallos);
        JsonArray arr = blocks.getAsJsonArray();
        int total = Math.min(arr.size(), MAX_LOTE);
        for (int i = 0; i < total; i++) {
            JsonElement el = arr.get(i);
            if (el == null || !el.isJsonObject()) { fallos.add(new Fallo(i, "invalido")); continue; }
            JsonObject o = el.getAsJsonObject();
            Integer x = entero(o, "x"), y = entero(o, "y"), z = entero(o, "z");
            String bloque = texto(o, "block");
            if (x == null || y == null || z == null || bloque.isEmpty()) { fallos.add(new Fallo(i, "invalido")); continue; }
            validos.add(new Bloque(i, x, y, z, bloque, texto(o, "state")));
        }
        return new Parseado(total, arr.size() - total, validos, fallos);
    }

    public static String resumen(int total, int colocados, List<Fallo> fallos, int ignorados) {
        JsonObject raiz = new JsonObject();
        int c = Math.max(0, Math.min(colocados, total));
        raiz.addProperty("status", total > 0 && c == total ? "success" : c == 0 ? "failed" : "partial");
        raiz.addProperty("placed", c);
        raiz.addProperty("total", total);
        JsonArray lista = new JsonArray();
        int mostrados = 0;
        if (fallos != null) {
            for (Fallo f : fallos) {
                if (f == null) continue;
                if (mostrados >= MAX_FALLOS) break;
                JsonObject o = new JsonObject();
                o.addProperty("i", f.i());
                o.addProperty("reason", f.motivo() == null || f.motivo().isBlank() ? "error" : f.motivo());
                lista.add(o);
                mostrados++;
            }
        }
        raiz.add("failed", lista);
        int totalFallos = fallos == null ? 0 : (int) fallos.stream().filter(f -> f != null).count();
        if (totalFallos > mostrados) raiz.addProperty("failed_more", totalFallos - mostrados);
        if (ignorados > 0) raiz.addProperty("ignored", ignorados);
        return raiz.toString();
    }
}
