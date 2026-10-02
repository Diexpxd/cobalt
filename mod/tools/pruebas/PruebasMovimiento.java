import com.example.cobaltbot.util.NoxMovimiento;

/** Reglas puras del movimiento de larga distancia (NoxMovimiento): tramos hacia un destino lejano, tiempo. */
public class PruebasMovimiento {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static double dist(double[] a, double x, double y, double z) {
        return Math.sqrt((a[0] - x) * (a[0] - x) + (a[1] - y) * (a[1] - y) + (a[2] - z) * (a[2] - z));
    }

    public static void main(String[] args) {
        // destino cercano: directo
        double[] p = NoxMovimiento.puntoIntermedio(0, 64, 0, 10, 64, 5, 24, false);
        check("destino a 11 bloques: va directo", p[0] == 10 && p[1] == 64 && p[2] == 5);
        p = NoxMovimiento.puntoIntermedio(0, 64, 0, 28, 64, 0, 24, false);
        check("destino justo en el umbral de tramos (28): directo", p[0] == 28);

        // destino lejano: tramo de 24 bloques rumbo al destino
        p = NoxMovimiento.puntoIntermedio(0, 64, 0, 200, 64, 0, 24, false);
        check("destino a 200 bloques: primer tramo a 24 bloques", Math.abs(p[0] - 24.0D) < 1e-9 && p[1] == 64 && p[2] == 0);
        p = NoxMovimiento.puntoIntermedio(0, 64, 0, 300, 64, 400, 24, false);
        check("el tramo apunta al destino (razón 3:4)", Math.abs(p[0] - 14.4D) < 1e-9 && Math.abs(p[2] - 19.2D) < 1e-9 && Math.abs(dist(p, 0, 64, 0) - 24.0D) < 1e-9);

        // a pie mantiene la altura; volando la interpola
        p = NoxMovimiento.puntoIntermedio(0, 64, 0, 100, 164, 0, 24, false);
        check("a pie: misma altura (el pathfinder resuelve el desnivel)", p[1] == 64);
        p = NoxMovimiento.puntoIntermedio(0, 64, 0, 100, 164, 0, 24, true);
        check("volando: la altura sube poco a poco hacia el destino", p[1] > 64 && p[1] < 164 && Math.abs(dist(p, 0, 64, 0) - 24.0D) < 1e-9);

        double x = 0, y = 64, z = 0;
        int pasos = 0;
        while (pasos < 200) {
            double[] q = NoxMovimiento.puntoIntermedio(x, y, z, 1000, 64, 0, 24, false);
            boolean llego = q[0] == 1000;
            x = q[0]; y = q[1]; z = q[2];
            pasos++;
            if (llego) break;
        }
        check("1000 bloques se recorren por tramos (menos de 45 pasos)", x == 1000 && pasos <= 45 && pasos >= 40);

        p = NoxMovimiento.puntoIntermedio(0, 0, 0, 100, 0, 0, 0, false);
        check("paso 0: directo", p[0] == 100);
        p = NoxMovimiento.puntoIntermedio(5, 5, 5, 5, 5, 5, 24, true);
        check("ya está en el destino: se queda", p[0] == 5 && p[1] == 5 && p[2] == 5);

        // tiempo concedido
        check("tiempo para 0 bloques = 30 s", NoxMovimiento.ticksParaLlegar(0) == 600);
        check("tiempo para 100 bloques = 30 s + 60 s", NoxMovimiento.ticksParaLlegar(100) == 1800);
        check("tiempo con tope de 5 min", NoxMovimiento.ticksParaLlegar(100000) == 6000);
        check("tiempo con distancia negativa o NaN no explota", NoxMovimiento.ticksParaLlegar(-5) == 600 && NoxMovimiento.ticksParaLlegar(Double.NaN) == 600);

        // detección de no acercarse
        check("acercarse 5 bloques no es 'sin acercarse'", !NoxMovimiento.sinAcercarse(50, 45, 1.5D));
        check("quedarse igual sí", NoxMovimiento.sinAcercarse(50, 50, 1.5D));
        check("acercarse menos que el margen sí (ruido)", NoxMovimiento.sinAcercarse(50, 49, 1.5D));
        check("alejarse sí", NoxMovimiento.sinAcercarse(50, 60, 1.5D));

        if (fallos > 0) {
            System.out.println("\nFALLOS: " + fallos);
            System.exit(1);
        }
        System.out.println("\nTODO OK");
    }
}
