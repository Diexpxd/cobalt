import com.example.cobaltbot.util.NoxLotes;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import java.util.ArrayList;
import java.util.List;

/** Pruebas de la colocación por lotes (parte pura): leer el lote, indices de los fallos y el resumen para Python. */
public class PruebasLotes {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static JsonElement j(String s) { return JsonParser.parseString(s); }

    public static void main(String[] a) {
        NoxLotes.Parseado p = NoxLotes.parsear(j("[{\"x\":1,\"y\":64,\"z\":2,\"block\":\"minecraft:stone\"},{\"x\":-3,\"y\":70,\"z\":5,\"block\":\"minecraft:oak_stairs\",\"state\":\"facing=east\"}]"));
        check("lote válido: 2 bloques con sus índices originales, coordenadas y estado", p.total() == 2 && p.ignorados() == 0 && p.fallos().isEmpty() && p.bloques().size() == 2
                && p.bloques().get(0).i() == 0 && p.bloques().get(0).x() == 1 && p.bloques().get(0).state().isEmpty() && p.bloques().get(1).i() == 1 && p.bloques().get(1).x() == -3
                && p.bloques().get(1).state().equals("facing=east") && p.bloques().get(1).block().equals("minecraft:oak_stairs"));

        p = NoxLotes.parsear(j("[{\"x\":1,\"y\":2,\"z\":3,\"block\":\"minecraft:stone\"},{\"x\":1,\"y\":2,\"block\":\"minecraft:stone\"},5,null,\"texto\",{\"x\":1.5,\"y\":2,\"z\":3,\"block\":\"a\"},"
                + "{\"x\":\"1\",\"y\":2,\"z\":3,\"block\":\"a\"},{\"x\":1,\"y\":2,\"z\":3},{\"x\":1,\"y\":2,\"z\":3,\"block\":\"  \"},{\"x\":1,\"y\":2,\"z\":3,\"block\":\"minecraft:dirt\"}]"));
        check("elementos inválidos (sin z, número, null, texto, decimal, coordenada como texto, sin bloque, bloque en blanco) fallan con 'invalido' SIN abortar el resto: " + p.fallos().size() + " fallos",
                p.total() == 10 && p.bloques().size() == 2 && p.fallos().size() == 8 && p.fallos().stream().allMatch(f -> f.motivo().equals("invalido")) && p.bloques().get(1).i() == 9
                        && p.fallos().get(0).i() == 1 && p.fallos().get(7).i() == 8);

        check("coordenadas absurdas (NaN no existe en JSON; 1e20 y -1e20) se rechazan", NoxLotes.parsear(j("[{\"x\":1e20,\"y\":1,\"z\":1,\"block\":\"a\"},{\"x\":-1e20,\"y\":1,\"z\":1,\"block\":\"a\"}]")).fallos().size() == 2);
        check("una coordenada entera escrita como 5.0 vale (JSON de Python)", NoxLotes.parsear(j("[{\"x\":5.0,\"y\":1,\"z\":1,\"block\":\"a\"}]")).bloques().size() == 1);

        JsonArray grande = new JsonArray();
        for (int i = 0; i < NoxLotes.MAX_LOTE + 10; i++) {
            JsonObject o = new JsonObject();
            o.addProperty("x", i); o.addProperty("y", 1); o.addProperty("z", 1); o.addProperty("block", "minecraft:stone");
            grande.add(o);
        }
        p = NoxLotes.parsear(grande);
        check("más de " + NoxLotes.MAX_LOTE + " bloques: se leen solo los primeros " + NoxLotes.MAX_LOTE + " y 'ignorados' dice cuántos sobran", p.total() == NoxLotes.MAX_LOTE && p.bloques().size() == NoxLotes.MAX_LOTE && p.ignorados() == 10);

        check("null, algo que no es un array, y array vacío: lote vacío sin lanzar", NoxLotes.parsear(null).total() == 0 && NoxLotes.parsear(j("{}")).total() == 0 && NoxLotes.parsear(j("\"x\"")).total() == 0
                && NoxLotes.parsear(j("[]")).total() == 0);

        check("texto larguísimo en 'block' se rechaza (no se acota en silencio)", NoxLotes.parsear(j("[{\"x\":1,\"y\":1,\"z\":1,\"block\":\"" + "a".repeat(400) + "\"}]")).fallos().size() == 1);

        JsonObject r = JsonParser.parseString(NoxLotes.resumen(5, 5, new ArrayList<>(), 0)).getAsJsonObject();
        check("resumen: todo colocado -> success, sin fallos ni campos extra", r.get("status").getAsString().equals("success") && r.get("placed").getAsInt() == 5 && r.get("total").getAsInt() == 5
                && r.getAsJsonArray("failed").size() == 0 && !r.has("failed_more") && !r.has("ignored"));
        List<NoxLotes.Fallo> f = new ArrayList<>();
        f.add(new NoxLotes.Fallo(1, "ocupado"));
        f.add(new NoxLotes.Fallo(3, "no_material"));
        r = JsonParser.parseString(NoxLotes.resumen(5, 3, f, 2)).getAsJsonObject();
        check("resumen: parcial con los índices y motivos de lo que falló, y 'ignored'", r.get("status").getAsString().equals("partial") && r.get("placed").getAsInt() == 3
                && r.getAsJsonArray("failed").size() == 2 && r.getAsJsonArray("failed").get(0).getAsJsonObject().get("i").getAsInt() == 1
                && r.getAsJsonArray("failed").get(1).getAsJsonObject().get("reason").getAsString().equals("no_material") && r.get("ignored").getAsInt() == 2);
        r = JsonParser.parseString(NoxLotes.resumen(3, 0, f, 0)).getAsJsonObject();
        check("resumen: nada colocado -> failed", r.get("status").getAsString().equals("failed") && r.get("placed").getAsInt() == 0);
        r = JsonParser.parseString(NoxLotes.resumen(0, 0, null, 0)).getAsJsonObject();
        check("resumen: lote vacío -> failed (no 'success' de algo que no se hizo) y sin lanzar con fallos null", r.get("status").getAsString().equals("failed") && r.get("total").getAsInt() == 0);
        r = JsonParser.parseString(NoxLotes.resumen(4, 9, new ArrayList<>(), 0)).getAsJsonObject();
        check("resumen: 'colocados' mayor que el total se acota (no se inventa un éxito mayor)", r.get("placed").getAsInt() == 4);

        List<NoxLotes.Fallo> muchos = new ArrayList<>();
        for (int i = 0; i < 100; i++) muchos.add(new NoxLotes.Fallo(i, "ocupado"));
        r = JsonParser.parseString(NoxLotes.resumen(100, 0, muchos, 0)).getAsJsonObject();
        check("resumen: como mucho " + NoxLotes.MAX_FALLOS + " fallos listados y 'failed_more' cuenta el resto", r.getAsJsonArray("failed").size() == NoxLotes.MAX_FALLOS && r.get("failed_more").getAsInt() == 100 - NoxLotes.MAX_FALLOS);
        List<NoxLotes.Fallo> raros = new ArrayList<>();
        raros.add(null);
        raros.add(new NoxLotes.Fallo(2, null));
        raros.add(new NoxLotes.Fallo(3, "  "));
        r = JsonParser.parseString(NoxLotes.resumen(5, 2, raros, 0)).getAsJsonObject();
        check("resumen: un fallo null se salta y un motivo vacío se llama 'error'", r.getAsJsonArray("failed").size() == 2 && r.getAsJsonArray("failed").get(0).getAsJsonObject().get("reason").getAsString().equals("error")
                && r.getAsJsonArray("failed").get(1).getAsJsonObject().get("reason").getAsString().equals("error"));

        System.out.println(fallos == 0 ? "\nPRUEBAS DE LOTES OK" : "\nFALLOS: " + fallos);
        System.exit(fallos == 0 ? 0 : 1);
    }
}
