import com.example.cobaltbot.util.NoxRutas;

import java.io.File;

/** Pruebas de la carpeta de intercambio con Python (NoxRutas): por defecto la de siempre y configurable sin recompilar. */
public class PruebasRutas {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    public static void main(String[] a) {
        System.clearProperty("cobalt.dir");
        boolean hayEntorno = System.getenv("COBALT_DIR") != null && !System.getenv("COBALT_DIR").isBlank();
        if (!hayEntorno) {
            check("sin propiedad ni variable: la carpeta por defecto", NoxRutas.dir().equals(new File(NoxRutas.POR_DEFECTO)));
            System.setProperty("cobalt.dir", "   ");
            check("una propiedad en blanco se ignora (vuelve a la de por defecto)", NoxRutas.dir().equals(new File(NoxRutas.POR_DEFECTO)));
            System.setProperty("cobalt.dir", "");
            check("una propiedad vacía se ignora", NoxRutas.dir().equals(new File(NoxRutas.POR_DEFECTO)));
        } else {
            System.out.println("SKIP  (la variable COBALT_DIR está definida en este equipo: no se prueba el valor por defecto)");
        }
        System.setProperty("cobalt.dir", "D:\\otra_carpeta");
        check("-Dcobalt.dir manda sobre todo lo demás", NoxRutas.dir().equals(new File("D:\\otra_carpeta")));
        check("archivo(nombre) cuelga de esa carpeta", NoxRutas.archivo("command.json").equals(new File(new File("D:\\otra_carpeta"), "command.json")));
        System.setProperty("cobalt.dir", "  D:\\con_espacios  ");
        check("los espacios alrededor se recortan", NoxRutas.dir().equals(new File("D:\\con_espacios")));
        System.setProperty("cobalt.dir", "D:\\uno");
        check("se relee en cada llamada (cambiarla en caliente funciona)", NoxRutas.dir().equals(new File("D:\\uno")));
        System.clearProperty("cobalt.dir");

        System.out.println(fallos == 0 ? "\nPRUEBAS DE RUTAS OK" : "\nFALLOS: " + fallos);
        System.exit(fallos == 0 ? 0 : 1);
    }
}
