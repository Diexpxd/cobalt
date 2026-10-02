import com.example.cobaltbot.util.NoxCombate;
import com.example.cobaltbot.util.NoxCombate.Candidato;

import java.util.List;

/** Pruebas del Bloque C (combate avanzado): decisiones puras, sin abrir Minecraft. */
public class PruebasCombate {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static Candidato zombi(double d) { return new Candidato(d, false, 100, false, false, false); }

    public static void main(String[] a) {
        check("lista vacía -> -1", NoxCombate.elegir(List.of()) == -1);
        check("un solo candidato -> 0", NoxCombate.elegir(List.of(zombi(20))) == 0);
        check("empate: gana el primero (el más cercano)", NoxCombate.elegir(List.of(zombi(5), zombi(5))) == 0);
        check("sin bonificaciones gana el más cercano", NoxCombate.elegir(List.of(zombi(9), zombi(4), zombi(7))) == 1);

        check("esqueleto a 10 m antes que un zombi a 6 m (los de rango primero)",
                NoxCombate.elegir(List.of(zombi(6), new Candidato(10, true, 100, false, false, false))) == 1);
        check("esqueleto a 15 m NO supera a un zombi a 6 m (demasiado lejos para compensar)",
                NoxCombate.elegir(List.of(zombi(6), new Candidato(15, true, 100, false, false, false))) == 0);
        check("zombi con 20% de vida a 8 m antes que uno sano a 6 m (rematar)",
                NoxCombate.elegir(List.of(zombi(6), new Candidato(8, false, 20, false, false, false))) == 1);
        check("creeper a 5 m antes que un zombi a 3 m (explosivo cerca)",
                NoxCombate.elegir(List.of(zombi(3), new Candidato(5, false, 100, true, false, false))) == 1);
        check("creeper a 12 m NO tiene prioridad (aún no es urgente)",
                NoxCombate.elegir(List.of(zombi(3), new Candidato(12, false, 100, true, false, false))) == 0);
        check("bruja (curandera) a 10 m antes que un zombi a 6 m",
                NoxCombate.elegir(List.of(zombi(6), new Candidato(10, false, 100, false, true, false))) == 1);
        check("jefe a 10 m antes que un zombi a 6 m (no se cambia de blanco a la ligera)",
                NoxCombate.elegir(List.of(zombi(6), new Candidato(10, false, 100, false, false, true))) == 1);
        check("las bonificaciones se acumulan: esqueleto herido a 12 m gana a un zombi a 6 m",
                NoxCombate.elegir(List.of(zombi(6), new Candidato(12, true, 20, false, false, false))) == 1);

        check("zombi solitario (20 vida), Cobalt sano -> melee", NoxCombate.debeCuerpoACuerpo(20, 20, 1, 100, false, false));
        check("dos hostiles cerca -> kiting", !NoxCombate.debeCuerpoACuerpo(20, 20, 2, 100, false, false));
        check("Cobalt con 50% de vida -> kiting", !NoxCombate.debeCuerpoACuerpo(20, 20, 1, 50, false, false));
        check("Cobalt con exactamente 60% -> melee permitido", NoxCombate.debeCuerpoACuerpo(20, 20, 1, 60, false, false));
        check("creeper solitario -> NUNCA melee (explota)", !NoxCombate.debeCuerpoACuerpo(20, 20, 1, 100, true, false));
        check("jefe solitario -> NUNCA melee", !NoxCombate.debeCuerpoACuerpo(20, 3, 1, 100, false, true));
        check("enemigo fuerte (40 vida) y sano -> kiting", !NoxCombate.debeCuerpoACuerpo(40, 40, 1, 100, false, false));
        check("enemigo fuerte pero casi muerto (5 de vida) -> melee para rematar", NoxCombate.debeCuerpoACuerpo(40, 5, 1, 100, false, false));
        check("sin hostiles contados (0) y débil -> melee", NoxCombate.debeCuerpoACuerpo(16, 16, 0, 100, false, false));

        int t2 = NoxCombate.ticksDeVuelo(2), t12 = NoxCombate.ticksDeVuelo(12), t24 = NoxCombate.ticksDeVuelo(24);
        System.out.println("     (ticks de vuelo: 2 m -> " + t2 + ", 12 m -> " + t12 + ", 24 m -> " + t24 + ")");
        check("el tiempo de vuelo crece con la distancia", t2 < t12 && t12 < t24);
        check("distancia 0 -> 1 tick", NoxCombate.ticksDeVuelo(0) == 1);
        check("a 12 m tarda entre 6 y 20 ticks (plausible para 'fireball')", t12 >= 6 && t12 <= 20);
        check("distancia absurda -> tope de 200 ticks (sin bucle infinito)", NoxCombate.ticksDeVuelo(1.0e9) == 200);

        double[] p = NoxCombate.puntoDeApuntado(0, 65, 0, 20, 65, 0, 0, 0);
        check("blanco quieto -> se apunta a su posición exacta", p[0] == 20 && p[1] == 65 && p[2] == 0);

        p = NoxCombate.puntoDeApuntado(0, 65, 0, 20, 65, 0, 0, 0.2);
        System.out.println("     (blanco a 20 m moviéndose +Z a 0.2/tick -> apunta a z=" + String.format("%.2f", p[2]) + ")");
        check("blanco que se mueve en +Z: se adelanta en +Z", p[2] > 0.5 && p[2] <= 10.0);
        check("...sin desviar X (no se movía en X) ni la altura", Math.abs(p[0] - 20) < 1e-9 && p[1] == 65);

        p = NoxCombate.puntoDeApuntado(0, 65, 0, 20, 65, 0, -0.2, 0);
        check("blanco que se ACERCA (vx<0): apunta más cerca del tirador que su posición actual", p[0] < 20);

        p = NoxCombate.puntoDeApuntado(0, 65, 0, 20, 65, 0, 5.0, 0);
        check("blanco velocísimo (5/tick): el adelanto se limita a 10 bloques", Math.abs((p[0] - 20) - 10.0) < 1e-6);

        p = NoxCombate.puntoDeApuntado(0, 65, 0, 20, 65, 0, 3.0, 4.0);
        check("el límite de 10 bloques conserva la DIRECCIÓN (3:4)", Math.abs((p[0] - 20) / (p[2]) - 0.75) < 1e-6 && Math.abs(Math.hypot(p[0] - 20, p[2]) - 10.0) < 1e-6);

        p = NoxCombate.puntoDeApuntado(5, 65, 5, 5, 65, 5, 0.3, 0.3);
        check("blanco justo encima del tirador (distancia 0) no produce NaN", !Double.isNaN(p[0]) && !Double.isNaN(p[2]));

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
