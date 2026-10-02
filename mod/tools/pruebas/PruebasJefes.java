import com.example.cobaltbot.util.NoxJefes;
import com.example.cobaltbot.util.NoxJefes.ParametrosKiting;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

/** Pruebas del Bloque D (jefes): parámetros del protocolo y JSON de encuentros, sin abrir Minecraft. */
public class PruebasJefes {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    public static void main(String[] a) {
        ParametrosKiting normal = NoxJefes.parametros(false);
        ParametrosKiting jefe = NoxJefes.parametros(true);
        check("normal: retroceso 9 / ideal 12 / máx 16 (idénticos al kiting anterior: nada cambia sin jefe)",
                normal.retroceso() == 9.0 && normal.ideal() == 12.0 && normal.max() == 16.0);
        check("normal: permite melee y EMP", normal.permiteMelee() && normal.permiteEmp());
        check("jefe: más distancia (14 / 18 / 24)", jefe.retroceso() == 14.0 && jefe.ideal() == 18.0 && jefe.max() == 24.0);
        check("jefe: NO permite melee ni EMP (solo plasma)", !jefe.permiteMelee() && !jefe.permiteEmp());
        check("jefe: las distancias mantienen el orden retroceso < ideal < máx", jefe.retroceso() < jefe.ideal() && jefe.ideal() < jefe.max());

        double min = 1e9, max = -1e9;
        for (long t = 0; t < 400; t++) {
            double h = NoxJefes.alturaEvasion(70.0, t);
            min = Math.min(min, h);
            max = Math.max(max, h);
        }
        check("evasión 3D: oscila entre 67 y 73 (±3 alrededor de 70)", min >= 66.999 && max <= 73.001 && min < 67.1 && max > 72.9);
        check("evasión 3D: en el tick 0 está en la altura base", Math.abs(NoxJefes.alturaEvasion(70.0, 0) - 70.0) < 1e-9);
        check("evasión 3D: cambia con el tiempo (no se queda quieto)", NoxJefes.alturaEvasion(70, 10) != NoxJefes.alturaEvasion(70, 20));

        check("registro: primera vez (último=0) -> permitido", NoxJefes.puedeRegistrar(1000, 0, 120000));
        check("registro: dentro de la ventana -> NO", !NoxJefes.puedeRegistrar(50000, 1000, 120000));
        check("registro: justo al cumplirse la ventana -> permitido", NoxJefes.puedeRegistrar(121000, 1000, 120000));

        String texto = NoxJefes.jsonEncuentro("Ender Dragon", "minecraft:ender_dragon", true, "derrota", 12345L);
        JsonObject j = JsonParser.parseString(texto).getAsJsonObject();
        check("JSON de encuentro válido con todos los campos",
                j.get("jefe").getAsString().equals("Ender Dragon") && j.get("id").getAsString().equals("minecraft:ender_dragon")
                        && j.get("es_jefe").getAsBoolean() && j.get("motivo").getAsString().equals("derrota") && j.get("ts").getAsLong() == 12345L);

        String raro = NoxJefes.jsonEncuentro("El \"Terrible\" Ñandú \\ Ω", "modx:terrible", false, "huida", 1L);
        JsonObject r = JsonParser.parseString(raro).getAsJsonObject();
        check("un nombre con comillas, barras y unicode NO rompe el JSON (antes sí: se armaba a mano)",
                r.get("jefe").getAsString().equals("El \"Terrible\" Ñandú \\ Ω") && !r.get("es_jefe").getAsBoolean());

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
