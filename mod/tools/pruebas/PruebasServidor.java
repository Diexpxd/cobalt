import com.example.cobaltbot.util.NoxServidor;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Pruebas del Bloque O (servidor y mantenimiento): TPS, límites del libro y reglas de hornos. */
public class PruebasServidor {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static boolean cerca(double a, double b) { return Math.abs(a - b) < 1e-9; }

    public static void main(String[] a) {
        check("tps: 50 ms por tick = 20 TPS", cerca(NoxServidor.tpsDesdeMspt(50.0), 20.0));
        check("tps: 25 ms (más rápido de lo necesario) sigue siendo 20, nunca más", cerca(NoxServidor.tpsDesdeMspt(25.0), 20.0));
        check("tps: 100 ms = 10 TPS; 200 ms = 5 TPS; 2000 ms = 0,5 TPS", cerca(NoxServidor.tpsDesdeMspt(100.0), 10.0) && cerca(NoxServidor.tpsDesdeMspt(200.0), 5.0) && cerca(NoxServidor.tpsDesdeMspt(2000.0), 0.5));
        check("tps: datos rotos (0, negativo, NaN, infinito) = 20: no se da una falsa alarma",
                cerca(NoxServidor.tpsDesdeMspt(0.0), 20.0) && cerca(NoxServidor.tpsDesdeMspt(-5.0), 20.0) && cerca(NoxServidor.tpsDesdeMspt(Double.NaN), 20.0) && cerca(NoxServidor.tpsDesdeMspt(Double.POSITIVE_INFINITY), 20.0));
        check("tps: 62,5 ms = 16 TPS", cerca(NoxServidor.tpsDesdeMspt(62.5), 16.0));

        NoxServidor.Libro l = NoxServidor.limitarLibro("Crónica de Cobalt", Arrays.asList("Página uno", "Página dos"));
        check("libro: un libro normal queda intacto", l.titulo().equals("Crónica de Cobalt") && l.paginas().equals(Arrays.asList("Página uno", "Página dos")));
        check("libro: el título se corta a 32 caracteres", NoxServidor.limitarLibro("x".repeat(80), Arrays.asList("a")).titulo().length() == 32);
        check("libro: título vacío o nulo = 'Crónica'", NoxServidor.limitarLibro("   ", Arrays.asList("a")).titulo().equals("Cr\u00f3nica") && NoxServidor.limitarLibro(null, Arrays.asList("a")).titulo().equals("Cr\u00f3nica"));
        List<String> muchas = new ArrayList<>();
        for (int i = 0; i < 100; i++) muchas.add("p" + i);
        NoxServidor.Libro grande = NoxServidor.limitarLibro("t", muchas);
        check("libro: máximo 40 páginas (se conservan las primeras)", grande.paginas().size() == 40 && grande.paginas().get(0).equals("p0") && grande.paginas().get(39).equals("p39"));
        check("libro: cada página se corta a 250 caracteres", NoxServidor.limitarLibro("t", Arrays.asList("y".repeat(900))).paginas().get(0).length() == 250);
        check("libro: las páginas vacías o en blanco se descartan", NoxServidor.limitarLibro("t", Arrays.asList("", "   ", "\n\n", "ok")).paginas().equals(Arrays.asList("ok")));
        check("libro: sin páginas (null o lista vacía) da 0 páginas", NoxServidor.limitarLibro("t", null).paginas().isEmpty() && NoxServidor.limitarLibro("t", new ArrayList<>()).paginas().isEmpty());
        check("libro: los caracteres de control se eliminan pero el salto de línea se conserva", NoxServidor.limitarLibro("t", Arrays.asList("a\u0000b\u0007c\nd\u007f")).paginas().get(0).equals("abc\nd"));
        check("libro: un salto de línea en el título se convierte en espacio", NoxServidor.limitarLibro("uno\ndos", Arrays.asList("a")).titulo().equals("uno dos"));

        check("combustible: carbón, carbón vegetal, bloque de carbón y vara de blaze sí",
                NoxServidor.esCombustibleSeguro("coal") && NoxServidor.esCombustibleSeguro("charcoal") && NoxServidor.esCombustibleSeguro("coal_block") && NoxServidor.esCombustibleSeguro("blaze_rod"));
        check("combustible: tablones, herramientas de madera, cubo de lava, palos y nulo NO",
                !NoxServidor.esCombustibleSeguro("oak_planks") && !NoxServidor.esCombustibleSeguro("wooden_pickaxe") && !NoxServidor.esCombustibleSeguro("lava_bucket")
                        && !NoxServidor.esCombustibleSeguro("stick") && !NoxServidor.esCombustibleSeguro(null) && !NoxServidor.esCombustibleSeguro("coal_ore"));
        check("fundible: menas en bruto, menas y escombros antiguos sí",
                NoxServidor.esFundible("raw_iron") && NoxServidor.esFundible("raw_copper") && NoxServidor.esFundible("iron_ore") && NoxServidor.esFundible("deepslate_gold_ore") && NoxServidor.esFundible("ancient_debris"));
        check("fundible: comida cruda sí (carne, pescado, patata, alga)",
                NoxServidor.esFundible("beef") && NoxServidor.esFundible("porkchop") && NoxServidor.esFundible("cod") && NoxServidor.esFundible("potato") && NoxServidor.esFundible("kelp"));
        check("fundible: herramientas y armaduras de hierro/oro NO (se convertirían en pepitas)",
                !NoxServidor.esFundible("iron_pickaxe") && !NoxServidor.esFundible("iron_chestplate") && !NoxServidor.esFundible("golden_sword") && !NoxServidor.esFundible("iron_ingot"));
        check("fundible: comida ya cocinada, bloques crudos, cobblestone y nulo NO",
                !NoxServidor.esFundible("cooked_beef") && !NoxServidor.esFundible("raw_iron_block") && !NoxServidor.esFundible("cobblestone") && !NoxServidor.esFundible("sand") && !NoxServidor.esFundible(null));
        check("cantidad: con el horno vacío se mete lo que se pide (8 de 20 disponibles)", NoxServidor.cantidadAMeter(0, 8, 20) == 8);
        check("cantidad: no se pasa de lo disponible (3 de 3) ni del límite (ya hay 6, límite 8 -> 2)", NoxServidor.cantidadAMeter(0, 8, 3) == 3 && NoxServidor.cantidadAMeter(6, 8, 20) == 2);
        check("cantidad: si ya está lleno o pasado del límite no mete nada (nunca negativo)", NoxServidor.cantidadAMeter(8, 8, 20) == 0 && NoxServidor.cantidadAMeter(12, 8, 20) == 0 && NoxServidor.cantidadAMeter(0, 8, 0) == 0 && NoxServidor.cantidadAMeter(-3, 8, 20) == 8);

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
