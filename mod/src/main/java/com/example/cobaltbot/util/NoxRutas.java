package com.example.cobaltbot.util;

import java.io.File;

/** Carpeta de intercambio entre el mod y el cerebro de Python (command.json, gps.json, waypoints.json...). */
public final class NoxRutas {
    public static final String POR_DEFECTO = System.getProperty("user.home") + File.separator + "cobalt";

    private NoxRutas() {}

    public static File dir() {
        String p = System.getProperty("cobalt.dir");
        if (p == null || p.isBlank()) p = System.getenv("COBALT_DIR");
        return new File(p == null || p.isBlank() ? POR_DEFECTO : p.trim());
    }

    public static File archivo(String nombre) {
        return new File(dir(), nombre);
    }
}
