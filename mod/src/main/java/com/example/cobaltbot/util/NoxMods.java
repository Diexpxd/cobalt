package com.example.cobaltbot.util;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

import java.util.List;

/** H6: la lista de mods cargados, en JSON, para que Python sepa con qué mods se está jugando (diagnóstico y, más. */
public final class NoxMods {
    public static final int MAX_MODS = 2000;
    public static final int MAX_TEXTO = 64;

    private NoxMods() {}

    private static String limpio(String s) {
        if (s == null) return "";
        String t = s.strip();
        return t.length() <= MAX_TEXTO ? t : t.substring(0, MAX_TEXTO);
    }

    public static String aJson(String minecraft, List<String[]> mods) {
        JsonObject raiz = new JsonObject();
        raiz.addProperty("minecraft", limpio(minecraft));
        JsonArray lista = new JsonArray();
        int total = 0;
        if (mods != null) {
            for (String[] par : mods) {
                if (par == null || par.length == 0) continue;
                String id = limpio(par[0]);
                if (id.isEmpty()) continue;
                total++;
                if (lista.size() >= MAX_MODS) continue; // se sigue contando para 'count', pero no se listan más
                JsonObject m = new JsonObject();
                m.addProperty("id", id);
                m.addProperty("version", par.length > 1 ? limpio(par[1]) : "");
                lista.add(m);
            }
        }
        raiz.addProperty("count", total);
        raiz.add("mods", lista);
        return raiz.toString();
    }
}
