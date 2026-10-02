package com.example.cobaltbot.gametest;

import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.registry.ModEntities;
import com.example.cobaltbot.util.NoxConfig;
import com.example.cobaltbot.util.NoxCuerpo;
import com.example.cobaltbot.util.NoxRutas;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.gametest.framework.BeforeBatch;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.properties.Half;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/** Pruebas con un MUNDO REAL (servidor de Minecraft sin ventana): lo que las pruebas de Java puras no pueden ver. */
@GameTestHolder("cobaltmod")
@PrefixGameTestTemplate(false)
public class CobaltGameTests {
    static final String PLANTILLA = "empty";
    static final int Y = 2;

    static void config(String json) {
        NoxConfig.fijarParaPruebas(json);
        NoxRutas.dir().mkdirs();
    }

    static void purgarMundo(ServerLevel nivel) {
        List<Entity> todas = new ArrayList<>();
        for (Entity x : nivel.getAllEntities()) todas.add(x);
        for (Entity x : todas) if (!(x instanceof Player) || x instanceof FakePlayer) x.discard();
    }

    @BeforeBatch(batch = "defaultBatch")
    public static void limpiarAntesDelBatchPorDefecto(ServerLevel nivel) {
        purgarMundo(nivel);
    }

    static CobaltEntity crear(GameTestHelper h, BlockPos rel) {
        CobaltEntity e = ModEntities.COBALT.get().create(h.getLevel());
        Vec3 p = h.absoluteVec(new Vec3(rel.getX() + 0.5D, rel.getY(), rel.getZ() + 0.5D));
        e.moveTo(p.x, p.y, p.z, 0.0F, 0.0F);
        e.setPersistenceRequired();
        h.getLevel().getGameRules().getRule(net.minecraft.world.level.GameRules.RULE_DOMOBSPAWNING).set(false, h.getLevel().getServer()); // sin mobs naturales que estorben
        net.minecraft.world.level.ChunkPos cp = new net.minecraft.world.level.ChunkPos(BlockPos.containing(p));
        for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++) h.getLevel().setChunkForced(cp.x + dx, cp.z + dz, true);
        h.getLevel().addFreshEntity(e);
        return e;
    }

    static Object campo(Object o, String nombre) throws Exception {
        Field f = o.getClass().getDeclaredField(nombre);
        f.setAccessible(true);
        return f.get(o);
    }

    static SimpleContainer inventario(CobaltEntity e) {
        return e.getCobaltInventory();
    }

    static String motivo(CobaltEntity e) throws Exception {
        return (String) campo(e, "motivoFalloColocacion");
    }

    static void invocar(CobaltEntity e, String metodo, Class<?>[] tipos, Object... args) throws Exception {
        Method m = CobaltEntity.class.getDeclaredMethod(metodo, tipos);
        m.setAccessible(true);
        m.invoke(e, args);
    }

    static int cuantos(SimpleContainer c, Item item) {
        int n = 0;
        for (int i = 0; i < c.getContainerSize(); i++) if (c.getItem(i).is(item)) n += c.getItem(i).getCount();
        return n;
    }

    static JsonObject leerJson(String nombre) throws Exception {
        File f = NoxRutas.archivo(nombre);
        return JsonParser.parseString(Files.readString(f.toPath(), StandardCharsets.UTF_8)).getAsJsonObject();
    }

    static void escribir(String nombre, String contenido) throws Exception {
        NoxRutas.dir().mkdirs();
        Files.writeString(NoxRutas.archivo(nombre).toPath(), contenido, StandardCharsets.UTF_8);
    }

    static String ordenPlaceBlock(GameTestHelper h, BlockPos rel, String bloque, String estado) {
        BlockPos a = h.absolutePos(rel);
        return "[{\"action\": \"place_block\", \"x\": " + a.getX() + ", \"y\": " + a.getY() + ", \"z\": " + a.getZ() + ", \"block\": \"" + bloque + "\""
                + (estado == null ? "" : ", \"state\": \"" + estado + "\"") + ", \"movement_mode\": \"walk\", \"bot_id\": \"" + NoxCuerpo.BOT_ID + "\"}]";
    }

    @GameTest(template = PLANTILLA)
    public static void escalera_con_estado(GameTestHelper h) throws Exception {
        config("{\"schematics_estados\": true}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_STAIRS, 2));
        BlockPos rel = new BlockPos(4, Y, 4);
        boolean ok = e.colocarBloqueEnMundo(h.absolutePos(rel), "minecraft:oak_stairs", "facing=east,half=top");
        h.assertTrue(ok, "colocarBloqueEnMundo devolvió false: " + motivo(e));
        h.assertBlockState(rel, s -> s.is(Blocks.OAK_STAIRS) && s.getValue(StairBlock.FACING) == Direction.EAST && s.getValue(StairBlock.HALF) == Half.TOP,
                () -> "la escalera no quedó con facing=east,half=top");
        h.assertTrue(cuantos(inventario(e), Items.OAK_STAIRS) == 1, "debía gastar exactamente 1 escalera del inventario");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void antorcha_de_pared_usa_el_item_de_la_antorcha(GameTestHelper h) throws Exception {
        config("{\"schematics_estados\": true}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.TORCH, 1));
        h.setBlock(new BlockPos(4, Y, 5), Blocks.STONE); // el soporte de la antorcha (mira al norte: se apoya en el sur)
        BlockPos rel = new BlockPos(4, Y, 4);
        boolean ok = e.colocarBloqueEnMundo(h.absolutePos(rel), "minecraft:wall_torch", "facing=north");
        h.assertTrue(ok, "con schematics_estados debía valer el ítem 'torch' para el bloque 'wall_torch': " + motivo(e));
        h.assertBlockState(rel, s -> s.is(Blocks.WALL_TORCH), () -> "no hay antorcha de pared");
        h.assertTrue(cuantos(inventario(e), Items.TORCH) == 0, "debía gastar la antorcha");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void antorcha_de_pared_sin_el_interruptor_no_cuenta(GameTestHelper h) throws Exception {
        config("{\"schematics_estados\": false}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.TORCH, 1));
        h.setBlock(new BlockPos(4, Y, 5), Blocks.STONE);
        boolean ok = e.colocarBloqueEnMundo(h.absolutePos(new BlockPos(4, Y, 4)), "minecraft:wall_torch", "");
        h.assertTrue(!ok && "no_material".equals(motivo(e)), "sin el interruptor debe ser el camino de siempre: false / no_material (ok=" + ok + ", motivo=" + motivo(e) + ")");
        h.assertBlockNotPresent(Blocks.WALL_TORCH, new BlockPos(4, Y, 4));
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void sin_material_y_hueco_ocupado(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        BlockPos rel = new BlockPos(4, Y, 4);
        boolean sinMaterial = e.colocarBloqueEnMundo(h.absolutePos(rel), "minecraft:stone", "");
        h.assertTrue(!sinMaterial && "no_material".equals(motivo(e)), "sin piedra en el inventario: false / no_material (motivo=" + motivo(e) + ")");
        inventario(e).addItem(new ItemStack(Items.STONE, 3));
        h.setBlock(rel, Blocks.DIRT);
        boolean ocupado = e.colocarBloqueEnMundo(h.absolutePos(rel), "minecraft:stone", "");
        h.assertTrue(!ocupado && "ocupado".equals(motivo(e)), "hueco ocupado por tierra: false / ocupado (motivo=" + motivo(e) + ")");
        h.assertBlockPresent(Blocks.DIRT, rel);
        h.assertTrue(cuantos(inventario(e), Items.STONE) == 3, "un bloque no colocado NO debe gastar material");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void bloque_invalido(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.STONE, 1));
        boolean ok = e.colocarBloqueEnMundo(h.absolutePos(new BlockPos(4, Y, 4)), "minecraft:stone_que_no_existe", "");
        h.assertTrue(!ok, "un id de bloque que no existe no puede colocarse");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void command_json_coloca_con_estado(GameTestHelper h) throws Exception {
        config("{\"schematics_estados\": true}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_STAIRS, 1));
        NoxRutas.archivo("build_feedback.json").delete();
        escribir("command.json", ordenPlaceBlock(h, new BlockPos(5, Y, 5), "minecraft:oak_stairs", "facing=south,half=bottom"));
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.assertBlockState(new BlockPos(5, Y, 5), s -> s.is(Blocks.OAK_STAIRS) && s.getValue(StairBlock.FACING) == Direction.SOUTH && s.getValue(StairBlock.HALF) == Half.BOTTOM,
                () -> "la orden place_block con state no colocó la escalera con facing=south");
        h.assertTrue(!NoxRutas.archivo("command.json").exists(), "Java debe consumir (borrar) command.json");
        h.assertTrue("success".equals(leerJson("build_feedback.json").get("status").getAsString()), "build_feedback.json debe decir success");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void command_json_ignora_el_estado_si_esta_apagado(GameTestHelper h) throws Exception {
        config("{\"schematics_estados\": false}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_STAIRS, 1));
        escribir("command.json", ordenPlaceBlock(h, new BlockPos(5, Y, 5), "minecraft:oak_stairs", "facing=south,half=top"));
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.assertBlockState(new BlockPos(5, Y, 5), s -> s.is(Blocks.OAK_STAIRS) && s.getValue(StairBlock.FACING) == Direction.NORTH && s.getValue(StairBlock.HALF) == Half.BOTTOM,
                () -> "con schematics_estados apagado la escalera debe quedar con el estado por defecto (norte, abajo)");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void command_json_de_otro_bot_se_ignora(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.STONE, 1));
        escribir("command.json", ordenPlaceBlock(h, new BlockPos(5, Y, 5), "minecraft:stone", null).replace(NoxCuerpo.BOT_ID, "Cobalt_99"));
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.assertBlockNotPresent(Blocks.STONE, new BlockPos(5, Y, 5));
        h.assertTrue(cuantos(inventario(e), Items.STONE) == 1, "la orden de otro cuerpo no debe gastar material");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void command_json_roto_no_tumba_nada(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        escribir("command.json", "[{\"action\": \"place_block\", \"x\": ");
        invocar(e, "leerComandosDePython", new Class<?>[] {}); // a medio escribir: se reintenta, no lanza
        h.assertTrue(e.isAlive(), "Cobalt sigue vivo tras un command.json a medio escribir");
        NoxRutas.archivo("command.json").delete();
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void gps_json_lleva_el_bloque_mundo_y_mods_json_existe(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(2, Y, 2));
        NoxRutas.archivo("gps.json").delete();
        NoxRutas.archivo("mods.json").delete();
        invocar(e, "actualizarGPS", new Class<?>[] {});
        JsonObject gps = leerJson("gps.json");
        h.assertTrue(gps.has("x") && gps.has("dimension") && gps.has("biome"), "gps.json conserva sus campos de siempre");
        h.assertTrue(gps.has("mundo") && gps.getAsJsonObject("mundo").has("day_time") && gps.getAsJsonObject("mundo").has("raining") && gps.getAsJsonObject("mundo").has("thundering")
                && gps.getAsJsonObject("mundo").has("has_skylight") && gps.getAsJsonObject("mundo").has("sky") && gps.getAsJsonObject("mundo").has("light"), "gps.json debe llevar el bloque 'mundo' completo (H3)");
        long dia = gps.getAsJsonObject("mundo").get("day_time").getAsLong();
        h.assertTrue(dia >= 0 && dia < 24000, "day_time debe estar en [0, 24000): " + dia);
        int luz = gps.getAsJsonObject("mundo").get("light").getAsInt();
        h.assertTrue(luz >= 0 && luz <= 15, "la luz está entre 0 y 15: " + luz);
        JsonObject mods = leerJson("mods.json");
        h.assertTrue(mods.get("count").getAsInt() >= 2 && mods.getAsJsonArray("mods").size() >= 2, "mods.json debe listar los mods cargados");
        boolean estoy = false;
        for (var m : mods.getAsJsonArray("mods")) if ("cobaltbot".equals(m.getAsJsonObject().get("id").getAsString())) estoy = true;
        h.assertTrue(estoy, "mods.json debe incluir al propio mod (cobaltbot)");
        h.succeed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400)
    public static void cobalt_aguanta_120_ticks_con_un_zombi_cerca(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(2, Y, 2));
        h.spawn(EntityType.ZOMBIE, new BlockPos(6, Y, 6));
        h.runAfterDelay(120, () -> {
            h.assertTrue(e.isAlive(), "Cobalt debe seguir vivo y sin fallar tras 120 ticks con un zombi cerca");
            h.succeed();
        });
    }

    @GameTest(template = PLANTILLA)
    public static void cobalt_sin_dueno_no_falla_al_exportar_sensores(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(2, Y, 2));
        invocar(e, "actualizarGPS", new Class<?>[] {});
        JsonObject gps = leerJson("gps.json");
        h.assertTrue(!gps.has("owner"), "sin dueño en la dimensión no hay bloque 'owner' (Python no debe inventar uno)");
        h.succeed();
    }

    static String elemento(GameTestHelper h, int x, int z, String bloque, String estado) {
        BlockPos a = h.absolutePos(new BlockPos(x, Y, z));
        return "{\"x\": " + a.getX() + ", \"y\": " + a.getY() + ", \"z\": " + a.getZ() + ", \"block\": \"" + bloque + "\"" + (estado == null ? "" : ", \"state\": \"" + estado + "\"") + "}";
    }

    static String ordenLote(String... elementos) {
        return "[{\"action\": \"place_blocks\", \"blocks\": [" + String.join(", ", elementos) + "], \"movement_mode\": \"walk\", \"bot_id\": \"" + NoxCuerpo.BOT_ID + "\"}]";
    }

    @GameTest(template = PLANTILLA)
    public static void lote_coloca_varios_y_resume_lo_que_falto(GameTestHelper h) throws Exception {
        config("{\"schematics_estados\": true}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.STONE, 3));
        inventario(e).addItem(new ItemStack(Items.OAK_STAIRS, 1));
        NoxRutas.archivo("build_feedback.json").delete();
        escribir("command.json", ordenLote(elemento(h, 3, 3, "minecraft:stone", null), elemento(h, 4, 3, "minecraft:oak_stairs", "facing=west,half=bottom"),
                elemento(h, 5, 3, "minecraft:stone", null), elemento(h, 3, 4, "minecraft:stone", null), elemento(h, 5, 4, "minecraft:stone", null)));
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.assertBlockPresent(Blocks.STONE, new BlockPos(3, Y, 3));
        h.assertBlockPresent(Blocks.STONE, new BlockPos(5, Y, 3));
        h.assertBlockPresent(Blocks.STONE, new BlockPos(3, Y, 4));
        h.assertBlockState(new BlockPos(4, Y, 3), s -> s.is(Blocks.OAK_STAIRS) && s.getValue(StairBlock.FACING) == Direction.WEST, () -> "la escalera del lote debe llevar su estado (facing=west)");
        h.assertBlockNotPresent(Blocks.STONE, new BlockPos(5, Y, 4)); // el 4.º bloque de piedra: no había material
        JsonObject fb = leerJson("build_feedback.json");
        h.assertTrue("partial".equals(fb.get("status").getAsString()) && fb.get("placed").getAsInt() == 4 && fb.get("total").getAsInt() == 5, "resumen: partial, 4 de 5: " + fb);
        h.assertTrue(fb.getAsJsonArray("failed").size() == 1 && fb.getAsJsonArray("failed").get(0).getAsJsonObject().get("i").getAsInt() == 4
                && "no_material".equals(fb.getAsJsonArray("failed").get(0).getAsJsonObject().get("reason").getAsString()), "debe indicar que falló el índice 4 por no_material: " + fb);
        h.assertTrue(cuantos(inventario(e), Items.STONE) == 0 && cuantos(inventario(e), Items.OAK_STAIRS) == 0, "el lote gasta el material de lo que colocó");
        h.assertTrue(!NoxRutas.archivo("command.json").exists(), "Java consume command.json también con lotes");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void lote_con_ocupado_invalido_y_bloque_inexistente(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.STONE, 10));
        inventario(e).addItem(new ItemStack(Items.APPLE, 1)); // un ítem que NO es un bloque: para el motivo bloque_invalido
        h.setBlock(new BlockPos(4, Y, 3), Blocks.DIRT);
        NoxRutas.archivo("build_feedback.json").delete();
        escribir("command.json", ordenLote(elemento(h, 3, 3, "minecraft:stone", null), elemento(h, 4, 3, "minecraft:stone", null), "{\"x\": 1, \"y\": 2, \"block\": \"minecraft:stone\"}", // sin z: SOLO le falta la z
                elemento(h, 5, 3, "minecraft:bloque_que_no_existe", null), "\"basura\"", elemento(h, 6, 3, "Esto no es un id!", null), elemento(h, 7, 3, "minecraft:stone", null),
                elemento(h, 8, 3, "minecraft:apple", null)));
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.assertBlockPresent(Blocks.STONE, new BlockPos(3, Y, 3));
        h.assertBlockPresent(Blocks.STONE, new BlockPos(7, Y, 3));
        h.assertBlockPresent(Blocks.DIRT, new BlockPos(4, Y, 3));
        JsonObject fb = leerJson("build_feedback.json");
        var fallos = fb.getAsJsonArray("failed");
        h.assertTrue("partial".equals(fb.get("status").getAsString()) && fb.get("placed").getAsInt() == 2 && fb.get("total").getAsInt() == 8 && fallos.size() == 6, "2 colocados de 8, 6 fallos: " + fb);
        String[] esperado = {"1:ocupado", "2:invalido", "3:no_material", "4:invalido", "5:no_material", "7:bloque_invalido"};
        for (int k = 0; k < esperado.length; k++) {
            String real = fallos.get(k).getAsJsonObject().get("i").getAsInt() + ":" + fallos.get(k).getAsJsonObject().get("reason").getAsString();
            h.assertTrue(real.equals(esperado[k]), "el fallo " + k + " debía ser " + esperado[k] + " y es " + real);
        }
        h.assertTrue(cuantos(inventario(e), Items.STONE) == 8 && cuantos(inventario(e), Items.APPLE) == 1, "solo se gastan las 2 piedras colocadas; los fallos no gastan: piedra=" + cuantos(inventario(e), Items.STONE));
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void lote_sin_el_interruptor_ignora_el_estado(GameTestHelper h) throws Exception {
        config("{\"schematics_estados\": false}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_STAIRS, 1));
        escribir("command.json", ordenLote(elemento(h, 4, 4, "minecraft:oak_stairs", "facing=east,half=top")));
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.assertBlockState(new BlockPos(4, Y, 4), s -> s.is(Blocks.OAK_STAIRS) && s.getValue(StairBlock.FACING) == Direction.NORTH && s.getValue(StairBlock.HALF) == Half.BOTTOM,
                () -> "con schematics_estados apagado el lote debe dejar el estado por defecto");
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void lote_de_mas_de_64_se_recorta(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.STONE, 64));
        inventario(e).addItem(new ItemStack(Items.STONE, 10));
        java.util.List<String> els = new java.util.ArrayList<>();
        for (int i = 0; i < 70; i++) els.add(elemento(h, i % 9, i / 9, "minecraft:stone", null));
        escribir("command.json", ordenLote(els.toArray(new String[0])));
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        JsonObject fb = leerJson("build_feedback.json");
        h.assertTrue("success".equals(fb.get("status").getAsString()) && fb.get("placed").getAsInt() == 64 && fb.get("total").getAsInt() == 64 && fb.get("ignored").getAsInt() == 6,
                "solo se procesan 64 y 'ignored' dice 6: " + fb);
        h.assertTrue(cuantos(inventario(e), Items.STONE) == 10, "quedan las 10 piedras que no se usaron: " + cuantos(inventario(e), Items.STONE));
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void gps_json_lleva_hambre_aire_fuego_e_inventario_del_dueno(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(2, Y, 2));
        net.minecraft.server.level.ServerPlayer p = net.minecraftforge.common.util.FakePlayerFactory.get(h.getLevel(),
                new com.mojang.authlib.GameProfile(java.util.UUID.randomUUID(), "cobalt-test-owner"));
        Vec3 pos = h.absoluteVec(new Vec3(3.5D, Y, 3.5D));
        p.moveTo(pos.x, pos.y, pos.z, 0.0F, 0.0F);
        h.getLevel().addFreshEntity(p);
        e.setOwnerUUID(p.getUUID());
        p.getFoodData().setFoodLevel(5);
        p.setAirSupply(60);
        p.setSecondsOnFire(5);
        for (int i = 0; i < 34; i++) p.getInventory().items.set(i, new ItemStack(Items.STONE, 1)); // 2 huecos libres de 36
        NoxRutas.archivo("gps.json").delete();
        invocar(e, "actualizarGPS", new Class<?>[] {});
        JsonObject dueno = leerJson("gps.json").getAsJsonObject("owner");
        h.assertTrue(dueno != null, "con el dueño en el mundo, gps.json lleva el bloque 'owner'");
        h.assertTrue(dueno.get("food").getAsInt() == 5, "food: " + dueno);
        h.assertTrue(dueno.get("air").getAsInt() == 60 && dueno.get("max_air").getAsInt() == 300, "air / max_air: " + dueno);
        h.assertTrue(dueno.get("on_fire").getAsBoolean(), "on_fire debe ser true: " + dueno);
        h.assertTrue(dueno.get("free_slots").getAsInt() == 2, "free_slots debe ser 2 (34 de 36 llenos): " + dueno);
        h.assertTrue(dueno.has("armor") && dueno.has("saturation") && dueno.has("hp") && dueno.has("name"), "y conserva sus campos de siempre más armor y saturation: " + dueno);
        p.discard();
        h.succeed();
    }

    @GameTest(template = PLANTILLA)
    public static void lote_vacio_o_sin_array_no_rompe_nada(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crear(h, new BlockPos(1, Y, 1));
        escribir("command.json", "[{\"action\": \"place_blocks\", \"bot_id\": \"" + NoxCuerpo.BOT_ID + "\"}]");
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        JsonObject fb = leerJson("build_feedback.json");
        h.assertTrue("failed".equals(fb.get("status").getAsString()) && fb.get("total").getAsInt() == 0, "un lote sin bloques es 'failed' con total 0 (no un éxito inventado): " + fb);
        h.assertTrue(e.isAlive(), "Cobalt sigue vivo");
        h.succeed();
    }
}
