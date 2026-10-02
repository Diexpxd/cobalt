import com.example.cobaltbot.util.NoxDrones;

/** Pruebas del enjambre de drones: números por defecto, límites de configuración, formación y reparto de objetivos. */
public class PruebasDrones {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static boolean casi(double a, double b) {
        return Math.abs(a - b) < 1e-9;
    }

    public static void main(String[] args) {
        check("por defecto: 5 drones, 60 s de apoyo y 4 minutos (240 s) de enfriamiento",
                NoxDrones.CANTIDAD == 5 && NoxDrones.DURACION_S == 60 && NoxDrones.COOLDOWN_S == 240);
        check("60 s son 1200 ticks y 240 s son 4800 ticks", NoxDrones.duracionTicks(NoxDrones.DURACION_S) == 1200 && NoxDrones.cooldownTicks(NoxDrones.COOLDOWN_S) == 4800);
        check("cantidad por defecto = 5", NoxDrones.cantidad(NoxDrones.CANTIDAD) == 5);
        check("daño por defecto = 40 % del plasma normal", Math.abs(NoxDrones.escalaDano(NoxDrones.DANO_PCT) - 0.4F) < 1e-6F);

        check("cantidad: 0 y negativos -> 1; 99 -> 8; 3.6 -> 4; NaN -> 1", NoxDrones.cantidad(0) == 1 && NoxDrones.cantidad(-7) == 1 && NoxDrones.cantidad(99) == 8
                && NoxDrones.cantidad(3.6) == 4 && NoxDrones.cantidad(Double.NaN) == 1);
        check("duración: mínimo 5 s, máximo 5 min", NoxDrones.duracionTicks(0) == 100 && NoxDrones.duracionTicks(100000) == 6000 && NoxDrones.duracionTicks(30) == 600);
        check("enfriamiento: mínimo 10 s, máximo 1 h", NoxDrones.cooldownTicks(0) == 200 && NoxDrones.cooldownTicks(999999) == 72000 && NoxDrones.cooldownTicks(120) == 2400);
        check("daño: 5 % a 200 %", NoxDrones.escalaDano(0) == 0.05F && NoxDrones.escalaDano(1000) == 2.0F && NoxDrones.escalaDano(100) == 1.0F);
        check("segundos restantes: redondea hacia arriba y nunca es negativo", NoxDrones.segundosRestantes(1) == 1 && NoxDrones.segundosRestantes(20) == 1 && NoxDrones.segundosRestantes(21) == 2
                && NoxDrones.segundosRestantes(4800) == 240 && NoxDrones.segundosRestantes(0) == 0 && NoxDrones.segundosRestantes(-50) == 0);

        double radio = 7.0;
        boolean todosAlRadio = true;
        for (int i = 0; i < 5; i++) {
            double[] p = NoxDrones.posicionEnAnillo(i, 5, 137L, radio, 3.0);
            todosAlRadio &= casi(Math.hypot(p[0], p[2]), radio);
        }
        check("anillo: los 5 drones están exactamente a 'radio' del centro (en el plano horizontal)", todosAlRadio);
        double[] p0 = NoxDrones.posicionEnAnillo(0, 5, 0L, radio, 3.0), p1 = NoxDrones.posicionEnAnillo(1, 5, 0L, radio, 3.0);
        double angulo = Math.acos((p0[0] * p1[0] + p0[2] * p1[2]) / (radio * radio));
        check("anillo: dos drones contiguos están separados 72 grados (360/5)", casi(Math.toDegrees(angulo), 72.0));
        double[] antes = NoxDrones.posicionEnAnillo(2, 5, 0L, radio, 3.0), despues = NoxDrones.posicionEnAnillo(2, 5, 100L, radio, 3.0);
        check("anillo: con el tiempo el enjambre GIRA (el mismo dron cambia de sitio)", Math.hypot(antes[0] - despues[0], antes[2] - despues[2]) > 1.0);
        boolean altura = true;
        for (long t = 0; t < 300; t += 7) {
            double dy = NoxDrones.posicionEnAnillo(3, 5, t, radio, 3.0)[1];
            altura &= dy >= 3.0 - 0.4 - 1e-9 && dy <= 3.0 + 0.4 + 1e-9;
        }
        check("anillo: la altura flota solo +-0,4 bloques alrededor de la altura pedida", altura);
        check("anillo: total 0 o negativo no da NaN ni divide por cero", !Double.isNaN(NoxDrones.posicionEnAnillo(0, 0, 5L, 3.0, 1.0)[0]) && !Double.isNaN(NoxDrones.posicionEnAnillo(2, -3, 5L, 3.0, 1.0)[2]));
        boolean distintos = true;
        for (int i = 0; i < 5; i++) {
            for (int j = i + 1; j < 5; j++) {
                double[] a = NoxDrones.posicionEnAnillo(i, 5, 0L, radio, 3.0), b = NoxDrones.posicionEnAnillo(j, 5, 0L, radio, 3.0);
                distintos &= Math.hypot(a[0] - b[0], a[2] - b[2]) > 1.0;
            }
        }
        check("anillo: ningún par de drones ocupa el mismo sitio", distintos);

        int[] conPrioridad = new int[5], sinPrioridad = new int[5];
        for (int i = 0; i < 5; i++) {
            conPrioridad[i] = NoxDrones.elegirCandidato(i, 3, true);
            sinPrioridad[i] = NoxDrones.elegirCandidato(i, 3, false);
        }
        check("reparto con objetivo de Cobalt y 3 enemigos: los drones pares (3 de 5) lo focalizan y los impares se reparten el resto -> [0,1,0,2,0]",
                java.util.Arrays.equals(conPrioridad, new int[]{0, 1, 0, 2, 0}));
        check("reparto sin objetivo de Cobalt: por turnos entre 3 enemigos -> [0,1,2,0,1]", java.util.Arrays.equals(sinPrioridad, new int[]{0, 1, 2, 0, 1}));
        boolean unico = true, ninguno = true;
        for (int i = 0; i < 5; i++) {
            unico &= NoxDrones.elegirCandidato(i, 1, true) == 0 && NoxDrones.elegirCandidato(i, 1, false) == 0;
            ninguno &= NoxDrones.elegirCandidato(i, 0, true) == -1 && NoxDrones.elegirCandidato(i, 0, false) == -1;
        }
        check("reparto: con un solo enemigo todos lo atacan; sin enemigos devuelve -1", unico && ninguno);
        boolean enRango = true;
        for (int candidatos = 1; candidatos <= 9; candidatos++) {
            for (int i = 0; i < 8; i++) {
                int a = NoxDrones.elegirCandidato(i, candidatos, true), b = NoxDrones.elegirCandidato(i, candidatos, false);
                enRango &= a >= 0 && a < candidatos && b >= 0 && b < candidatos;
            }
        }
        check("reparto: el índice devuelto SIEMPRE cae dentro de la lista (1-9 enemigos, 8 drones)", enRango);

        check("velocidad: se para a menos de 0,3, frena al acercarse (proporcional) y tiene tope 0,45",
                NoxDrones.velocidadHacia(0.1) == 0.0 && casi(NoxDrones.velocidadHacia(1.0), 0.2) && NoxDrones.velocidadHacia(50.0) == 0.45
                        && NoxDrones.velocidadHacia(2.0) < NoxDrones.velocidadHacia(5.0));

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
