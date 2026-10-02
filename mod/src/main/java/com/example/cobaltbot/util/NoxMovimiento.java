package com.example.cobaltbot.util;

/** Reglas PURAS del movimiento de larga distancia (probadas sin Minecraft en tools/pruebas/PruebasMovimiento.java). */
public final class NoxMovimiento {
    private NoxMovimiento() {}

    public static final double PASO_MAX = 24.0D;
    public static final double DIST_TRAMOS = 28.0D;

    public static double[] puntoIntermedio(double px, double py, double pz, double dx, double dy, double dz, double paso, boolean volando) {
        double vx = dx - px, vy = dy - py, vz = dz - pz;
        double dist = Math.sqrt(vx * vx + vy * vy + vz * vz);
        if (dist <= DIST_TRAMOS || dist <= paso || paso <= 0.0D) return new double[] {dx, dy, dz};
        double k = paso / dist;
        return new double[] {px + vx * k, volando ? py + vy * k : py, pz + vz * k};
    }

    public static int ticksParaLlegar(double distancia) {
        double d = Double.isNaN(distancia) || distancia < 0.0D ? 0.0D : distancia;
        return (int) Math.min(6000.0D, 600.0D + d * 12.0D);
    }

    public static boolean sinAcercarse(double mejor, double actual, double margen) {
        return actual >= mejor - margen;
    }
}
