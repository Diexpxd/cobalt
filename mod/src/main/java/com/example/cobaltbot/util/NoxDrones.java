package com.example.cobaltbot.util;

/** ENJAMBRE DE DRONES: reglas PURAS (números, formación y reparto de objetivos) probadas sin Minecraft en tools/pruebas/PruebasDrones.java. */
public final class NoxDrones {

    private NoxDrones() {}

    public static final int CANTIDAD = 5;
    public static final int DURACION_S = 60;
    public static final int COOLDOWN_S = 240;
    public static final int DANO_PCT = 40;

    private static double acotar(double valor, double minimo, double maximo) {
        if (Double.isNaN(valor)) return minimo;
        return Math.max(minimo, Math.min(maximo, valor));
    }

    public static int cantidad(double valor) {
        return (int) Math.round(acotar(valor, 1.0D, 8.0D));
    }

    public static int duracionTicks(double segundos) {
        return (int) Math.round(acotar(segundos, 5.0D, 300.0D)) * 20;
    }

    public static int cooldownTicks(double segundos) {
        return (int) Math.round(acotar(segundos, 10.0D, 3600.0D)) * 20;
    }

    public static float escalaDano(double porcentaje) {
        return (float) (acotar(porcentaje, 5.0D, 200.0D) / 100.0D);
    }

    public static int segundosRestantes(int ticks) {
        return ticks <= 0 ? 0 : (int) Math.ceil(ticks / 20.0D);
    }

    public static double[] posicionEnAnillo(int indice, int total, long tick, double radio, double altura) {
        int n = Math.max(1, total);
        double angulo = 2.0D * Math.PI * indice / n + tick * 0.04D;
        double flotar = 0.4D * Math.sin(tick * 0.1D + indice);
        return new double[]{Math.cos(angulo) * radio, altura + flotar, Math.sin(angulo) * radio};
    }

    public static int elegirCandidato(int indice, int candidatos, boolean prioridadDueno) {
        if (candidatos <= 0) return -1;
        if (!prioridadDueno) return indice % candidatos;
        if (indice % 2 == 0 || candidatos == 1) return 0;
        return 1 + ((indice / 2) % (candidatos - 1));
    }

    public static double velocidadHacia(double distancia) {
        if (distancia < 0.3D) return 0.0D;
        return Math.min(0.45D, distancia * 0.2D);
    }
}
