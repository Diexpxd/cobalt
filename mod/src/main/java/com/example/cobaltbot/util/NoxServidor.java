package com.example.cobaltbot.util;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/** Reglas PURAS, probadas sin Minecraft en tools/pruebas/PruebasServidor.java. */
public final class NoxServidor {

    private NoxServidor() {}

    public static final int MAX_TITULO = 32;
    public static final int MAX_PAGINAS = 40;
    public static final int MAX_CHARS_PAGINA = 250;
    public static final int COMBUSTIBLE_OBJETIVO = 8;
    public static final int ENTRADA_MAXIMA = 64;

    public static double tpsDesdeMspt(double mspt) {
        if (Double.isNaN(mspt) || Double.isInfinite(mspt) || mspt <= 0.0D) return 20.0D;
        return Math.min(20.0D, 1000.0D / mspt);
    }

    public record Libro(String titulo, List<String> paginas) {}

    private static String limpiar(String t) {
        if (t == null) return "";
        StringBuilder sb = new StringBuilder(t.length());
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            if (c == '\n' || (c >= 32 && c != 127)) sb.append(c); // sin caracteres de control (menos el salto de línea)
        }
        return sb.toString();
    }

    public static Libro limitarLibro(String titulo, List<String> paginas) {
        String t = limpiar(titulo).replace('\n', ' ').trim();
        if (t.length() > MAX_TITULO) t = t.substring(0, MAX_TITULO).trim();
        if (t.isEmpty()) t = "Crónica";
        List<String> limpias = new ArrayList<>();
        if (paginas != null) {
            for (String p : paginas) {
                String s = limpiar(p);
                if (s.length() > MAX_CHARS_PAGINA) s = s.substring(0, MAX_CHARS_PAGINA);
                if (s.isBlank()) continue;
                limpias.add(s);
                if (limpias.size() >= MAX_PAGINAS) break;
            }
        }
        return new Libro(t, limpias);
    }

    private static final Set<String> COMBUSTIBLES = Set.of("coal", "charcoal", "coal_block", "blaze_rod");

    public static boolean esCombustibleSeguro(String ruta) {
        return ruta != null && COMBUSTIBLES.contains(ruta);
    }

    private static final Set<String> COMIDA_CRUDA = Set.of("beef", "porkchop", "chicken", "mutton", "rabbit", "cod", "salmon", "potato", "kelp");

    public static boolean esFundible(String ruta) {
        if (ruta == null) return false;
        if (ruta.endsWith("_block")) return false;
        return ruta.startsWith("raw_") || ruta.endsWith("_ore") || ruta.equals("ancient_debris") || COMIDA_CRUDA.contains(ruta);
    }

    public static int cantidadAMeter(int enHorno, int limite, int disponible) {
        return Math.max(0, Math.min(disponible, limite - Math.max(0, enHorno)));
    }
}
