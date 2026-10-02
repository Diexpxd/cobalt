import com.example.cobaltbot.util.NoxCarga;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Reglas puras del chunk loader de Cobalt (NoxCarga): anillo, anillo de trabajo, chunks por delante y tope. */
public class PruebasCarga {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static Set<String> conjunto(List<int[]> l) {
        Set<String> s = new HashSet<>();
        for (int[] c : l) s.add(c[0] + "," + c[1]);
        return s;
    }

    public static void main(String[] args) {
        List<int[]> l = NoxCarga.chunks(10, 20, 1, false, 2, 0, 0, 3, 30);
        check("radio 1 quieto: 9 chunks (3x3)", l.size() == 9 && conjunto(l).size() == 9);
        check("el chunk de Cobalt va el primero", l.get(0)[0] == 10 && l.get(0)[1] == 20);
        check("y contiene las 8 casillas de alrededor", conjunto(l).contains("9,19") && conjunto(l).contains("11,21") && conjunto(l).contains("10,19"));
        check("radio 0: solo el suyo", NoxCarga.chunks(10, 20, 0, false, 2, 0, 0, 3, 30).size() == 1);
        check("radio 2: 25 chunks", NoxCarga.chunks(10, 20, 2, false, 2, 0, 0, 3, 30).size() == 25);
        check("trabajando lejos con radio de trabajo 2: 5x5 (25)", NoxCarga.chunks(10, 20, 1, true, 2, 0, 0, 3, 30).size() == 25);
        check("trabajando lejos NUNCA reduce un radio normal mayor que el de trabajo", NoxCarga.chunks(10, 20, 3, true, 2, 0, 0, 0, 100).size() == 49);
        check("un radio de trabajo absurdo (99) tambien se limita a 3 (49)", NoxCarga.chunks(0, 0, 1, true, 99, 0, 0, 0, 1000).size() == 49);
        check("radio absurdo (99) se limita a 3 (7x7 = 49)", NoxCarga.chunks(0, 0, 99, false, 2, 0, 0, 0, 100).size() == 49);
        check("radio negativo = solo el suyo", NoxCarga.chunks(0, 0, -5, false, 2, 0, 0, 0, 100).size() == 1);

        // por delante
        l = NoxCarga.chunks(10, 20, 1, false, 2, 1, 0, 3, 30);
        Set<String> s = conjunto(l);
        check("yendo al este (radio 1, 3 por delante): 9 + 3 chunks en línea (12,20)(13,20)(14,20)", l.size() == 12 && s.contains("12,20") && s.contains("13,20") && s.contains("14,20"));
        check("y ninguno más allá ni por detrás", !s.contains("15,20") && !s.contains("7,20"));
        l = NoxCarga.chunks(10, 20, 1, false, 2, 0, -50, 2, 30);
        s = conjunto(l);
        check("yendo al norte (z decrece) carga (10,18)(10,17)", s.contains("10,18") && s.contains("10,17") && l.size() == 11);
        l = NoxCarga.chunks(10, 20, 1, false, 2, 30, 30, 3, 30);
        check("en diagonal los chunks de delante avanzan en ambos ejes y no se repiten", conjunto(l).size() == l.size() && conjunto(l).contains("12,22") && l.size() > 9);
        check("la dirección no hace falta normalizarla (1 o 1000 dan lo mismo)", conjunto(NoxCarga.chunks(10, 20, 1, false, 2, 1, 0, 3, 30)).equals(conjunto(NoxCarga.chunks(10, 20, 1, false, 2, 1000, 0, 3, 30))));
        check("quieto (dirección 0,0) no carga nada por delante", NoxCarga.chunks(10, 20, 1, false, 2, 0, 0, 5, 30).size() == 9);
        check("con adelante 0 tampoco", NoxCarga.chunks(10, 20, 1, false, 2, 1, 0, 0, 30).size() == 9);
        check("adelante se limita a 8", NoxCarga.chunks(0, 0, 0, false, 2, 1, 0, 100, 100).size() == 1 + NoxCarga.ADELANTE_MAX);
        check("adelante negativo = 0", NoxCarga.chunks(0, 0, 1, false, 2, 1, 0, -3, 100).size() == 9);
        Set<String> t = conjunto(NoxCarga.chunks(10, 20, 1, true, 2, 1, 0, 3, 100));
        check("con el anillo de trabajo (5x5) la línea empieza pasado el anillo: (13,20)(14,20)(15,20) y no (16,20)", t.contains("13,20") && t.contains("15,20") && !t.contains("16,20") && t.size() == 28);

        // tope
        l = NoxCarga.chunks(10, 20, 3, false, 2, 1, 0, 5, 30);
        check("el tope recorta a 30 chunks", l.size() == 30);
        check("y el recorte deja el suyo dentro (va primero)", l.get(0)[0] == 10 && l.get(0)[1] == 20);
        check("un tope absurdo (0 o negativo) deja al menos el suyo", NoxCarga.chunks(10, 20, 3, false, 2, 1, 0, 5, 0).size() == 1 && NoxCarga.chunks(10, 20, 3, false, 2, 1, 0, 5, -4).size() == 1);
        l = NoxCarga.chunks(10, 20, 2, false, 2, 1, 0, 3, 26);
        check("el tope recorta primero lo LEJANO: con 26 el anillo 5x5 (25) queda entero y entra solo 1 de delante", l.size() == 26 && conjunto(l).contains("13,20"));

        System.out.println(fallos == 0 ? "\nTODO OK" : "\nFALLOS: " + fallos);
        if (fallos > 0) System.exit(1);
    }
}
