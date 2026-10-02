package com.example.cobaltbot.util;

import com.google.gson.JsonObject;

/** Parámetros y utilidades PURAS del protocolo de jefe y del registro de encuentros. */
public final class NoxJefes {

    private NoxJefes() {}

    /** Distancias del kiting y qué armas se permiten. */
    public record ParametrosKiting(double retroceso, double ideal, double max, boolean permiteMelee, boolean permiteEmp) {}

    private static final ParametrosKiting NORMAL = new ParametrosKiting(9.0D, 12.0D, 16.0D, true, true);
    private static final ParametrosKiting JEFE = new ParametrosKiting(14.0D, 18.0D, 24.0D, false, false);

    private static final ParametrosKiting EXTREMO = new ParametrosKiting(20.0D, 26.0D, 34.0D, false, false);

    public static ParametrosKiting parametros(boolean modoJefe) {
        return modoJefe ? JEFE : NORMAL;
    }

    public static ParametrosKiting parametros(boolean modoJefe, boolean faseExtrema) {
        return modoJefe && faseExtrema ? EXTREMO : parametros(modoJefe);
    }

    public static double alturaEvasion(double alturaBase, long tick) {
        return alturaBase + 3.0D * Math.sin(tick * 0.12D);
    }

    public static boolean puedeRegistrar(long ahoraMs, long ultimoMs, long ventanaMs) {
        return ultimoMs <= 0L || ahoraMs - ultimoMs >= ventanaMs;
    }

    public static String jsonEncuentro(String nombre, String id, boolean esJefe, String motivo, long marcaMs) {
        JsonObject json = new JsonObject();
        json.addProperty("jefe", nombre);
        json.addProperty("id", id);
        json.addProperty("es_jefe", esJefe);
        json.addProperty("motivo", motivo);
        json.addProperty("ts", marcaMs);
        return json.toString();
    }

    public static double limitarAltura(double y, double ancla, double maxSobre, double maxBajo) {
        return Math.max(ancla - maxBajo, Math.min(ancla + maxSobre, y));
    }
}
