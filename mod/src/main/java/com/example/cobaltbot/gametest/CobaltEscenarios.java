package com.example.cobaltbot.gametest;

import com.example.cobaltbot.entity.CobaltDroneEntity;
import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.util.NoxArboles;
import com.example.cobaltbot.util.NoxCuerpo;
import com.example.cobaltbot.util.NoxRutas;
import com.google.gson.JsonObject;
import net.minecraft.core.BlockPos;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.monster.Husk;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.LeavesBlock;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;

import static com.example.cobaltbot.gametest.CobaltGameTests.PLANTILLA;
import static com.example.cobaltbot.gametest.CobaltGameTests.Y;
import static com.example.cobaltbot.gametest.CobaltGameTests.campo;
import static com.example.cobaltbot.gametest.CobaltGameTests.config;
import static com.example.cobaltbot.gametest.CobaltGameTests.crear;
import static com.example.cobaltbot.gametest.CobaltGameTests.cuantos;
import static com.example.cobaltbot.gametest.CobaltGameTests.escribir;
import static com.example.cobaltbot.gametest.CobaltGameTests.inventario;
import static com.example.cobaltbot.gametest.CobaltGameTests.invocar;
import static com.example.cobaltbot.gametest.CobaltGameTests.leerJson;

/** ESCENARIOS de comportamiento de Cobalt en un servidor real: cada uno manda la orden como lo haría Python. */
@GameTestHolder("cobaltmod")
@PrefixGameTestTemplate(false)
public class CobaltEscenarios {

    static ServerPlayer dueno(GameTestHelper h, CobaltEntity e, double x, double z) {
        ServerPlayer p = net.minecraftforge.common.util.FakePlayerFactory.get(h.getLevel(), new com.mojang.authlib.GameProfile(java.util.UUID.randomUUID(), "cobalt-test-owner"));
        Vec3 pos = h.absoluteVec(new Vec3(x, Y, z));
        p.moveTo(pos.x, pos.y, pos.z, 0.0F, 0.0F);
        h.getLevel().addFreshEntity(p);
        e.setOwnerUUID(p.getUUID());
        return p;
    }

    static void enviar(CobaltEntity e, String accionJson) throws Exception {
        String json = accionJson.trim();
        json = json.substring(0, json.length() - 1) + ", \"movement_mode\": \"walk\", \"bot_id\": \"" + NoxCuerpo.BOT_ID + "\"}";
        escribir("command.json", "[" + json + "]");
        invocar(e, "leerComandosDePython", new Class<?>[] {});
    }

    static boolean flag(CobaltEntity e, String nombre) {
        try {
            return (boolean) campo(e, nombre);
        } catch (Exception ex) {
            return false;
        }
    }

    static int cuantosC(Container c, Item item) {
        int n = 0;
        for (int i = 0; i < c.getContainerSize(); i++) if (c.getItem(i).is(item)) n += c.getItem(i).getCount();
        return n;
    }

    static CobaltEntity crearLimpio(GameTestHelper h, BlockPos rel) {
        CobaltGameTests.purgarMundo(h.getLevel());
        return crear(h, rel);
    }

    static void exitoCuando(GameTestHelper h, ServerPlayer p, Runnable comprobacion) {
        h.succeedWhen(() -> {
            comprobacion.run();
            if (p != null) p.discard();
        });
    }

    static void sinFeedback(String archivo) {
        NoxRutas.archivo(archivo).delete();
    }

    static JsonObject feedback(GameTestHelper h, String archivo) {
        h.assertTrue(NoxRutas.archivo(archivo).exists(), archivo + " aún no existe (Python no sabría cómo acabó la tarea)");
        try {
            return leerJson(archivo);
        } catch (Exception ex) {
            h.assertTrue(false, archivo + " ilegible: " + ex);
            return null;
        }
    }

