package com.example.cobaltbot.util;

import java.util.List;

/** Decisiones PURAS (sin estado del juego) para poder probarlas sin abrir Minecraft (tools/pruebas/PruebasCombate.java). */
public final class NoxCombate {

    private NoxCombate() {}

    /** Lo que se sabe de un hostil para decidir a cuál atacar primero. */
    public record Candidato(double distancia, boolean atacaADistancia, double vidaPct,
                            boolean explosivo, boolean curandero, boolean jefe) {}

    static final double BONO_RANGO = 8.0D;          // esqueletos, brujas, blazes...: dañan desde lejos
    static final double BONO_VIDA_BAJA = 4.0D;      // rematar al que casi muere limpia la zona antes
    static final double BONO_EXPLOSIVO = 10.0D;     // un creeper cerca es lo más urgente
    static final double BONO_CURANDERO = 5.0D;      // las unidades de apoyo alargan el combate
    static final double BONO_JEFE = 6.0D;          // no se cambia de blanco a la ligera si hay un jefe
    static final double VIDA_BAJA_PCT = 30.0D;
    static final double DIST_EXPLOSIVO = 7.0D;

    public static double puntuacion(Candidato c) {
        double puntos = c.distancia();
        if (c.atacaADistancia()) puntos -= BONO_RANGO;
        if (c.vidaPct() <= VIDA_BAJA_PCT) puntos -= BONO_VIDA_BAJA;
        if (c.explosivo() && c.distancia() <= DIST_EXPLOSIVO) puntos -= BONO_EXPLOSIVO;
        if (c.curandero()) puntos -= BONO_CURANDERO;
        if (c.jefe()) puntos -= BONO_JEFE;
        return puntos;
    }

    public static int elegir(List<Candidato> candidatos) {
        int mejor = -1;
        double mejorPuntos = Double.MAX_VALUE;
        for (int i = 0; i < candidatos.size(); i++) {
            double puntos = puntuacion(candidatos.get(i));
            if (puntos < mejorPuntos) {
                mejorPuntos = puntos;
                mejor = i;
            }
        }
        return mejor;
    }

    public static boolean debeCuerpoACuerpo(double vidaMaxObjetivo, double vidaActualObjetivo, int hostilesCercanos,
                                            double vidaPropiaPct, boolean explosivo, boolean jefe) {
        if (jefe || explosivo || vidaPropiaPct < 60.0D || hostilesCercanos > 1) return false;
        return vidaMaxObjetivo <= 20.0D || vidaActualObjetivo <= 6.0D;
    }

    private static final double ACELERACION_PLASMA = 0.1D;   // AbstractHurtingProjectile: potencia por tick
    private static final double INERCIA_PLASMA = 0.95D;      // y factor de rozamiento por tick
    static final int MAX_TICKS_ANTICIPACION = 30;            // 1.5 s
    static final double MAX_ANTICIPACION = 10.0D;            // bloques de adelanto como máximo

    public static int ticksDeVuelo(double distancia) {
        double velocidad = 0.0D;
        double recorrido = 0.0D;
        for (int tick = 1; tick <= 200; tick++) {
            velocidad = (velocidad + ACELERACION_PLASMA) * INERCIA_PLASMA;
            recorrido += velocidad;
            if (recorrido >= distancia) return tick;
        }
        return 200;
    }

    public static double[] puntoDeApuntado(double sx, double sy, double sz, double tx, double ty, double tz,
                                           double velX, double velZ) {
        double ax = tx;
        double az = tz;
        for (int i = 0; i < 3; i++) {
            double dx = ax - sx, dy = ty - sy, dz = az - sz;
            int ticks = Math.min(MAX_TICKS_ANTICIPACION, ticksDeVuelo(Math.sqrt(dx * dx + dy * dy + dz * dz)));
            ax = tx + velX * ticks;
            az = tz + velZ * ticks;
        }
        double adelantoX = ax - tx;
        double adelantoZ = az - tz;
        double adelanto = Math.sqrt(adelantoX * adelantoX + adelantoZ * adelantoZ);
        if (adelanto > MAX_ANTICIPACION) {
            ax = tx + adelantoX / adelanto * MAX_ANTICIPACION;
            az = tz + adelantoZ / adelanto * MAX_ANTICIPACION;
        }
        return new double[]{ax, ty, az};
    }
}
