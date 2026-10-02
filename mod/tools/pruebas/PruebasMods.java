import com.example.cobaltbot.util.NoxMods;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Pruebas de H6 (lista de mods en JSON): pura, sin Minecraft ni Forge. */
public class PruebasMods {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static JsonObject analizar(String json) { return JsonParser.parseString(json).getAsJsonObject(); }

    public static void main(String[] a) {
        List<String[]> mods = new ArrayList<>();
        mods.add(new String[] {"create", "0.5.1.f"});
        mods.add(new String[] {"mekanism", "10.4.8"});
        JsonObject j = analizar(NoxMods.aJson("1.20.1", mods));
        check("estructura: minecraft, count y mods en el orden dado", j.get("minecraft").getAsString().equals("1.20.1") && j.get("count").getAsInt() == 2
                && j.getAsJsonArray("mods").size() == 2 && j.getAsJsonArray("mods").get(0).getAsJsonObject().get("id").getAsString().equals("create")
                && j.getAsJsonArray("mods").get(1).getAsJsonObject().get("version").getAsString().equals("10.4.8"));

        check("lista vacía y null: JSON válido con count 0", analizar(NoxMods.aJson("1.20.1", new ArrayList<>())).get("count").getAsInt() == 0
                && analizar(NoxMods.aJson(null, null)).get("count").getAsInt() == 0 && analizar(NoxMods.aJson(null, null)).get("minecraft").getAsString().isEmpty());

        List<String[]> raros = new ArrayList<>();
        raros.add(null);
        raros.add(new String[] {});
        raros.add(new String[] {null, "1"});
        raros.add(new String[] {"   ", "1"});
        raros.add(new String[] {"solo_id"});
        raros.add(new String[] {"  con_espacios  ", "  2.0  "});
        raros.add(new String[] {"sin_version", null});
        j = analizar(NoxMods.aJson("x", raros));
        JsonArray arr = j.getAsJsonArray("mods");
        check("entradas raras: null, vacías y sin id se ignoran; sin versión queda '' y se recortan espacios (3 válidas)", j.get("count").getAsInt() == 3 && arr.size() == 3
                && arr.get(0).getAsJsonObject().get("version").getAsString().isEmpty() && arr.get(1).getAsJsonObject().get("id").getAsString().equals("con_espacios")
                && arr.get(1).getAsJsonObject().get("version").getAsString().equals("2.0") && arr.get(2).getAsJsonObject().get("version").getAsString().isEmpty());

        List<String[]> inyeccion = new ArrayList<>();
        inyeccion.add(new String[] {"evil\"},{\"id\":\"x", "1\n2"});
        String json = NoxMods.aJson("1.20.1\"}", inyeccion);
        j = analizar(json); // si no se escapara, esto no sería JSON válido o tendría un mod de más
        check("comillas y saltos de línea en los nombres se escapan: sigue siendo 1 mod y JSON válido", j.get("count").getAsInt() == 1 && j.getAsJsonArray("mods").size() == 1);

        check("un id o versión larguísimo se acota a " + NoxMods.MAX_TEXTO, analizar(NoxMods.aJson("x", Arrays.<String[]>asList(new String[] {"a".repeat(500), "v".repeat(500)}))).getAsJsonArray("mods")
                .get(0).getAsJsonObject().get("id").getAsString().length() == NoxMods.MAX_TEXTO);

        List<String[]> muchos = new ArrayList<>();
        for (int i = 0; i < NoxMods.MAX_MODS + 500; i++) muchos.add(new String[] {"mod" + i, "1"});
        j = analizar(NoxMods.aJson("x", muchos));
        check("más de " + NoxMods.MAX_MODS + " mods: se listan solo " + NoxMods.MAX_MODS + " pero 'count' dice el total real", j.getAsJsonArray("mods").size() == NoxMods.MAX_MODS && j.get("count").getAsInt() == NoxMods.MAX_MODS + 500);

        System.out.println(fallos == 0 ? "\nPRUEBAS DE MODS OK" : "\nFALLOS: " + fallos);
        System.exit(fallos == 0 ? 0 : 1);
    }
}