    static String coord(GameTestHelper h, int x, int z) {
        BlockPos a = h.absolutePos(new BlockPos(x, Y, z));
        return "\"x\": " + a.getX() + ", \"y\": " + a.getY() + ", \"z\": " + a.getZ();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400, batch = "movimiento_sigue_al_dueno")
    public static void sigue_al_dueno(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        ServerPlayer p = dueno(h, e, 7.5, 7.5);
        enviar(e, "{\"action\": \"follow\"}");
        exitoCuando(h, p, () -> h.assertTrue(e.distanceTo(p) < 5.0F, "tras 'follow' Cobalt debe acercarse al dueño (distancia " + e.distanceTo(p) + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400, batch = "movimiento_ven_va_a_donde_estas_el_")
    public static void ven_va_a_donde_estas_el_dueno(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        ServerPlayer p = dueno(h, e, 7.5, 7.5);
        enviar(e, "{\"action\": \"ven\"}");
        exitoCuando(h, p, () -> h.assertTrue(e.distanceTo(p) < 4.0F, "tras 'ven' Cobalt debe llegar junto al dueño (distancia " + e.distanceTo(p) + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400, batch = "movimiento_go_to_llega_al_destino")
    public static void go_to_llega_al_destino(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        Vec3 destino = h.absoluteVec(new Vec3(7.5, Y, 3.5));
        enviar(e, "{\"action\": \"go_to\", " + coord(h, 7, 3) + "}");
        h.succeedWhen(() -> h.assertTrue(e.position().distanceTo(destino) < 2.5D, "tras go_to Cobalt debe llegar al destino (a " + e.position().distanceTo(destino) + " bloques)"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 500, batch = "halt")
    public static void halt_all_congela_y_resume_reanuda(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        Vec3 inicio = e.position();
        Vec3 destino = h.absoluteVec(new Vec3(7.5, Y, 1.5));
        BlockPos hueco = new BlockPos(2, Y, 1);
        inventario(e).addItem(new ItemStack(Items.COBBLESTONE, 4));
        escribir("command.json", "HALT_ALL");
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.startSequence().thenExecute(() -> {
            try {
                enviar(e, "{\"action\": \"go_to\", " + coord(h, 7, 1) + "}");
                // congelado no obedece NADA (no solo el movimiento): tampoco construye
                BlockPos a = h.absolutePos(hueco);
                enviar(e, "{\"action\": \"place_block\", \"x\": " + a.getX() + ", \"y\": " + a.getY() + ", \"z\": " + a.getZ() + ", \"block\": \"minecraft:cobblestone\"}");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenIdle(60).thenExecute(() -> h.assertTrue(e.position().distanceTo(inicio) < 1.0D, "congelado: NO debe moverse aunque le manden ir a un sitio (se movió " + e.position().distanceTo(inicio) + ")"))
                .thenExecute(() -> h.assertBlockNotPresent(Blocks.COBBLESTONE, hueco))
                .thenExecute(() -> {
                    try {
                        enviar(e, "{\"action\": \"resume\"}");
                        enviar(e, "{\"action\": \"go_to\", " + coord(h, 7, 1) + "}");
                    } catch (Exception ex) {
                        h.fail("excepción inesperada: " + ex);
                    }
                }).thenWaitUntil(() -> h.assertTrue(e.position().distanceTo(destino) < 2.5D, "tras 'resume' debe obedecer y llegar (a " + e.position().distanceTo(destino) + ")")).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 700, batch = "combate_defender")
    public static void defiende_y_derrota_a_un_hostil(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        Husk husk = h.spawn(EntityType.HUSK, new BlockPos(6, Y, 6));
        enviar(e, "{\"action\": \"defend\"}");
        h.succeedWhen(() -> h.assertTrue(!husk.isAlive() || husk.getHealth() < husk.getMaxHealth() * 0.5F, "tras 'defend' el hostil debe recibir daño serio (vida " + husk.getHealth() + "/" + husk.getMaxHealth() + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 700, batch = "combate_auto")
    public static void ataca_solo_a_un_hostil_cercano_sin_orden(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        Husk husk = h.spawn(EntityType.HUSK, new BlockPos(5, Y, 5));
        h.succeedWhen(() -> h.assertTrue(!husk.isAlive() || husk.getHealth() < husk.getMaxHealth(), "sin ninguna orden, Cobalt debe defenderse de un hostil cercano (vida " + husk.getHealth() + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 500, batch = "combate_plasma")
    public static void dispara_plasma_con_linea_de_vista(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        Husk husk = h.spawn(EntityType.HUSK, new BlockPos(7, Y, 1));
        husk.setNoAi(true); // quieto: se comprueba el disparo, no la persecución
        enviar(e, "{\"action\": \"shoot_plasma\"}");
        h.succeedWhen(() -> h.assertTrue(!husk.isAlive() || husk.getHealth() < husk.getMaxHealth(), "shoot_plasma debe dañar al objetivo con línea de vista (vida " + husk.getHealth() + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "combate_emp")
    public static void pulso_emp_daña_frena_y_empuja(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(4, Y, 4));
        Husk a = h.spawn(EntityType.HUSK, new BlockPos(2, Y, 4));
        Husk b = h.spawn(EntityType.HUSK, new BlockPos(6, Y, 4));
        a.setNoAi(true);
        b.setNoAi(true);
        enviar(e, "{\"action\": \"special_power\"}");
        h.runAfterDelay(5, () -> {
            h.assertTrue(a.getHealth() <= a.getMaxHealth() - 11.0F && b.getHealth() <= b.getMaxHealth() - 11.0F, "el EMP hace 12 de daño en radio 7 (vidas " + a.getHealth() + " y " + b.getHealth() + ")");
            h.assertTrue(a.hasEffect(MobEffects.MOVEMENT_SLOWDOWN) && b.hasEffect(MobEffects.MOVEMENT_SLOWDOWN), "y los frena");
            h.succeed();
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 800, batch = "combate_curarse")
    public static void se_cura_solo_con_comida_o_regeneracion(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(2, Y, 2));
        inventario(e).addItem(new ItemStack(Items.BREAD, 8));
        e.setHealth(6.0F);
        h.succeedWhen(() -> h.assertTrue(e.getHealth() > 12.0F, "con comida y sin combate Cobalt debe recuperar vida (vida " + e.getHealth() + "/" + e.getMaxHealth() + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "combate_critica")
    public static void con_vida_critica_entra_en_modo_huida(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(4, Y, 4));
        h.spawn(EntityType.HUSK, new BlockPos(6, Y, 6));
        e.setHealth(4.0F); // 20 % de 20: por debajo del 30 % crítico
        h.succeedWhen(() -> h.assertTrue(flag(e, "vidaCriticaActiva"), "con la vida por debajo del 30 % Cobalt debe activar la vida crítica"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "drones")
    public static void despliega_y_retira_el_enjambre_de_drones(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(4, Y, 4));
        AABB area = new AABB(e.blockPosition()).inflate(40.0D);
        enviar(e, "{\"action\": \"deploy_drones\"}");
        h.startSequence().thenIdle(10).thenExecute(() -> {
            int n = h.getLevel().getEntitiesOfClass(CobaltDroneEntity.class, area).size();
            h.assertTrue(n >= 3, "deploy_drones debe soltar el enjambre (hay " + n + " drones)");
        }).thenExecute(() -> {
            try {
                enviar(e, "{\"action\": \"recall_drones\"}");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenWaitUntil(() -> {
            int n = h.getLevel().getEntitiesOfClass(CobaltDroneEntity.class, area).size();
            h.assertTrue(n == 0, "recall_drones debe retirarlos todos (quedan " + n + ")");
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "logistica_guarda_en_el_cofre_y_se_")
    public static void guarda_en_el_cofre_y_se_queda_con_herramientas_y_comida(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        BlockPos cofre = new BlockPos(4, Y, 4);
        h.setBlock(cofre, Blocks.CHEST);
        inventario(e).addItem(new ItemStack(Items.COBBLESTONE, 64));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        inventario(e).addItem(new ItemStack(Items.BREAD, 8));
        enviar(e, "{\"action\": \"store\"}");
        h.succeedWhen(() -> {
            Container c = (Container) h.getBlockEntity(cofre);
            h.assertTrue(cuantosC(c, Items.COBBLESTONE) == 64, "el cofre debe recibir la piedra (tiene " + cuantosC(c, Items.COBBLESTONE) + ")");
            h.assertTrue(cuantos(inventario(e), Items.IRON_PICKAXE) == 1 && cuantos(inventario(e), Items.BREAD) == 8, "y Cobalt conserva el pico y la comida");
            h.assertTrue(cuantos(inventario(e), Items.COBBLESTONE) == 0, "sin piedra en el inventario");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "logistica_reabastece_material_de_u")
    public static void reabastece_material_de_un_cofre(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        BlockPos cofre = new BlockPos(4, Y, 4);
        h.setBlock(cofre, Blocks.CHEST);
        ((Container) h.getBlockEntity(cofre)).setItem(0, new ItemStack(Items.OAK_PLANKS, 32));
        enviar(e, "{\"action\": \"restock\", \"material\": \"minecraft:oak_planks\", \"amount\": 16}");
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.OAK_PLANKS) >= 16, "restock debe traer 16 tablas del cofre (trajo " + cuantos(inventario(e), Items.OAK_PLANKS) + ")");
            h.assertTrue(cuantosC((Container) h.getBlockEntity(cofre), Items.OAK_PLANKS) == 16, "y el cofre debe quedarse con las otras 16 (no se duplican: tiene " + cuantosC((Container) h.getBlockEntity(cofre), Items.OAK_PLANKS) + ")");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "logistica_da_material_al_dueno")
    public static void da_material_al_dueno(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        ServerPlayer p = dueno(h, e, 5.5, 5.5);
        inventario(e).addItem(new ItemStack(Items.IRON_INGOT, 10));
        enviar(e, "{\"action\": \"give\", \"material\": \"minecraft:iron_ingot\", \"amount\": 5}");
        exitoCuando(h, p, () -> h.assertTrue(cuantos(inventario(e), Items.IRON_INGOT) <= 5, "give debe entregar 5 lingotes (le quedan " + cuantos(inventario(e), Items.IRON_INGOT) + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "logistica_recoge_objetos_del_suelo")
    public static void recoge_objetos_del_suelo(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        for (int i = 0; i < 3; i++) h.spawnItem(Items.DIAMOND, 5.5F, Y, 5.5F);
        sinFeedback("pickup_feedback.json");
        enviar(e, "{\"action\": \"pickup\", \"radius\": 10}");
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.DIAMOND) >= 3, "pickup debe recoger los 3 diamantes (recogió " + cuantos(inventario(e), Items.DIAMOND) + ")");
            JsonObject fb = feedback(h, "pickup_feedback.json");
            h.assertTrue(fb.get("picked").getAsInt() == 3 && "success".equals(fb.get("status").getAsString()), "pickup_feedback.json debe decir 3 recogidos con éxito: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 900, batch = "oficios_cosecha_trigo_maduro_y_l")
    public static void cosecha_trigo_maduro_y_lo_replanta(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        BlockPos[] cultivos = {new BlockPos(4, Y, 4), new BlockPos(5, Y, 4), new BlockPos(6, Y, 4)};
        h.setBlock(new BlockPos(5, Y + 2, 4), Blocks.GLOWSTONE);
        for (BlockPos c : cultivos) h.setBlock(c.below(), Blocks.FARMLAND);
        h.startSequence().thenIdle(10).thenExecute(() -> {
            for (BlockPos c : cultivos) h.setBlock(c, Blocks.WHEAT.defaultBlockState().setValue(CropBlock.AGE, 7));
        }).thenIdle(2).thenExecute(() -> {
            for (BlockPos c : cultivos) h.assertBlockState(c, s -> s.is(Blocks.WHEAT) && s.getValue(CropBlock.AGE) == 7, () -> "montaje del test: el trigo maduro debe seguir en pie antes de dar la orden");
            try {
                enviar(e, "{\"action\": \"harvest\", \"radius\": 8}");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenWaitUntil(() -> {
            StringBuilder desc = new StringBuilder();
            for (BlockPos c : cultivos) desc.append(h.getBlockState(c).getBlock().getName().getString()).append("/").append(h.getBlockState(c.below()).getBlock().getName().getString()).append(" ");
            for (BlockPos c : cultivos) {
                h.assertBlockState(c, s -> s.is(Blocks.WHEAT) && s.getValue(CropBlock.AGE) == 0, () -> "el cultivo maduro debe cosecharse y replantarse (semilla nueva, edad 0). Estado (cultivo/suelo): " + desc + " | trigo en inventario: " + cuantos(inventario(e), Items.WHEAT) + " semillas: " + cuantos(inventario(e), Items.WHEAT_SEEDS));
            }
            h.assertTrue(cuantos(inventario(e), Items.WHEAT) >= 3, "y quedarse con el trigo (tiene " + cuantos(inventario(e), Items.WHEAT) + ")");
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1500, batch = "oficios_mina_mena_de_hierro_a_la")
    public static void mina_mena_de_hierro_a_la_vista(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        h.setBlock(new BlockPos(5, Y, 3), Blocks.IRON_ORE);
        h.setBlock(new BlockPos(6, Y, 3), Blocks.IRON_ORE);
        sinFeedback("mine_feedback.json");
        enviar(e, "{\"action\": \"mine\", \"material\": \"minecraft:iron_ore\", \"amount\": 2}");
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.RAW_IRON) >= 2, "mine debe conseguir 2 de hierro en bruto (tiene " + cuantos(inventario(e), Items.RAW_IRON) + ")");
            h.assertBlockNotPresent(Blocks.IRON_ORE, new BlockPos(5, Y, 3));
            h.assertBlockNotPresent(Blocks.IRON_ORE, new BlockPos(6, Y, 3));
            JsonObject fb = feedback(h, "mine_feedback.json");
            h.assertTrue(fb.get("mined").getAsInt() == 2 && "success".equals(fb.get("status").getAsString()), "mine_feedback.json debe decir 2 minados con éxito: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 800, batch = "oficios_limpia_una_zona_de_tierr")
    public static void limpia_una_zona_de_tierra(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        for (int x = 4; x <= 6; x++) for (int z = 4; z <= 6; z++) for (int y = Y; y <= Y + 1; y++) h.setBlock(new BlockPos(x, y, z), Blocks.DIRT);
        BlockPos a = h.absolutePos(new BlockPos(4, Y, 4)), b = h.absolutePos(new BlockPos(6, Y + 1, 6));
        enviar(e, "{\"action\": \"clear_area\", \"x1\": " + a.getX() + ", \"y1\": " + a.getY() + ", \"z1\": " + a.getZ() + ", \"x2\": " + b.getX() + ", \"y2\": " + b.getY() + ", \"z2\": " + b.getZ() + "}");
        h.succeedWhen(() -> {
            for (int x = 4; x <= 6; x++) for (int z = 4; z <= 6; z++) for (int y = Y; y <= Y + 1; y++) h.assertBlockNotPresent(Blocks.DIRT, new BlockPos(x, y, z));
        });
    }

    static void plantarArbol(GameTestHelper h, int x, int z, int altura) {
        h.setBlock(new BlockPos(x, Y - 1, z), Blocks.DIRT);
        for (int i = 0; i < altura; i++) h.setBlock(new BlockPos(x, Y + i, z), Blocks.OAK_LOG);
        for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++) for (int dy = altura - 1; dy <= altura; dy++) {
            if (dx == 0 && dz == 0 && dy == altura - 1) continue;
            h.setBlock(new BlockPos(x + dx, Y + dy, z + dz), Blocks.OAK_LEAVES.defaultBlockState().setValue(LeavesBlock.DISTANCE, 1));
        }
    }

    static void cabanaDeTroncos(GameTestHelper h, int x, int z) {
        for (int i = 0; i < 3; i++) {
            h.setBlock(new BlockPos(x + i, Y - 1, z), Blocks.DIRT);
            h.setBlock(new BlockPos(x + i, Y, z), Blocks.OAK_LOG);
        }
        h.setBlock(new BlockPos(x + 1, Y + 1, z), Blocks.OAK_LEAVES.defaultBlockState().setValue(LeavesBlock.PERSISTENT, true));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 100, batch = "arboles_distingue_arbol_de_cabana")
    public static void un_arbol_es_un_arbol_y_una_cabana_de_troncos_no(GameTestHelper h) {
        plantarArbol(h, 5, 5, 4);
        cabanaDeTroncos(h, 1, 1);
        h.setBlock(new BlockPos(1, Y, 4), Blocks.OAK_LOG); // un tronco suelto sobre tierra, sin hojas
        h.setBlock(new BlockPos(1, Y - 1, 4), Blocks.DIRT);
        h.setBlock(new BlockPos(3, Y, 7), Blocks.OAK_LOG);
        h.setBlock(new BlockPos(3, Y - 1, 7), Blocks.STONE);
        h.setBlock(new BlockPos(3, Y + 1, 7), Blocks.OAK_LEAVES.defaultBlockState().setValue(LeavesBlock.DISTANCE, 1));
        var nivel = h.getLevel();
        h.assertTrue(NoxArboles.arbol(nivel, h.absolutePos(new BlockPos(5, Y + 2, 5))).size() == 4, "el roble tiene 4 troncos (salen " + NoxArboles.arbol(nivel, h.absolutePos(new BlockPos(5, Y + 2, 5))).size() + ")");
        h.assertTrue(NoxArboles.arbol(nivel, h.absolutePos(new BlockPos(5, Y + 2, 5))).get(0).equals(h.absolutePos(new BlockPos(5, Y, 5))), "y se ordenan de abajo arriba");
        h.assertTrue(NoxArboles.arbol(nivel, h.absolutePos(new BlockPos(1, Y, 1))).isEmpty(), "la cabaña de troncos (con hojas persistentes) NO es un árbol");
        h.assertTrue(NoxArboles.arbol(nivel, h.absolutePos(new BlockPos(1, Y, 4))).isEmpty(), "un tronco suelto sin hojas NO es un árbol");
        h.assertTrue(NoxArboles.arbol(nivel, h.absolutePos(new BlockPos(3, Y, 7))).isEmpty(), "unos troncos sobre piedra sin hojas NO son un árbol");
        h.assertTrue(NoxArboles.arbol(nivel, h.absolutePos(new BlockPos(5, Y - 1, 5))).isEmpty(), "un bloque que no es tronco no es un árbol");
        BlockPos colArbol = h.absolutePos(new BlockPos(5, Y, 5)), colCabana = h.absolutePos(new BlockPos(2, Y, 1));
        h.assertTrue(com.example.cobaltbot.util.NoxTerreno.superficie(nivel, colArbol.getX(), colArbol.getZ(), colArbol.getY() + 8, colArbol.getY() - 1)[1] == com.example.cobaltbot.util.NoxTerreno.SUELO,
                "al medir el relieve, la columna de un árbol es terreno natural (se puede despejar)");
        h.assertTrue(com.example.cobaltbot.util.NoxTerreno.superficie(nivel, colCabana.getX(), colCabana.getZ(), colCabana.getY() + 8, colCabana.getY() - 1)[1] == com.example.cobaltbot.util.NoxTerreno.OBSTACULO,
                "y la de una cabaña de troncos es un obstáculo");
        h.succeed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1200, batch = "oficios_tala_un_arbol_no_una_cabana")
    public static void tala_un_arbol_entero_pero_no_una_cabana_de_troncos(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_AXE, 1));
        plantarArbol(h, 5, 5, 4);
        cabanaDeTroncos(h, 1, 4); // más cerca de Cobalt que el árbol: si no distingue, talaría esto primero
        sinFeedback("chop_feedback.json");
        enviar(e, "{\"action\": \"chop_wood\", \"radius\": 12, \"amount\": 4}");
        h.succeedWhen(() -> {
            for (int i = 0; i < 4; i++) h.assertBlockNotPresent(Blocks.OAK_LOG, new BlockPos(5, Y + i, 5));
            h.assertTrue(cuantos(inventario(e), Items.OAK_LOG) == 4, "los 4 troncos del árbol acaban en el inventario (tiene " + cuantos(inventario(e), Items.OAK_LOG) + ")");
            h.assertTrue(inventario(e).getItem(0).getDamageValue() > 0, "y el hacha se desgasta al talar");
            for (int i = 0; i < 3; i++) h.assertBlockPresent(Blocks.OAK_LOG, new BlockPos(1 + i, Y, 4)); // la cabaña, intacta
            JsonObject fb = feedback(h, "chop_feedback.json");
            h.assertTrue("success".equals(fb.get("status").getAsString()) && fb.get("chopped").getAsInt() == 4 && fb.get("trees").getAsInt() == 1, "chop_feedback.json: 4 troncos, 1 árbol, éxito: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 500, batch = "oficios_tala_sin_arboles_dice_que_no")
    public static void si_solo_hay_una_cabana_de_troncos_no_talan_nada_y_lo_dice(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_AXE, 1));
        cabanaDeTroncos(h, 3, 4);
        sinFeedback("chop_feedback.json");
        enviar(e, "{\"action\": \"chop_wood\", \"radius\": 12, \"amount\": 3}");
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "chop_feedback.json");
            h.assertTrue("failed".equals(fb.get("status").getAsString()) && fb.get("chopped").getAsInt() == 0, "sin árboles: fallo y 0 talados: " + fb);
            for (int i = 0; i < 3; i++) h.assertBlockPresent(Blocks.OAK_LOG, new BlockPos(3 + i, Y, 4));
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 500, batch = "oficios_tala_apagada")
    public static void con_tala_apagada_no_tala(GameTestHelper h) throws Exception {
        config("{\"tala\": false}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_AXE, 1));
        plantarArbol(h, 4, 4, 3);
        sinFeedback("chop_feedback.json");
        enviar(e, "{\"action\": \"chop_wood\", \"radius\": 12, \"amount\": 3}");
        h.startSequence().thenIdle(120).thenExecute(() -> {
            h.assertBlockPresent(Blocks.OAK_LOG, new BlockPos(4, Y, 4));
            h.assertTrue(!NoxRutas.archivo("chop_feedback.json").exists(), "con tala=false no hay tarea de talar (solo el comportamiento de antes: mirar si hay hacha)");
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1200, batch = "oficios_mina_hierro_con_pico_de_oro_y_hierro")
    public static void con_un_pico_de_oro_y_otro_de_hierro_usa_el_de_hierro_para_la_mena_de_hierro(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.GOLDEN_PICKAXE, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        h.setBlock(new BlockPos(5, Y, 3), Blocks.IRON_ORE);
        sinFeedback("mine_feedback.json");
        enviar(e, "{\"action\": \"mine\", \"material\": \"minecraft:iron_ore\", \"amount\": 1}");
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.RAW_IRON) >= 1, "debe sacar el hierro con el pico de hierro (tiene " + cuantos(inventario(e), Items.RAW_IRON) + " de hierro en bruto)");
            h.assertBlockNotPresent(Blocks.IRON_ORE, new BlockPos(5, Y, 3));
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1200, batch = "oficios_mena_muy_por_encima")
    public static void alcanza_una_mena_muy_por_encima_de_su_cabeza_volando(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        h.setBlock(new BlockPos(5, Y + 8, 3), Blocks.IRON_ORE); // flotando a 8 bloques: andando no se llega ni se alcanza desde el suelo
        sinFeedback("mine_feedback.json");
        enviar(e, "{\"action\": \"mine\", \"material\": \"minecraft:iron_ore\", \"amount\": 1}");
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.RAW_IRON) >= 1, "debe volar hasta la mena y sacarla (tiene " + cuantos(inventario(e), Items.RAW_IRON) + ")");
            h.assertBlockNotPresent(Blocks.IRON_ORE, new BlockPos(5, Y + 8, 3));
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 500, batch = "oficios_obsidiana_con_pico_de_hierro")
    public static void un_pico_de_hierro_no_rompe_la_obsidiana(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        h.setBlock(new BlockPos(5, Y, 3), Blocks.OBSIDIAN);
        sinFeedback("mine_feedback.json");
        enviar(e, "{\"action\": \"mine\", \"material\": \"minecraft:obsidian\", \"amount\": 1}");
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "mine_feedback.json"); // la tarea ya acabó
            h.assertTrue(!"success".equals(fb.get("status").getAsString()), "con un pico de hierro NO se consigue la obsidiana: " + fb);
            h.assertBlockPresent(Blocks.OBSIDIAN, new BlockPos(5, Y, 3));
            h.assertTrue(cuantos(inventario(e), Items.OBSIDIAN) == 0, "y no gasta el pico ni suelta nada");
            h.assertTrue(inventario(e).getItem(0).getDamageValue() == 0, "el pico de hierro no se desgasta intentándolo");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1200, batch = "oficios_obsidiana_con_pico_de_diamante")
    public static void un_pico_de_diamante_si_rompe_la_obsidiana(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1)); // con este de compañero: elige el de diamante
        inventario(e).addItem(new ItemStack(Items.DIAMOND_PICKAXE, 1));
        h.setBlock(new BlockPos(5, Y, 3), Blocks.OBSIDIAN);
        sinFeedback("mine_feedback.json");
        enviar(e, "{\"action\": \"mine\", \"material\": \"minecraft:obsidian\", \"amount\": 1}");
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.OBSIDIAN) >= 1, "con pico de diamante sí saca la obsidiana (tiene " + cuantos(inventario(e), Items.OBSIDIAN) + ")");
            h.assertBlockNotPresent(Blocks.OBSIDIAN, new BlockPos(5, Y, 3));
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1200, batch = "oficios_despeja_una_zona_con_arbol")
    public static void al_despejar_una_zona_se_lleva_el_arbol_pero_no_la_cabana(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_AXE, 1));
        plantarArbol(h, 5, 5, 3);
        cabanaDeTroncos(h, 3, 2);
        BlockPos a = h.absolutePos(new BlockPos(2, Y, 2)), b = h.absolutePos(new BlockPos(7, Y + 4, 7));
        enviar(e, "{\"action\": \"clear_area\", \"x1\": " + a.getX() + ", \"y1\": " + a.getY() + ", \"z1\": " + a.getZ() + ", \"x2\": " + b.getX() + ", \"y2\": " + b.getY() + ", \"z2\": " + b.getZ() + "}");
        h.succeedWhen(() -> {
            for (int i = 0; i < 3; i++) h.assertBlockNotPresent(Blocks.OAK_LOG, new BlockPos(5, Y + i, 5));
            for (int i = 0; i < 3; i++) h.assertBlockPresent(Blocks.OAK_LOG, new BlockPos(3 + i, Y, 2));
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1200, batch = "oficios_aplana_una_zona_con_arbol")
    public static void al_aplanar_se_lleva_el_arbol_pero_no_la_cabana_de_troncos(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_AXE, 1));
        for (int x = 3; x <= 7; x++) for (int z = 2; z <= 7; z++) for (int y = Y - 2; y <= Y - 1; y++) h.setBlock(new BlockPos(x, y, z), Blocks.DIRT); // suelo natural a nivel
        plantarArbol(h, 5, 5, 3);
        cabanaDeTroncos(h, 4, 3);
        BlockPos a = h.absolutePos(new BlockPos(4, Y - 1, 3)), b = h.absolutePos(new BlockPos(6, Y - 1, 6));
        enviar(e, "{\"action\": \"flatten_area\", \"x1\": " + a.getX() + ", \"z1\": " + a.getZ() + ", \"x2\": " + b.getX() + ", \"z2\": " + b.getZ() + ", \"y\": " + a.getY() + "}");
        h.succeedWhen(() -> {
            for (int i = 0; i < 3; i++) h.assertBlockNotPresent(Blocks.OAK_LOG, new BlockPos(5, Y + i, 5));
            for (int i = 0; i < 3; i++) h.assertBlockPresent(Blocks.OAK_LOG, new BlockPos(4 + i, Y, 3)); // la columna de la cabaña se deja como estaba
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1200, batch = "oficios_tala_no_toca_troncos_junto_a_lava")
    public static void no_tala_un_tronco_pegado_a_la_lava(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_AXE, 1));
        plantarArbol(h, 5, 5, 3);
        h.setBlock(new BlockPos(6, Y, 5), Blocks.OBSIDIAN); // contención: la lava no se extiende hacia Cobalt durante la prueba
        h.setBlock(new BlockPos(5, Y, 4), Blocks.LAVA);      // pegada al tronco de más abajo (y solo a ese)
        for (BlockPos vecino : new BlockPos[] {new BlockPos(4, Y, 4), new BlockPos(6, Y, 4), new BlockPos(5, Y, 3), new BlockPos(5, Y - 1, 4)}) h.setBlock(vecino, Blocks.OBSIDIAN);
        h.setBlock(new BlockPos(4, Y, 5), Blocks.DIRT);
        sinFeedback("chop_feedback.json");
        enviar(e, "{\"action\": \"chop_wood\", \"radius\": 12, \"amount\": 3}");
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "chop_feedback.json");
            h.assertBlockPresent(Blocks.OAK_LOG, new BlockPos(5, Y, 5)); // el pegado a la lava se queda
            h.assertBlockNotPresent(Blocks.OAK_LOG, new BlockPos(5, Y + 1, 5));
            h.assertBlockNotPresent(Blocks.OAK_LOG, new BlockPos(5, Y + 2, 5));
            h.assertTrue("partial".equals(fb.get("status").getAsString()) && fb.get("chopped").getAsInt() == 2 && fb.get("skipped").getAsInt() == 1, "2 talados y 1 omitido por la lava: " + fb);
        });
    }

    static void estanque(GameTestHelper h, int x, int z, boolean tapado) {
        for (int dx = 0; dx < 3; dx++) for (int dz = 0; dz < 3; dz++) {
            h.setBlock(new BlockPos(x + dx, Y - 2, z + dz), Blocks.STONE);
            h.setBlock(new BlockPos(x + dx, Y - 1, z + dz), Blocks.WATER);
            if (tapado) h.setBlock(new BlockPos(x + dx, Y, z + dz), Blocks.STONE);
        }
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 2000, batch = "oficios_pesca_con_cana")
    public static void pesca_con_una_cana_junto_al_agua(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.FISHING_ROD, 1));
        estanque(h, 5, 4, false);
        sinFeedback("fish_feedback.json");
        enviar(e, "{\"action\": \"fish\", \"radius\": 12, \"amount\": 2}");
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "fish_feedback.json");
            h.assertTrue("success".equals(fb.get("status").getAsString()) && fb.get("caught").getAsInt() == 2 && fb.get("wanted").getAsInt() == 2, "fish_feedback.json: 2 capturas con éxito: " + fb);
            int piezas = 0;
            for (var entrada : fb.getAsJsonObject("items").entrySet()) piezas += entrada.getValue().getAsInt();
            h.assertTrue(piezas >= 2, "y el botín aparece en el feedback (" + fb.get("items") + ")");
            int enInventario = 0;
            for (int i = 1; i < inventario(e).getContainerSize(); i++) enInventario += inventario(e).getItem(i).getCount();
            h.assertTrue(enInventario >= 2, "y está en el inventario de Cobalt (" + enInventario + " piezas)");
            h.assertTrue(inventario(e).getItem(0).is(Items.FISHING_ROD) && inventario(e).getItem(0).getDamageValue() >= 2, "y la caña se desgasta con cada captura (daño " + inventario(e).getItem(0).getDamageValue() + ")");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400, batch = "oficios_pesca_sin_cana")
    public static void sin_cana_no_pesca_y_lo_dice(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        estanque(h, 5, 4, false);
        sinFeedback("fish_feedback.json");
        enviar(e, "{\"action\": \"fish\", \"radius\": 12, \"amount\": 2}");
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "fish_feedback.json");
            h.assertTrue("failed".equals(fb.get("status").getAsString()) && fb.get("detalle").getAsString().contains("caña"), "sin caña: fallo que pide una caña: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400, batch = "oficios_pesca_sin_agua_abierta")
    public static void con_el_agua_tapada_no_hay_donde_pescar(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.FISHING_ROD, 1));
        estanque(h, 5, 4, true); // agua con techo: sin superficie
        sinFeedback("fish_feedback.json");
        enviar(e, "{\"action\": \"fish\", \"radius\": 12, \"amount\": 2}");
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "fish_feedback.json");
            h.assertTrue("failed".equals(fb.get("status").getAsString()) && fb.get("detalle").getAsString().contains("agua") && fb.get("caught").getAsInt() == 0, "agua tapada: no pesca y dice que no hay agua: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "oficios_pesca_apagada")
    public static void con_pesca_apagada_no_pesca(GameTestHelper h) throws Exception {
        config("{\"pesca\": false}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.FISHING_ROD, 1));
        estanque(h, 5, 4, false);
        sinFeedback("fish_feedback.json");
        enviar(e, "{\"action\": \"fish\", \"radius\": 12, \"amount\": 2}");
        h.startSequence().thenIdle(60).thenExecute(() -> {
            JsonObject fb = feedback(h, "fish_feedback.json");
            h.assertTrue("disabled".equals(fb.get("status").getAsString()), "con pesca=false lo dice y no pesca: " + fb);
            try {
                h.assertTrue(!((com.example.cobaltbot.entity.CobaltTareas) campo(e, "tareas")).ocupado(), "y no queda ninguna tarea en curso");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 60, batch = "movimiento_tp_enfriamiento")
    public static void el_tp_cuantico_tarda_120_s_en_volver_a_estar_disponible(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        ServerPlayer p = dueno(h, e, 7.5, 7.5);
        invocar(e, "tpCuantico", new Class<?>[] {net.minecraft.world.entity.player.Player.class, String.class}, p, "prueba");
        int ticks = (int) campo(e, "autoTpCooldown");
        h.assertTrue(ticks == 2400, "el enfriamiento del TP cuántico por defecto es de 120 s = 2400 ticks (tiene " + ticks + ")");
        p.discard();
        h.succeed();
    }

    static void fabricar(GameTestHelper h, CobaltEntity e, String material, int cantidad) throws Exception {
        sinFeedback("craft_feedback.json");
        enviar(e, "{\"action\": \"craft\", \"material\": \"" + material + "\", \"amount\": " + cantidad + "}");
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "crafteo_palos")
    public static void craftea_palos_con_tablones(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_PLANKS, 2));
        fabricar(h, e, "minecraft:stick", 4);
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "craft_feedback.json");
            h.assertTrue("success".equals(fb.get("status").getAsString()) && fb.get("crafted").getAsInt() == 4 && fb.get("steps").getAsInt() == 1, "4 palos con 1 crafteo: " + fb);
            h.assertTrue(cuantos(inventario(e), Items.STICK) == 4 && cuantos(inventario(e), Items.OAK_PLANKS) == 0, "gasta los 2 tablones y tiene 4 palos (" + cuantos(inventario(e), Items.STICK) + " palos, " + cuantos(inventario(e), Items.OAK_PLANKS) + " tablones)");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400, batch = "crafteo_intermedios")
    public static void fabrica_lo_intermedio_que_le_falta_troncos_tablones_palos_pico(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_INGOT, 3));
        inventario(e).addItem(new ItemStack(Items.OAK_LOG, 1));
        fabricar(h, e, "minecraft:iron_pickaxe", 1);
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "craft_feedback.json");
            h.assertTrue("success".equals(fb.get("status").getAsString()) && fb.get("crafted").getAsInt() == 1 && fb.get("steps").getAsInt() == 3, "1 pico en 3 crafteos (tablones, palos, pico) y solo el producto final cuenta: " + fb);
            h.assertTrue(cuantos(inventario(e), Items.IRON_PICKAXE) == 1 && cuantos(inventario(e), Items.IRON_INGOT) == 0 && cuantos(inventario(e), Items.OAK_LOG) == 0, "tiene el pico y gastó lingotes y tronco");
            h.assertTrue(cuantos(inventario(e), Items.OAK_PLANKS) == 2 && cuantos(inventario(e), Items.STICK) == 2, "y sobran 2 tablones y 2 palos (" + cuantos(inventario(e), Items.OAK_PLANKS) + ", " + cuantos(inventario(e), Items.STICK) + ")");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "crafteo_sin_material")
    public static void si_no_le_alcanza_no_gasta_nada_y_dice_que_falta(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_INGOT, 2));
        inventario(e).addItem(new ItemStack(Items.OAK_PLANKS, 2));
        fabricar(h, e, "minecraft:iron_pickaxe", 1);
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "craft_feedback.json");
            h.assertTrue("failed".equals(fb.get("status").getAsString()) && fb.get("detalle").getAsString().contains("faltan"), "falla y dice que faltan cosas: " + fb);
            h.assertTrue(fb.getAsJsonObject("missing").has("minecraft:iron_ingot") && fb.getAsJsonObject("missing").get("minecraft:iron_ingot").getAsInt() == 1, "y qué: 1 lingote de hierro: " + fb.get("missing"));
            h.assertTrue(cuantos(inventario(e), Items.IRON_INGOT) == 2 && cuantos(inventario(e), Items.OAK_PLANKS) == 2 && cuantos(inventario(e), Items.STICK) == 0, "no gasta NADA (ni fabrica los palos a medias)");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "crafteo_sin_mesa_colocada")
    public static void no_necesita_una_mesa_de_crafteo_colocada(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_PLANKS, 4));
        fabricar(h, e, "minecraft:crafting_table", 1); // una receta de 2x2, pero ninguna mesa en todo el mundo de la prueba
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.CRAFTING_TABLE) == 1 && cuantos(inventario(e), Items.OAK_PLANKS) == 0, "fabrica la mesa sin ninguna mesa cerca");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "crafteo_generico_tablones")
    public static void pide_tablones_en_general_y_fabrica_los_de_la_madera_que_tiene(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.SPRUCE_LOG, 1));
        fabricar(h, e, "planks", 4);
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.SPRUCE_PLANKS) == 4 && cuantos(inventario(e), Items.SPRUCE_LOG) == 0, "de un tronco de abeto salen 4 tablones de abeto (los de roble no se pueden): " + cuantos(inventario(e), Items.SPRUCE_PLANKS));
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "crafteo_varios_candidatos")
    public static void si_el_primer_objeto_no_se_puede_fabrica_el_siguiente_de_la_lista(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_INGOT, 3));
        inventario(e).addItem(new ItemStack(Items.STICK, 2));
        fabricar(h, e, "minecraft:diamond_pickaxe,minecraft:iron_pickaxe", 1); // sin diamantes: hace el de hierro
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.IRON_PICKAXE) == 1 && cuantos(inventario(e), Items.DIAMOND_PICKAXE) == 0, "sin diamantes fabrica el de hierro");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "crafteo_sin_forma")
    public static void una_receta_sin_forma_tambien_vale_mechero(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_INGOT, 1));
        inventario(e).addItem(new ItemStack(Items.FLINT, 1));
        fabricar(h, e, "minecraft:flint_and_steel", 1);
        h.succeedWhen(() -> h.assertTrue(cuantos(inventario(e), Items.FLINT_AND_STEEL) == 1 && cuantos(inventario(e), Items.FLINT) == 0, "un mechero con pedernal y hierro"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "crafteo_restos")
    public static void los_cubos_de_leche_de_una_tarta_vuelven_vacios(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.MILK_BUCKET, 3));
        inventario(e).addItem(new ItemStack(Items.SUGAR, 2));
        inventario(e).addItem(new ItemStack(Items.EGG, 1));
        inventario(e).addItem(new ItemStack(Items.WHEAT, 3));
        fabricar(h, e, "minecraft:cake", 1);
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.CAKE) == 1 && cuantos(inventario(e), Items.MILK_BUCKET) == 0, "tiene la tarta y gastó la leche");
            h.assertTrue(cuantos(inventario(e), Items.BUCKET) == 3, "y recupera los 3 cubos vacíos (los restos de la receta): " + cuantos(inventario(e), Items.BUCKET));
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "crafteo_redondeo")
    public static void pide_6_antorchas_y_hace_2_crafteos_de_4(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.COAL, 2));
        inventario(e).addItem(new ItemStack(Items.STICK, 2));
        fabricar(h, e, "minecraft:torch", 6);
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "craft_feedback.json");
            h.assertTrue(cuantos(inventario(e), Items.TORCH) == 8 && cuantos(inventario(e), Items.COAL) == 0 && fb.get("steps").getAsInt() == 2, "para 6 antorchas hace 2 crafteos (8 antorchas): " + cuantos(inventario(e), Items.TORCH) + ", " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "crafteo_demasiados_pasos")
    public static void se_niega_a_un_plan_de_mas_de_64_crafteos_sin_gastar_nada(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_LOG, 64));
        fabricar(h, e, "minecraft:stick", 256); // 64 crafteos de palos + 32 de tablones = 96
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "craft_feedback.json");
            h.assertTrue("failed".equals(fb.get("status").getAsString()) && fb.get("detalle").getAsString().contains("demasiados"), "demasiados pasos: " + fb);
            h.assertTrue(cuantos(inventario(e), Items.OAK_LOG) == 64 && cuantos(inventario(e), Items.STICK) == 0, "y no toca el inventario");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "crafteo_desconocido")
    public static void un_objeto_sin_receta_de_mesa_de_crafteo_falla_y_lo_dice(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_PLANKS, 4));
        fabricar(h, e, "minecraft:bedrock", 1);
        h.succeedWhen(() -> {
            JsonObject fb = feedback(h, "craft_feedback.json");
            h.assertTrue("failed".equals(fb.get("status").getAsString()) && fb.get("detalle").getAsString().contains("no conozco"), "sin receta: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "crafteo_apagado")
    public static void con_crafteo_apagado_no_fabrica_nada(GameTestHelper h) throws Exception {
        config("{\"crafteo\": false}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.OAK_PLANKS, 2));
        fabricar(h, e, "minecraft:stick", 4);
        h.startSequence().thenIdle(40).thenExecute(() -> {
            JsonObject fb = feedback(h, "craft_feedback.json");
            h.assertTrue("disabled".equals(fb.get("status").getAsString()) && cuantos(inventario(e), Items.STICK) == 0 && cuantos(inventario(e), Items.OAK_PLANKS) == 2, "con crafteo=false lo dice y no toca nada: " + fb);
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 300, batch = "sensores")
    public static void los_sensores_describen_al_hostil_al_dueno_y_al_inventario(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(2, Y, 2));
        ServerPlayer p = dueno(h, e, 3.5, 2.5);
        Husk husk = h.spawn(EntityType.HUSK, new BlockPos(7, Y, 7));
        husk.setNoAi(true);
        husk.setInvulnerable(true);
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        h.startSequence().thenIdle(80).thenExecute(() -> {
            try {
                JsonObject ent = leerJson("entities.json");
                boolean hostil = false, dueno = false;
                for (var x : ent.getAsJsonArray("entities")) {
                    JsonObject o = x.getAsJsonObject();
                    if ("hostile".equals(o.get("kind").getAsString()) && o.get("type").getAsString().contains("husk")) hostil = true;
                    if ("player".equals(o.get("kind").getAsString()) && o.has("owner") && o.get("owner").getAsBoolean()) dueno = true;
                }
                h.assertTrue(hostil, "entities.json debe listar al husk como hostil: " + ent);
                h.assertTrue(dueno, "y al dueño como jugador dueño: " + ent);
                h.assertTrue(ent.has("bot") && ent.get("bot_id").getAsString().equals(NoxCuerpo.BOT_ID), "con la posición de Cobalt y su bot_id");
                JsonObject st = leerJson("nox_status.json");
                h.assertTrue(st.has("hp") && st.has("inventory") && st.has("is_deployed"), "nox_status.json con hp, inventory e is_deployed: " + st);
                String radar = java.nio.file.Files.readString(NoxRutas.archivo("vision.json").toPath());
                h.assertTrue(radar.contains("Radar de Hostiles"), "vision.json debe ser el radar de hostiles: " + radar);
                java.io.File contrato = new java.io.File(NoxRutas.dir(), "contrato");
                contrato.mkdirs();
                for (String nombre : new String[] {"gps.json", "entities.json", "nox_status.json", "vision.json", "terreno_sensor.json", "tech_sensor.json", "mods.json"}) {
                    java.io.File origen = NoxRutas.archivo(nombre);
                    if (origen.exists()) java.nio.file.Files.copy(origen.toPath(), new java.io.File(contrato, nombre).toPath(), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                }
                p.discard();
            } catch (java.io.IOException ex) {
                h.fail("excepción inesperada: " + ex);
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "oficios_atiende_hornos")
    public static void atiende_un_horno_recoge_lo_fundido_y_lo_recarga(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        BlockPos horno = new BlockPos(4, Y, 4);
        h.setBlock(horno, Blocks.FURNACE);
        ((Container) h.getBlockEntity(horno)).setItem(2, new ItemStack(Items.IRON_INGOT, 5));
        inventario(e).addItem(new ItemStack(Items.COAL, 8));
        inventario(e).addItem(new ItemStack(Items.RAW_IRON, 8));
        sinFeedback("furnace_feedback.json");
        enviar(e, "{\"action\": \"tend_furnaces\", \"radius\": 8}");
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.IRON_INGOT) >= 5, "tend_furnaces debe recoger los 5 lingotes del horno (tiene " + cuantos(inventario(e), Items.IRON_INGOT) + ")");
            Container f = (Container) h.getBlockEntity(horno);
            h.assertTrue(!f.getItem(0).isEmpty() && !f.getItem(1).isEmpty(), "y recargarlo: mineral en la entrada y carbón en el combustible");
            JsonObject fb = feedback(h, "furnace_feedback.json");
            h.assertTrue(fb.get("collected").getAsInt() >= 5 && "success".equals(fb.get("status").getAsString()), "furnace_feedback.json debe decir lo recogido con éxito: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "guardia_vuelve_a_su_puesto")
    public static void en_guardia_vuelve_a_su_puesto(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(2, Y, 2));
        Vec3 puesto = h.absoluteVec(new Vec3(2.5, Y, 2.5));
        enviar(e, "{\"action\": \"stand_ground\", " + coord(h, 2, 2) + ", \"radius\": 8}");
        h.startSequence().thenIdle(10).thenExecute(() -> {
            Vec3 lejos = h.absoluteVec(new Vec3(7.5, Y, 7.5));
            e.teleportTo(lejos.x, lejos.y, lejos.z); // algo lo aparta del puesto
        }).thenWaitUntil(() -> h.assertTrue(e.position().distanceTo(puesto) < 3.5D, "en guardia, si algo lo aparta debe volver a su puesto (a " + e.position().distanceTo(puesto) + " bloques)")).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "logistica_suelta_objetos")
    public static void suelta_material_pero_nunca_herramientas(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.COBBLESTONE, 10));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        sinFeedback("drop_feedback.json");
        enviar(e, "{\"action\": \"drop\", \"material\": \"minecraft:cobblestone\", \"amount\": 4}");
        enviar(e, "{\"action\": \"drop\", \"material\": \"minecraft:iron_pickaxe\", \"amount\": 1}"); // una herramienta NUNCA se suelta
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.COBBLESTONE) == 6, "debe soltar 4 de 10 (le quedan " + cuantos(inventario(e), Items.COBBLESTONE) + ")");
            h.assertTrue(cuantos(inventario(e), Items.IRON_PICKAXE) == 1, "y conservar el pico aunque se lo pidan");
            int enSuelo = 0;
            for (net.minecraft.world.entity.item.ItemEntity i : h.getLevel().getEntitiesOfClass(net.minecraft.world.entity.item.ItemEntity.class, e.getBoundingBox().inflate(6.0D))) {
                if (i.getItem().is(Items.COBBLESTONE)) enSuelo += i.getItem().getCount();
                h.assertTrue(!i.getItem().is(Items.IRON_PICKAXE), "el pico no debe estar en el suelo");
            }
            h.assertTrue(enSuelo == 4, "los 4 adoquines deben estar en el suelo (hay " + enSuelo + ")");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "supervivencia_use_item")
    public static void bebe_una_pocion_y_recibe_su_efecto(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(net.minecraft.world.item.alchemy.PotionUtils.setPotion(new ItemStack(Items.POTION), net.minecraft.world.item.alchemy.Potions.SWIFTNESS));
        sinFeedback("use_feedback.json");
        enviar(e, "{\"action\": \"use_item\", \"effect\": \"speed\"}");
        h.succeedWhen(() -> {
            h.assertTrue(e.hasEffect(MobEffects.MOVEMENT_SPEED), "tras use_item 'speed' Cobalt debe tener velocidad");
            h.assertTrue(cuantos(inventario(e), Items.POTION) == 0 && cuantos(inventario(e), Items.GLASS_BOTTLE) == 1, "y haber gastado la poción dejando el frasco vacío");
            h.assertTrue("success".equals(feedback(h, "use_feedback.json").get("status").getAsString()), "use_feedback.json debe decir success");
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "bardo_escribe_libro")
    public static void escribe_un_libro_con_titulo_y_paginas(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        sinFeedback("book_feedback.json");
        enviar(e, "{\"action\": \"write_book\", \"title\": \"Cronica\", \"pages\": [\"Primera\", \"Segunda\"], \"give\": \"false\"}");
        h.succeedWhen(() -> {
            ItemStack libro = ItemStack.EMPTY;
            for (int i = 0; i < inventario(e).getContainerSize(); i++) if (inventario(e).getItem(i).is(Items.WRITTEN_BOOK)) libro = inventario(e).getItem(i);
            h.assertTrue(!libro.isEmpty(), "write_book debe dejar un libro escrito en el inventario");
            h.assertTrue("Cronica".equals(libro.getTag().getString("title")) && libro.getTag().getList("pages", 8).size() == 2, "con su título y sus 2 páginas: " + libro.getTag());
            JsonObject fb = feedback(h, "book_feedback.json");
            h.assertTrue("success".equals(fb.get("status").getAsString()) && fb.get("pages").getAsInt() == 2, "book_feedback.json debe decir success con 2 páginas: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "combate_emp_onda")
    public static void el_pulso_emp_crea_la_onda_de_runas_y_la_retira(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(3, Y, 3));
        enviar(e, "{\"action\": \"special_power\"}");
        h.startSequence().thenExecuteAfter(2, () -> {
            int ondas = h.getLevel().getEntitiesOfClass(com.example.cobaltbot.entity.EmpWaveEntity.class, e.getBoundingBox().inflate(3.0D)).size();
            h.assertTrue(ondas == 1, "el pulso EMP debe crear UNA onda de runas junto a Cobalt (hay " + ondas + ")");
        }).thenExecuteAfter(40, () -> {
            int ondas = h.getLevel().getEntitiesOfClass(com.example.cobaltbot.entity.EmpWaveEntity.class, e.getBoundingBox().inflate(3.0D)).size();
            h.assertTrue(ondas == 0, "y la onda debe desaparecer sola (quedan " + ondas + ")");
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "logistica_guarda_solo_lo_pedido")
    public static void guarda_solo_lo_pedido_aunque_sea_comida(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        BlockPos cofre = new BlockPos(4, Y, 4);
        h.setBlock(cofre, Blocks.CHEST);
        inventario(e).addItem(new ItemStack(Items.WHEAT, 10));
        inventario(e).addItem(new ItemStack(Items.CARROT, 5));
        inventario(e).addItem(new ItemStack(Items.BREAD, 4));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        inventario(e).addItem(new ItemStack(Items.COBBLESTONE, 7));
        sinFeedback("logistica_feedback.json");
        enviar(e, "{\"action\": \"store\", \"material\": \"minecraft:wheat,minecraft:carrot\"}");
        h.succeedWhen(() -> {
            Container c = (Container) h.getBlockEntity(cofre);
            h.assertTrue(cuantosC(c, Items.WHEAT) == 10 && cuantosC(c, Items.CARROT) == 5, "el cofre debe recibir los 10 de trigo y las 5 zanahorias (tiene " + cuantosC(c, Items.WHEAT) + " y " + cuantosC(c, Items.CARROT) + ")");
            h.assertTrue(cuantos(inventario(e), Items.WHEAT) == 0 && cuantos(inventario(e), Items.CARROT) == 0, "y Cobalt ya no debe llevarlos");
            h.assertTrue(cuantos(inventario(e), Items.BREAD) == 4 && cuantos(inventario(e), Items.IRON_PICKAXE) == 1 && cuantos(inventario(e), Items.COBBLESTONE) == 7, "lo que NO se pidió se lo queda (pan, pico, adoquín)");
            JsonObject fb = feedback(h, "logistica_feedback.json");
            h.assertTrue(fb.get("stored").getAsInt() == 15 && "success".equals(fb.get("status").getAsString()), "logistica_feedback.json debe decir 15 guardados: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 600, batch = "logistica_recoge_solo_lo_pedido")
    public static void recoge_solo_el_material_pedido_aunque_haya_varios(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        for (int i = 0; i < 3; i++) h.spawnItem(Items.ROTTEN_FLESH, 5.5F, Y, 5.5F);
        for (int i = 0; i < 2; i++) h.spawnItem(Items.DIAMOND, 6.5F, Y, 5.5F);
        sinFeedback("pickup_feedback.json");
        enviar(e, "{\"action\": \"pickup\", \"radius\": 12, \"material\": \"minecraft:rotten_flesh,minecraft:beef\"}");   // varios ids separados por coma
        h.succeedWhen(() -> {
            h.assertTrue(cuantos(inventario(e), Items.ROTTEN_FLESH) == 3, "debe recoger las 3 carnes podridas (tiene " + cuantos(inventario(e), Items.ROTTEN_FLESH) + ")");
            h.assertTrue(cuantos(inventario(e), Items.DIAMOND) == 0, "pero NO los diamantes, que no pidió");
            JsonObject fb = feedback(h, "pickup_feedback.json");
            h.assertTrue(fb.get("picked").getAsInt() == 3, "pickup_feedback.json debe decir 3 recogidos: " + fb);
        });
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1500, batch = "oficios_defensa_selectiva_ignora")
    public static void mientras_mina_ignora_a_un_hostil_lejano_que_no_lo_ataca(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        h.setBlock(new BlockPos(4, Y, 2), Blocks.IRON_ORE);
        h.setBlock(new BlockPos(5, Y, 2), Blocks.IRON_ORE);
        Husk husk = h.spawn(EntityType.HUSK, new BlockPos(8, Y, 8)); // a ~10 bloques y a la vista, pero sin atacarle
        husk.setNoAi(true);
        husk.setInvulnerable(true);
        enviar(e, "{\"action\": \"mine\", \"material\": \"minecraft:iron_ore\", \"amount\": 2}");
        h.onEachTick(() -> h.assertTrue(e.getTarget() != husk, "con una tarea en curso Cobalt NO debe salir a por un hostil que ni lo ataca"));
        h.succeedWhen(() -> h.assertTrue(cuantos(inventario(e), Items.RAW_IRON) >= 2, "y debe cumplir la misión de minar (tiene " + cuantos(inventario(e), Items.RAW_IRON) + ")"));
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 400, batch = "oficios_defensa_selectiva_se_defiende")
    public static void mientras_mina_si_un_hostil_ataca_al_dueno_lo_defiende(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.IRON_PICKAXE, 1));
        for (int x = 4; x <= 6; x++) for (int y = Y; y <= Y + 1; y++) h.setBlock(new BlockPos(x, y, 2), Blocks.IRON_ORE); // 6 menas: la tarea dura de sobra
        ServerPlayer p = dueno(h, e, 7.5, 7.5);
        Husk husk = h.spawn(EntityType.HUSK, new BlockPos(8, Y, 8));
        husk.setNoAi(true);
        husk.setInvulnerable(true);
        husk.setTarget(p);
        enviar(e, "{\"action\": \"mine\", \"material\": \"minecraft:iron_ore\", \"amount\": 6}");
        h.startSequence().thenIdle(60).thenExecute(() -> {
            try {
                h.assertTrue(((com.example.cobaltbot.entity.CobaltTareas) campo(e, "tareas")).ocupado(), "montaje: a los 3 s debe seguir con la tarea de minar");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
            h.assertTrue(e.getTarget() == husk, "un hostil que ataca al dueño sí es amenaza real aunque Cobalt esté minando (blanco: " + e.getTarget() + ")");
        }).thenExecute(p::discard).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 150, batch = "movimiento_nada_con_el_dueno")
    public static void si_el_dueno_nada_y_cobalt_vuela_por_encima_se_mete_al_agua_y_nada(GameTestHelper h) throws Exception {
        config("{}");
        for (int x = 5; x <= 8; x++) for (int z = 3; z <= 7; z++) for (int y = Y; y <= Y + 3; y++) {
            boolean borde = x == 5 || x == 8 || z == 3 || z == 7 || y == Y + 3;
            h.setBlock(new BlockPos(x, y, z), borde ? Blocks.BARRIER : Blocks.WATER);
        }
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y + 2, 4));
        ServerPlayer p = dueno(h, e, 6.5, 5.5);
        e.setModoVuelo(true);
        escribir("command.json", "[{\"action\": \"follow\", \"movement_mode\": \"fly\", \"bot_id\": \"" + NoxCuerpo.BOT_ID + "\"}]");
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.onEachTick(p::baseTick);
        h.succeedWhen(() -> {
            h.assertTrue(p.isInWater(), "montaje: el dueño debe estar en el agua");
            h.assertTrue(!e.isInWater(), "montaje: Cobalt debe estar fuera del estanque, fuera del agua");
            h.assertTrue(e.getNavigation() instanceof net.minecraft.world.entity.ai.navigation.WaterBoundPathNavigation, "el dueño nada: Cobalt debe pasar a modo nado en vez de flotar por encima");
            p.discard();
        });
    }

    @SuppressWarnings("unchecked")
    static boolean hayTicketDeCobalt(net.minecraft.server.level.ServerLevel nivel, int cx, int cz) throws Exception {
        Object gestor = net.minecraftforge.fml.util.ObfuscationReflectionHelper.getPrivateValue(net.minecraft.server.level.ServerChunkCache.class, nivel.getChunkSource(), "distanceManager");
        Object tickets = net.minecraftforge.fml.util.ObfuscationReflectionHelper.getPrivateValue(net.minecraft.server.level.DistanceManager.class, (net.minecraft.server.level.DistanceManager) gestor, "tickets");
        var conjunto = ((it.unimi.dsi.fastutil.longs.Long2ObjectMap<net.minecraft.util.SortedArraySet<net.minecraft.server.level.Ticket<?>>>) tickets).get(net.minecraft.world.level.ChunkPos.asLong(cx, cz));
        if (conjunto == null) return false;
        for (net.minecraft.server.level.Ticket<?> t : conjunto) if (t.getType() == com.example.cobaltbot.util.NoxChunkLoader.TICKET) return true;
        return false;
    }

    static int chunkX(GameTestHelper h, CobaltEntity e) {
        return e.blockPosition().getX() >> 4;
    }

    static int chunkZ(GameTestHelper h, CobaltEntity e) {
        return e.blockPosition().getZ() >> 4;
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 100, batch = "carga_anillo_3x3")
    public static void cobalt_mantiene_un_anillo_de_3x3_chunks_cargados(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        h.startSequence().thenIdle(25).thenExecute(() -> {
            try {
                int cx = chunkX(h, e), cz = chunkZ(h, e);
                for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++) h.assertTrue(hayTicketDeCobalt(h.getLevel(), cx + dx, cz + dz), "el anillo 3x3 debe estar cargado (" + dx + "," + dz + ")");
                h.assertTrue(!hayTicketDeCobalt(h.getLevel(), cx + 2, cz) && !hayTicketDeCobalt(h.getLevel(), cx, cz - 2), "y quieto no carga más allá (5x5 solo al trabajar lejos)");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "carga_trabajo_lejos")
    public static void mientras_trabaja_lejos_del_jugador_carga_un_anillo_de_5x5(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        inventario(e).addItem(new ItemStack(Items.FISHING_ROD, 1));
        estanque(h, 5, 4, false);
        sinFeedback("fish_feedback.json");
        enviar(e, "{\"action\": \"fish\", \"radius\": 12, \"amount\": 1}"); // una tarea que dura: espera el pique (sin dueño = lejos de él)
        h.startSequence().thenIdle(40).thenExecute(() -> {
            try {
                h.assertTrue(((com.example.cobaltbot.entity.CobaltTareas) campo(e, "tareas")).ocupado(), "montaje: debe seguir con la tarea");
                int cx = chunkX(h, e), cz = chunkZ(h, e);
                for (int dx = -2; dx <= 2; dx++) for (int dz = -2; dz <= 2; dz++) h.assertTrue(hayTicketDeCobalt(h.getLevel(), cx + dx, cz + dz), "haciendo una tarea lejos del jugador el anillo es de 5x5 (" + dx + "," + dz + ")");
                h.assertTrue(!hayTicketDeCobalt(h.getLevel(), cx + 3, cz), "pero no más");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "carga_por_delante")
    public static void yendo_a_un_destino_lejano_carga_chunks_por_delante(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        BlockPos destino = h.absolutePos(new BlockPos(1, Y, 1)).offset(200, 0, 0); // 200 bloques al este (12 chunks)
        escribir("command.json", "[{\"action\": \"go_to\", \"x\": " + destino.getX() + ", \"y\": " + destino.getY() + ", \"z\": " + destino.getZ() + ", \"movement_mode\": \"walk\", \"bot_id\": \"" + NoxCuerpo.BOT_ID + "\"}]");
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        int cx0 = chunkX(h, e), cz0 = chunkZ(h, e);
        h.startSequence().thenIdle(25).thenExecute(() -> {
            try {
                for (int k = 2; k <= 4; k++) h.assertTrue(hayTicketDeCobalt(h.getLevel(), cx0 + k, cz0), "yendo al este carga el chunk " + k + " por delante (anillo 1 + línea 3)");
                h.assertTrue(!hayTicketDeCobalt(h.getLevel(), cx0 + 6, cz0), "pero solo los 3 de delante");
                h.assertTrue(!hayTicketDeCobalt(h.getLevel(), cx0 - 2, cz0), "y nada por detrás");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "carga_por_delante_cerca")
    public static void con_un_destino_cercano_no_carga_por_delante_mas_alla_de_el(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        BlockPos destino = h.absolutePos(new BlockPos(1, Y, 1)).offset(40, 0, 0); // a 40 bloques (2 chunks y medio)
        escribir("command.json", "[{\"action\": \"go_to\", \"x\": " + destino.getX() + ", \"y\": " + destino.getY() + ", \"z\": " + destino.getZ() + ", \"movement_mode\": \"walk\", \"bot_id\": \"" + NoxCuerpo.BOT_ID + "\"}]");
        invocar(e, "leerComandosDePython", new Class<?>[] {});
        h.startSequence().thenIdle(25).thenExecute(() -> {
            try {
                int cx = chunkX(h, e), cz = chunkZ(h, e);
                h.assertTrue(hayTicketDeCobalt(h.getLevel(), cx + 1, cz), "montaje: el anillo está");
                h.assertTrue(!hayTicketDeCobalt(h.getLevel(), cx + 3, cz), "a 40 bloques del destino solo se adelanta lo que falta (1 chunk), no los 3 de siempre: no hay ticket 3 chunks por delante");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 200, batch = "carga_caduca")
    public static void si_nadie_los_renueva_los_tickets_caducan_solos(GameTestHelper h) throws Exception {
        net.minecraft.server.level.ServerLevel nivel = h.getLevel();
        int cx = 900, cz = 900; // lejos de todo
        com.example.cobaltbot.util.NoxChunkLoader.mantener(nivel, java.util.List.of(new int[] {cx, cz}, new int[] {cx + 1, cz}));
        h.assertTrue(hayTicketDeCobalt(nivel, cx, cz) && hayTicketDeCobalt(nivel, cx + 1, cz), "recién pedidos, los tickets existen");
        h.startSequence().thenIdle(20).thenExecute(() -> {
            try {
                h.assertTrue(hayTicketDeCobalt(nivel, cx, cz), "a los 20 ticks (un segundo) siguen (duran 40)");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenIdle(60).thenExecute(() -> {
            try {
                h.assertTrue(!hayTicketDeCobalt(nivel, cx, cz) && !hayTicketDeCobalt(nivel, cx + 1, cz), "sin renovarlos, a los 80 ticks ya no quedan (no se guarda nada en el mundo)");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 100, batch = "carga_se_suelta_al_irse")
    public static void al_desaparecer_cobalt_suelta_su_carga_al_instante(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        int cx = chunkX(h, e), cz = chunkZ(h, e);
        h.startSequence().thenIdle(25).thenExecute(() -> {
            try {
                h.assertTrue(hayTicketDeCobalt(h.getLevel(), cx, cz), "montaje: la carga existe mientras está");
                e.discard();
                h.assertTrue(!hayTicketDeCobalt(h.getLevel(), cx, cz) && !hayTicketDeCobalt(h.getLevel(), cx + 1, cz + 1), "al desaparecer se sueltan sin esperar a que caduquen");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 100, batch = "carga_apagada")
    public static void con_carga_chunks_apagada_no_carga_nada(GameTestHelper h) throws Exception {
        config("{\"carga_chunks\": false}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        h.startSequence().thenIdle(30).thenExecute(() -> {
            try {
                int cx = chunkX(h, e), cz = chunkZ(h, e);
                h.assertTrue(!hayTicketDeCobalt(h.getLevel(), cx, cz) && !hayTicketDeCobalt(h.getLevel(), cx + 1, cz), "con carga_chunks=false no crea ningún ticket");
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 500, batch = "movimiento_desvio_corto")
    public static void un_go_to_corto_mientras_te_sigue_no_le_hace_dejar_de_seguirte(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(1, Y, 1));
        ServerPlayer p = dueno(h, e, 7.5, 7.5);
        enviar(e, "{\"action\": \"follow\"}");
        h.startSequence().thenIdle(5).thenExecute(() -> {
            try {
                enviar(e, "{\"action\": \"go_to\", " + coord(h, 3, 3) + "}"); // un desvío corto, como esquivar un creeper
            } catch (Exception ex) {
                h.fail("excepción inesperada: " + ex);
            }
        }).thenIdle(3).thenExecute(() -> h.assertTrue(!flag(e, "isFollowingOwner"), "mientras hace el desvío no debe seguirte"))
                .thenWaitUntil(() -> h.assertTrue(flag(e, "isFollowingOwner"), "al terminar el desvío corto debe volver a seguirte")).thenExecute(p::discard).thenSucceed();
    }

    @GameTest(template = PLANTILLA, timeoutTicks = 1500, batch = "soak")
    public static void aguanta_una_oleada_de_1000_ticks_sin_fallar(GameTestHelper h) throws Exception {
        config("{}");
        CobaltEntity e = crearLimpio(h, new BlockPos(4, Y, 4));
        ServerPlayer p = dueno(h, e, 5.5, 4.5);
        inventario(e).addItem(new ItemStack(Items.BREAD, 16));
        for (int i = 0; i < 3; i++) h.spawn(EntityType.HUSK, new BlockPos(1 + i * 3, Y, 8));
        enviar(e, "{\"action\": \"follow\"}");
        h.startSequence().thenIdle(1000).thenExecute(() -> {
            h.assertTrue(e.isAlive() || e.isDeadOrDying(), "el servidor sigue en pie tras 1000 ticks de combate");
            p.discard();
        }).thenSucceed();
    }
}
