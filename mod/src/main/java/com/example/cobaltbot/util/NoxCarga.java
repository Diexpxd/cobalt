package com.example.cobaltbot.util;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Qué chunks mantiene cargados Cobalt (su "chunk loader" personal). */
public final class NoxCarga {
    private NoxCarga() {}

    public static final int RADIO_MAX = 3;
    public static final int ADELANTE_MAX = 8;
    public static final int TOPE_POR_DEFECTO = 30;

    private static int limitar(int valor, int min, int max) {
        return Math.max(min, Math.min(max, valor));
    }

    public static List<int[]> chunks(int cx, int cz, int radio, boolean trabajoLejos, int radioTrabajo, double dirX, double dirZ, int adelante, int tope) {
        int r = limitar(radio, 0, RADIO_MAX);
        if (trabajoLejos) r = Math.max(r, limitar(radioTrabajo, 0, RADIO_MAX));
        List<int[]> lista = new ArrayList<>();
        for (int dx = -r; dx <= r; dx++) for (int dz = -r; dz <= r; dz++) lista.add(new int[] {cx + dx, cz + dz});
        lista.sort(Comparator.comparingInt((int[] c) -> (c[0] - cx) * (c[0] - cx) + (c[1] - cz) * (c[1] - cz)));

        double largo = Math.sqrt(dirX * dirX + dirZ * dirZ);
        int pasos = limitar(adelante, 0, ADELANTE_MAX);
        if (pasos > 0 && largo > 1.0E-6D) {
            double ux = dirX / largo, uz = dirZ / largo;
            Set<Long> ya = new HashSet<>();
            for (int[] c : lista) ya.add(clave(c[0], c[1]));
            for (int k = 1; k <= pasos; k++) {
                int x = cx + (int) Math.round(ux * (r + k)), z = cz + (int) Math.round(uz * (r + k));
                if (ya.add(clave(x, z))) lista.add(new int[] {x, z});
            }
        }
        int maximo = Math.max(1, tope);
        return lista.size() > maximo ? new ArrayList<>(lista.subList(0, maximo)) : lista;
    }

    private static long clave(int x, int z) {
        return ((long) x << 32) ^ (z & 0xFFFFFFFFL);
    }
}
