package com.example.cobaltbot.gametest;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.cache.object.GeoCube;
import software.bernie.geckolib.cache.object.GeoQuad;
import software.bernie.geckolib.core.animation.Animation;
import software.bernie.geckolib.loading.json.raw.Model;
import software.bernie.geckolib.loading.object.BakedAnimations;
import software.bernie.geckolib.loading.object.BakedModelFactory;
import software.bernie.geckolib.loading.object.GeometryTree;
import software.bernie.geckolib.util.JsonUtil;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static com.example.cobaltbot.gametest.CobaltGameTests.PLANTILLA;

/** Los modelos 3D no se pueden ver en un servidor sin ventana, pero SÍ se pueden cargar con el propio cargador. */
@GameTestHolder("cobaltmod")
@PrefixGameTestTemplate(false)
public class CobaltModeloTests {

    static final List<String> ANIMACIONES_DE_COBALT = List.of("idle", "walk", "fly", "fly_move", "fly_start", "fly_end", "swim", "attack", "cast_spell", "emp", "death", "runico");

    static String texto(String ruta) throws Exception {
        try (InputStream in = CobaltModeloTests.class.getResourceAsStream(ruta)) {
            if (in == null) throw new IllegalStateException("no está en el .jar: " + ruta);
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    static BufferedImage imagen(String ruta) throws Exception {
        try (InputStream in = CobaltModeloTests.class.getResourceAsStream(ruta)) {
            if (in == null) throw new IllegalStateException("no está en el .jar: " + ruta);
            return ImageIO.read(in);
        }
    }

    static void validar(GameTestHelper h, String nombre, List<String> animaciones, int minHuesos, int minCubos) throws Exception {
        String rutaGeo = "/assets/cobaltbot/geo/" + nombre + ".geo.json";
        String rutaAnim = "/assets/cobaltbot/animations/" + nombre + ".animation.json";
        Model modelo = JsonUtil.GEO_GSON.fromJson(texto(rutaGeo), Model.class);
        BakedGeoModel baked = BakedModelFactory.getForNamespace("cobaltbot").constructGeoModel(GeometryTree.fromModel(modelo));
        int huesos = 0, cubos = 0, caras = 0;
        Set<String> nombres = new HashSet<>();
        java.util.ArrayDeque<GeoBone> pila = new java.util.ArrayDeque<>(baked.topLevelBones());
        while (!pila.isEmpty()) {
            GeoBone b = pila.pop();
            huesos++;
            nombres.add(b.getName());
            pila.addAll(b.getChildBones());
            for (GeoCube c : b.getCubes()) {
                cubos++;
                for (GeoQuad q : c.quads()) if (q != null) caras++;
            }
        }
        h.assertTrue(huesos >= minHuesos && cubos >= minCubos, nombre + ": el modelo debe tener huesos y cubos (tiene " + huesos + " huesos y " + cubos + " cubos)");
        h.assertTrue(caras >= cubos * 4, nombre + ": cada cubo debe tener sus caras (" + caras + " caras para " + cubos + " cubos)");

        JsonObject crudas = JsonParser.parseString(texto(rutaAnim)).getAsJsonObject().getAsJsonObject("animations");
        BakedAnimations anims = JsonUtil.GEO_GSON.fromJson(crudas, BakedAnimations.class);
        for (String a : animaciones) h.assertTrue(anims.animations().containsKey(a), nombre + ": falta la animación '" + a + "' que pide el código");
        for (String a : crudas.keySet()) {
            JsonObject bones = crudas.getAsJsonObject(a).getAsJsonObject("bones");
            if (bones == null) continue;
            for (String hueso : bones.keySet()) h.assertTrue(nombres.contains(hueso), nombre + ": la animación '" + a + "' mueve el hueso '" + hueso + "', que no existe en el modelo");
        }
        for (Animation a : anims.animations().values()) h.assertTrue(a.length() > 0.0D, nombre + ": la animación '" + a.name() + "' no tiene duración");

        JsonObject geoJson = JsonParser.parseString(texto(rutaGeo)).getAsJsonObject().getAsJsonArray("minecraft:geometry").get(0).getAsJsonObject();
        int tw = geoJson.getAsJsonObject("description").get("texture_width").getAsInt(), th = geoJson.getAsJsonObject("description").get("texture_height").getAsInt();
        BufferedImage base = imagen("/assets/cobaltbot/textures/entity/" + nombre + ".png");
        BufferedImage brillo = imagen("/assets/cobaltbot/textures/entity/" + nombre + "_glowmask.png");
        h.assertTrue(base.getWidth() == tw && base.getHeight() == th, nombre + ".png (" + base.getWidth() + "x" + base.getHeight() + ") no coincide con el modelo (" + tw + "x" + th + ")");
        h.assertTrue(brillo.getWidth() == tw && brillo.getHeight() == th, nombre + "_glowmask.png debe medir lo mismo que la textura base");
        int marcados = 0;
        for (int x = 0; x < tw; x++) {
            for (int y = 0; y < th; y++) {
                if (brillo.getRGB(x, y) == 0) continue;
                marcados++;
                h.assertTrue((base.getRGB(x, y) >>> 24) != 0, nombre + "_glowmask.png marca un píxel (" + x + "," + y + ") que en la textura base está vacío");
            }
        }
        h.assertTrue(marcados > 0, nombre + "_glowmask.png no marca ningún píxel: no habría brillo");

        // ninguna cara del modelo apunta fuera de la textura
        for (JsonElement be : geoJson.getAsJsonArray("bones")) {
            JsonObject b = be.getAsJsonObject();
            if (!b.has("cubes")) continue;
            for (JsonElement ce : b.getAsJsonArray("cubes")) {
                JsonObject uv = ce.getAsJsonObject().getAsJsonObject("uv");
                for (String cara : uv.keySet()) {
                    JsonArray o = uv.getAsJsonObject(cara).getAsJsonArray("uv"), t = uv.getAsJsonObject(cara).getAsJsonArray("uv_size");
                    h.assertTrue(o.get(0).getAsInt() >= 0 && o.get(1).getAsInt() >= 0 && o.get(0).getAsInt() + t.get(0).getAsInt() <= tw && o.get(1).getAsInt() + t.get(1).getAsInt() <= th,
                            nombre + ": una cara del hueso '" + b.get("name").getAsString() + "' cae fuera de la textura");
                }
            }
        }
    }

    static void probar(GameTestHelper h, String nombre, List<String> animaciones, int minHuesos, int minCubos) {
        try {
            validar(h, nombre, animaciones, minHuesos, minCubos);
        } catch (GameTestAssertException e) {
            throw e;
        } catch (Exception e) {
            h.fail("el modelo '" + nombre + "' no carga: " + e);
        }
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void el_guardian_lo_carga_geckolib_con_todas_las_animaciones_que_usa_cobalt(GameTestHelper h) {
        probar(h, "nox", ANIMACIONES_DE_COBALT, 30, 100);
    }

    @GameTest(template = PLANTILLA)
    public static void el_orbe_de_plasma_lo_carga_geckolib(GameTestHelper h) {
        probar(h, "plasma", List.of("spin"), 4, 30);
    }

    @GameTest(template = PLANTILLA)
    public static void la_onda_de_runas_del_emp_la_carga_geckolib(GameTestHelper h) {
        probar(h, "emp_wave", List.of("expand"), 4, 100);
    }

    @GameTest(template = PLANTILLA)
    public static void el_dron_lo_carga_geckolib(GameTestHelper h) {
        probar(h, "drone", List.of("spin"), 3, 15);
    }
}
