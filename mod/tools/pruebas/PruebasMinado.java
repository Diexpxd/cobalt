import com.example.cobaltbot.util.NoxMinado;
import com.google.gson.JsonParser;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.function.Function;
import java.util.function.Predicate;

/** Pruebas del Bloque E (reglas de seguridad de minería y limpieza): sin abrir Minecraft. */
public class PruebasMinado {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static BlockGetter mundo(Function<BlockPos, BlockState> f) {
        return new BlockGetter() {
            public BlockEntity getBlockEntity(BlockPos p) { return null; }
            public BlockState getBlockState(BlockPos p) { return f.apply(p); }
            public FluidState getFluidState(BlockPos p) { return f.apply(p).getFluidState(); }
            public int getHeight() { return 384; }
            public int getMinBuildHeight() { return -64; }
        };
    }

    static BlockState s(Block b) { return b.defaultBlockState(); }

    static boolean adyacente(BlockPos a, BlockPos b) {
        return Math.abs(a.getX() - b.getX()) + Math.abs(a.getY() - b.getY()) + Math.abs(a.getZ() - b.getZ()) == 1;
    }

    static int oraculo(BlockGetter w, BlockPos ini, Predicate<BlockState> objetivo, int radio, int cota) {
        List<BlockPos> ores = new java.util.ArrayList<>();
        for (int dx = -radio; dx <= radio; dx++)
            for (int dy = -radio; dy <= radio; dy++)
                for (int dz = -radio; dz <= radio; dz++) {
                    BlockPos v = ini.offset(dx, dy, dz);
                    if (objetivo.test(w.getBlockState(v)) && NoxMinado.excavableSeguro(w, v, null, 0)) ores.add(v);
                }
        int[] mejor = {cota};
        Set<BlockPos> visitados = new HashSet<>();
        visitados.add(ini);
        dfs(w, ini, ini, radio, ores, visitados, new HashSet<>(), mejor);
        return mejor[0];
    }

    static void dfs(BlockGetter w, BlockPos ini, BlockPos nodo, int radio, List<BlockPos> ores, Set<BlockPos> visitados, Set<BlockPos> picadas, int[] mejor) {
        for (BlockPos ore : ores) {
            boolean toca = ore.equals(nodo) || ore.equals(nodo.above()) || adyacente(ore, nodo) || adyacente(ore, nodo.above());
            if (toca) mejor[0] = Math.min(mejor[0], picadas.size() + (picadas.contains(ore) ? 0 : 1));
        }
        for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
            BlockPos b = nodo.relative(d);
            if (visitados.contains(b) || Math.abs(b.getX() - ini.getX()) > radio || Math.abs(b.getY() - ini.getY()) > radio || Math.abs(b.getZ() - ini.getZ()) > radio) continue;
            List<BlockPos> nuevas = new java.util.ArrayList<>();
            boolean ok = true;
            for (BlockPos c : new BlockPos[]{b, b.above()}) {
                if (c.equals(ini) || c.equals(ini.above()) || w.getBlockState(c).isAir()) continue; // el hitbox de partida y el aire son gratis
                if (!NoxMinado.excavableSeguro(w, c, null, 0)) { ok = false; break; }
                if (!picadas.contains(c)) nuevas.add(c);
            }
            if (!ok || picadas.size() + nuevas.size() >= mejor[0]) continue; // poda: ya no puede mejorar
            picadas.addAll(nuevas);
            visitados.add(b);
            dfs(w, ini, b, radio, ores, visitados, picadas, mejor);
            visitados.remove(b);
            picadas.removeAll(nuevas);
        }
    }

    public static void main(String[] a) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        for (Block b : new Block[]{Blocks.AIR, Blocks.STONE, Blocks.WATER, Blocks.LAVA, Blocks.IRON_ORE, Blocks.DEEPSLATE_IRON_ORE,
                Blocks.COAL_ORE, Blocks.OAK_LOG, Blocks.DIRT, Blocks.GRASS_BLOCK, Blocks.BEDROCK, Blocks.CHEST, Blocks.TALL_GRASS,
                Blocks.OAK_LEAVES, Blocks.SNOW, Blocks.WHEAT, Blocks.OAK_PLANKS, Blocks.COBBLESTONE}) {
            b.getStateDefinition().getPossibleStates().forEach(BlockBehaviour.BlockStateBase::initCache);
        }

        check("iron_ore  <- iron_ore", NoxMinado.esObjetivo(s(Blocks.IRON_ORE), "iron_ore"));
        check("iron_ore  <- deepslate_iron_ore", NoxMinado.esObjetivo(s(Blocks.DEEPSLATE_IRON_ORE), "iron_ore"));
        check("iron_ore  NO coincide con coal_ore", !NoxMinado.esObjetivo(s(Blocks.COAL_ORE), "iron_ore"));
        check("iron_ore  NO coincide con iron_block ni raw_iron_block", !NoxMinado.esObjetivo(s(Blocks.IRON_BLOCK), "iron_ore") && !NoxMinado.esObjetivo(s(Blocks.RAW_IRON_BLOCK), "iron_ore"));
        check("'IRON_ORE' en mayúsculas también", NoxMinado.esObjetivo(s(Blocks.IRON_ORE), "  IRON_ORE "));
        check("log <- oak_log y stripped_oak_log", NoxMinado.esObjetivo(s(Blocks.OAK_LOG), "log") && NoxMinado.esObjetivo(s(Blocks.STRIPPED_OAK_LOG), "log"));
        check("'troncos' (español) también", NoxMinado.esObjetivo(s(Blocks.OAK_LOG), "troncos"));
        check("log NO coincide con oak_planks", !NoxMinado.esObjetivo(s(Blocks.OAK_PLANKS), "log"));
        check("stone <- stone, pero NO cobblestone ni stone_bricks",
                NoxMinado.esObjetivo(s(Blocks.STONE), "stone") && !NoxMinado.esObjetivo(s(Blocks.COBBLESTONE), "stone") && !NoxMinado.esObjetivo(s(Blocks.STONE_BRICKS), "stone"));
        check("dirt <- dirt y coarse_dirt", NoxMinado.esObjetivo(s(Blocks.DIRT), "dirt") && NoxMinado.esObjetivo(s(Blocks.COARSE_DIRT), "dirt"));
        check("'cualquiera' = cualquier mena (iron, diamond, ancient_debris)",
                NoxMinado.esObjetivo(s(Blocks.IRON_ORE), "cualquiera") && NoxMinado.esObjetivo(s(Blocks.DIAMOND_ORE), "cualquiera") && NoxMinado.esObjetivo(s(Blocks.ANCIENT_DEBRIS), "cualquiera"));
        check("'cualquiera' NO es piedra ni madera", !NoxMinado.esObjetivo(s(Blocks.STONE), "cualquiera") && !NoxMinado.esObjetivo(s(Blocks.OAK_LOG), "cualquiera"));
        check("material null se trata como 'cualquiera'", NoxMinado.esObjetivo(s(Blocks.COAL_ORE), null) && !NoxMinado.esObjetivo(s(Blocks.STONE), null));
        check("id completo exacto: minecraft:iron_ore <- iron_ore pero NO deepslate", NoxMinado.esObjetivo(s(Blocks.IRON_ORE), "minecraft:iron_ore") && !NoxMinado.esObjetivo(s(Blocks.DEEPSLATE_IRON_ORE), "minecraft:iron_ore"));

        check("ítem iron_ore <- 'iron_ore' y deepslate_iron_ore", NoxMinado.itemCoincide(new ItemStack(Items.IRON_ORE), "iron_ore") && NoxMinado.itemCoincide(new ItemStack(Items.DEEPSLATE_IRON_ORE), "iron_ore"));
        check("ítem raw_iron NO es 'iron_ore'", !NoxMinado.itemCoincide(new ItemStack(Items.RAW_IRON), "iron_ore"));
        check("ítem log <- oak_log; stick no", NoxMinado.itemCoincide(new ItemStack(Items.OAK_LOG), "log") && !NoxMinado.itemCoincide(new ItemStack(Items.STICK), "log"));
        check("ítem: pila vacía y 'cualquiera' nunca coinciden", !NoxMinado.itemCoincide(ItemStack.EMPTY, "iron_ore") && !NoxMinado.itemCoincide(new ItemStack(Items.IRON_ORE), "cualquiera"));
        check("ítem: un pico de hierro NO es 'iron_ore' (el bug de contains en fundir)", !NoxMinado.itemCoincide(new ItemStack(Items.IRON_PICKAXE), "iron_ore") && !NoxMinado.itemCoincide(new ItemStack(Items.IRON_PICKAXE), "iron"));

        check("etiqueta: '#forge:ores/iron', 'forge:ores/iron' y 'c:ores/iron' se reconocen y devuelven la misma etiqueta",
                NoxMinado.etiquetaDe("#forge:ores/iron") != null && "forge:ores/iron".equals(String.valueOf(NoxMinado.etiquetaDe("#forge:ores/iron")))
                        && "forge:ores/iron".equals(String.valueOf(NoxMinado.etiquetaDe("forge:ores/iron"))) && "c:ores/iron".equals(String.valueOf(NoxMinado.etiquetaDe("  C:Ores/Iron "))));
        check("etiqueta: un id normal, un nombre suelto y null NO son etiquetas",
                NoxMinado.etiquetaDe("minecraft:iron_ore") == null && NoxMinado.etiquetaDe("iron_ore") == null && NoxMinado.etiquetaDe("cualquiera") == null && NoxMinado.etiquetaDe(null) == null && NoxMinado.etiquetaDe("") == null);
        check("etiqueta: '#minecraft:logs' también (cualquier espacio de nombres con #)", "minecraft:logs".equals(String.valueOf(NoxMinado.etiquetaDe("#minecraft:logs"))));
        check("etiqueta: sin el registro de etiquetas cargado (pruebas) no coincide con nada y no lanza excepción",
                !NoxMinado.esObjetivo(s(Blocks.IRON_ORE), "#forge:ores/iron") && !NoxMinado.itemCoincide(new ItemStack(Items.IRON_ORE), "forge:ores/iron") && !NoxMinado.itemCoincide(ItemStack.EMPTY, "#forge:ores"));
        check("etiqueta: los ids y materiales de siempre siguen funcionando igual", NoxMinado.esObjetivo(s(Blocks.IRON_ORE), "iron_ore") && !NoxMinado.esObjetivo(s(Blocks.COAL_ORE), "iron_ore"));

        check("piedra es minable", NoxMinado.esMinable(s(Blocks.STONE)));
        check("aire, agua y lava NO", !NoxMinado.esMinable(s(Blocks.AIR)) && !NoxMinado.esMinable(s(Blocks.WATER)) && !NoxMinado.esMinable(s(Blocks.LAVA)));
        check("bedrock (irrompible) NO", !NoxMinado.esMinable(s(Blocks.BEDROCK)));
        check("cofre, horno y spawner (con inventario/datos) NO",
                !NoxMinado.esMinable(s(Blocks.CHEST)) && !NoxMinado.esMinable(s(Blocks.FURNACE)) && !NoxMinado.esMinable(s(Blocks.SPAWNER)));

        check("limpiable: tierra, hierba, arena, grava, piedra, hojas",
                NoxMinado.esLimpiable(s(Blocks.DIRT)) && NoxMinado.esLimpiable(s(Blocks.GRASS_BLOCK)) && NoxMinado.esLimpiable(s(Blocks.SAND))
                        && NoxMinado.esLimpiable(s(Blocks.GRAVEL)) && NoxMinado.esLimpiable(s(Blocks.STONE)) && NoxMinado.esLimpiable(s(Blocks.OAK_LEAVES)));
        check("limpiable: plantas (hierba alta, flores, nieve)", NoxMinado.esLimpiable(s(Blocks.TALL_GRASS)) && NoxMinado.esLimpiable(s(Blocks.DANDELION)) && NoxMinado.esLimpiable(s(Blocks.SNOW)));
        check("NO limpiable: tablones, cobblestone y bloques de diamante (los construye el jugador)",
                !NoxMinado.esLimpiable(s(Blocks.OAK_PLANKS)) && !NoxMinado.esLimpiable(s(Blocks.COBBLESTONE)) && !NoxMinado.esLimpiable(s(Blocks.DIAMOND_BLOCK)));
        check("NO limpiable: cofres, troncos, menas, cultivos, agua y aire",
                !NoxMinado.esLimpiable(s(Blocks.CHEST)) && !NoxMinado.esLimpiable(s(Blocks.OAK_LOG)) && !NoxMinado.esLimpiable(s(Blocks.IRON_ORE))
                        && !NoxMinado.esLimpiable(s(Blocks.WHEAT)) && !NoxMinado.esLimpiable(s(Blocks.WATER)) && !NoxMinado.esLimpiable(s(Blocks.AIR)));

        check("ticksParaRomper piedra (1.5) a mano = 45", NoxMinado.ticksParaRomper(1.5F, 1.0F) == 45);
        check("ticksParaRomper piedra con pico de hierro (velocidad 6) = 8", NoxMinado.ticksParaRomper(1.5F, 6.0F) == 8);
        check("mínimo 4 ticks (dureza 0)", NoxMinado.ticksParaRomper(0.0F, 1.0F) == 4);
        check("máximo 200 ticks (dureza enorme)", NoxMinado.ticksParaRomper(500.0F, 1.0F) == 200);
        check("velocidad < 1 se trata como 1 (sin división rara)", NoxMinado.ticksParaRomper(1.5F, 0.0F) == 45);
        check("dureza negativa no da tiempos negativos", NoxMinado.ticksParaRomper(-1.0F, 1.0F) == 4);

        BlockPos base = new BlockPos(0, 64, 0);
        check("protegido: a 10 bloques de la base", NoxMinado.protegido(new BlockPos(10, 64, 0), base, 24));
        check("protegido: justo en el borde (24)", NoxMinado.protegido(new BlockPos(24, 64, 0), base, 24));
        check("NO protegido: a 30 bloques", !NoxMinado.protegido(new BlockPos(30, 64, 0), base, 24));
        check("sin base definida nada está protegido", !NoxMinado.protegido(new BlockPos(1, 64, 0), null, 24));
        check("coordenadas de base: floor de decimales y negativos",
                NoxMinado.coordenadasDe(JsonParser.parseString("{\"x\": 1.7, \"y\": 64, \"z\": -2.2}")).equals(new BlockPos(1, 64, -3)));
        check("coordenadas incompletas o no-objeto -> null",
                NoxMinado.coordenadasDe(JsonParser.parseString("{\"x\": 1}")) == null && NoxMinado.coordenadasDe(JsonParser.parseString("\"hola\"")) == null && NoxMinado.coordenadasDe(null) == null);

        BlockPos menaA = new BlockPos(3, 61, 0), menaD = new BlockPos(-4, 61, 0), menaB = new BlockPos(0, 55, 0);
        BlockPos menaC = new BlockPos(6, 61, 0), carbon = new BlockPos(1, 61, 1), lejana = new BlockPos(9, 61, 9);
        BlockGetter mina = mundo(p -> {
            if (p.equals(menaA) || p.equals(menaD) || p.equals(menaB) || p.equals(lejana)) return s(Blocks.IRON_ORE);
            if (p.equals(menaC)) return s(Blocks.DEEPSLATE_IRON_ORE);
            if (p.equals(carbon)) return s(Blocks.COAL_ORE);
            if (p.equals(new BlockPos(6, 62, 0))) return s(Blocks.WATER); // agua pegada a la mena C
            return p.getY() <= 60 || p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR);
        });
        // (menaB queda enterrada bajo el suelo de piedra: y=55)
        BlockPos centro = new BlockPos(0, 62, 0);
        List<BlockPos> r = NoxMinado.buscarBloques(mina, centro, 10, st -> NoxMinado.esObjetivo(st, "iron_ore"), null, 0, 32, null);
        check("encuentra las 2 menas de hierro EXPUESTAS y ordenadas por cercanía (A antes que D)", r.size() == 2 && r.get(0).equals(menaA) && r.get(1).equals(menaD));
        check("NO devuelve la mena enterrada (sin cara al aire)", !r.contains(menaB));
        check("NO devuelve la mena junto al agua (soltaría agua)", !r.contains(menaC));
        check("NO devuelve la que está fuera del radio", !r.contains(lejana));

        r = NoxMinado.buscarBloques(mina, centro, 10, st -> NoxMinado.esObjetivo(st, "iron_ore"), menaD, 2, 32, null);
        check("con la base sobre la mena D (radio 2): D queda protegida y solo sale A", r.size() == 1 && r.get(0).equals(menaA));
        r = NoxMinado.buscarBloques(mina, centro, 10, st -> NoxMinado.esObjetivo(st, "iron_ore"), null, 0, 32, menaA::equals);
        check("un bloque 'excluido' (descartado por inaccesible) no vuelve a salir", r.size() == 1 && r.get(0).equals(menaD));
        r = NoxMinado.buscarBloques(mina, centro, 10, st -> NoxMinado.esObjetivo(st, "iron_ore"), null, 0, 1, null);
        check("el límite 'max' se respeta", r.size() == 1 && r.get(0).equals(menaA));
        r = NoxMinado.buscarBloques(mina, centro, 10, st -> NoxMinado.esObjetivo(st, "cualquiera"), null, 0, 32, null);
        check("'cualquiera' incluye el carbón y ordena por cercanía (el carbón es el más cercano)", r.size() == 3 && r.get(0).equals(carbon));

        BlockPos acceso = NoxMinado.accesoAire(mina, menaA, 3.5, 70, 0.5);
        check("accesoAire: un hueco de aire pegado a la mena (el de arriba, el más cercano a quien viene de arriba)", acceso != null && acceso.equals(new BlockPos(3, 62, 0)));
        check("accesoAire de una mena enterrada -> null (no hay por dónde llegar sin picar roca)", NoxMinado.accesoAire(mina, menaB, 0, 70, 0) == null);

        check("terreno excavable: piedra, tierra, deepslate, netherrack y menas SÍ", NoxMinado.esTerrenoExcavable(s(Blocks.STONE)) && NoxMinado.esTerrenoExcavable(s(Blocks.DIRT))
                && NoxMinado.esTerrenoExcavable(s(Blocks.DEEPSLATE)) && NoxMinado.esTerrenoExcavable(s(Blocks.NETHERRACK))
                && NoxMinado.esTerrenoExcavable(s(Blocks.IRON_ORE)) && NoxMinado.esTerrenoExcavable(s(Blocks.DEEPSLATE_DIAMOND_ORE)) && NoxMinado.esTerrenoExcavable(s(Blocks.ANCIENT_DEBRIS)));
        check("terreno excavable: tablones, cobblestone, ladrillos, cristal, obsidiana, arena y grava NO (construcciones del jugador / caen)",
                !NoxMinado.esTerrenoExcavable(s(Blocks.OAK_PLANKS)) && !NoxMinado.esTerrenoExcavable(s(Blocks.COBBLESTONE)) && !NoxMinado.esTerrenoExcavable(s(Blocks.STONE_BRICKS))
                        && !NoxMinado.esTerrenoExcavable(s(Blocks.GLASS)) && !NoxMinado.esTerrenoExcavable(s(Blocks.OBSIDIAN))
                        && !NoxMinado.esTerrenoExcavable(s(Blocks.SAND)) && !NoxMinado.esTerrenoExcavable(s(Blocks.GRAVEL)));

        BlockPos vetaProfunda = new BlockPos(4, 56, 0);
        BlockPos inicioT = new BlockPos(0, 61, 0);
        Predicate<BlockState> hierro = st -> NoxMinado.esObjetivo(st, "iron_ore");
        BlockGetter roca = mundo(p -> p.equals(vetaProfunda) ? s(Blocks.IRON_ORE) : (p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR)));
        List<BlockPos> plan = NoxMinado.planificarTunel(roca, inicioT, hierro, null, 0, 12, 24, null);
        check("túnel: encuentra un plan hasta la veta enterrada y la veta va la ÚLTIMA", !plan.isEmpty() && plan.get(plan.size() - 1).equals(vetaProfunda));
        check("túnel: respeta el tope de bloques a picar", plan.size() <= 24);
        check("túnel: empieza picando en la superficie (y=60) y solo pica roca real (nada de aire)",
                !plan.isEmpty() && plan.get(0).getY() == 60 && plan.stream().noneMatch(p -> roca.getBlockState(p).isAir()));
        Set<BlockPos> abierto = new HashSet<>();
        boolean conectado = true;
        for (BlockPos p : plan) { // cada bloque debe tocar aire o algo ya picado: el túnel es continuo
            boolean toca = false;
            for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
                BlockPos v = p.relative(d);
                if (roca.getBlockState(v).isAir() || abierto.contains(v)) toca = true;
            }
            conectado &= toca;
            abierto.add(p);
        }
        check("túnel: es CONTINUO (cada bloque toca aire o algo ya picado)", conectado);
        check("túnel: veta ya a la vista (pegada al aire) -> el plan es solo esa veta",
                NoxMinado.planificarTunel(roca, new BlockPos(4, 57, 0), hierro, null, 0, 12, 24, null).equals(List.of(vetaProfunda)));

        BlockPos agua = new BlockPos(4, 58, 0);
        BlockGetter rocaConAgua = mundo(p -> p.equals(vetaProfunda) ? s(Blocks.IRON_ORE) : p.equals(agua) ? s(Blocks.WATER) : (p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR)));
        List<BlockPos> rodeo = NoxMinado.planificarTunel(rocaConAgua, inicioT, hierro, null, 0, 12, 24, null);
        boolean sinAguaCerca = true;
        for (BlockPos p : rodeo) {
            for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
                sinAguaCerca &= rocaConAgua.getBlockState(p.relative(d)).getFluidState().isEmpty();
            }
        }
        check("túnel con una bolsa de agua en medio: RODEA el agua (ningún bloque picado toca el agua) y llega a la veta",
                !rodeo.isEmpty() && rodeo.get(rodeo.size() - 1).equals(vetaProfunda) && sinAguaCerca);

        BlockGetter vetaJuntoAgua = mundo(p -> p.equals(vetaProfunda) ? s(Blocks.IRON_ORE) : p.equals(new BlockPos(4, 55, 0)) ? s(Blocks.WATER) : (p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR)));
        check("túnel: una veta pegada al agua NO se toca (soltaría agua)", NoxMinado.planificarTunel(vetaJuntoAgua, inicioT, hierro, null, 0, 12, 24, null).isEmpty());
        BlockGetter vetaJuntoLava = mundo(p -> p.equals(vetaProfunda) ? s(Blocks.IRON_ORE) : p.equals(new BlockPos(5, 56, 0)) ? s(Blocks.LAVA) : (p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR)));
        check("túnel: una veta pegada a la lava NO se toca", NoxMinado.planificarTunel(vetaJuntoLava, inicioT, hierro, null, 0, 12, 24, null).isEmpty());

        BlockGetter mundoVetaLejana = mundo(p -> p.equals(new BlockPos(0, 40, 0)) ? s(Blocks.IRON_ORE) : (p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR)));
        check("túnel: una veta fuera del radio de búsqueda (12) se ignora", NoxMinado.planificarTunel(mundoVetaLejana, inicioT, hierro, null, 0, 12, 24, null).isEmpty());
        check("túnel: si picar costaría más del tope, no se planifica (tope 3)", NoxMinado.planificarTunel(roca, inicioT, hierro, null, 0, 12, 3, null).isEmpty());
        check("túnel: la zona de la base está protegida (base sobre la veta, radio 3)", NoxMinado.planificarTunel(roca, inicioT, hierro, vetaProfunda, 3, 12, 24, null).isEmpty());
        check("túnel: una veta 'excluida' (ya descartada) no se vuelve a intentar", NoxMinado.planificarTunel(roca, inicioT, hierro, null, 0, 12, 24, vetaProfunda::equals).isEmpty());

        BlockGetter casa = mundo(p -> {
            if (p.equals(vetaProfunda)) return s(Blocks.IRON_ORE);
            if (Math.abs(p.getX() - 4) <= 1 && Math.abs(p.getY() - 56) <= 1 && Math.abs(p.getZ()) <= 1) return s(Blocks.OAK_PLANKS);
            return p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR);
        });
        check("túnel: una veta tras una pared de tablones (construcción del jugador) NO se alcanza", NoxMinado.planificarTunel(casa, inicioT, hierro, null, 0, 12, 24, null).isEmpty());

        BlockGetter conGrava = mundo(p -> p.equals(new BlockPos(2, 59, 0)) ? s(Blocks.STONE) : p.equals(new BlockPos(2, 60, 0)) ? s(Blocks.GRAVEL) : s(Blocks.AIR));
        check("excavableSeguro: piedra con GRAVA justo encima NO (se desplomaría sobre el túnel)", !NoxMinado.excavableSeguro(conGrava, new BlockPos(2, 59, 0), null, 0));
        check("excavableSeguro: piedra normal SÍ; la zona de la base NO",
                NoxMinado.excavableSeguro(roca, new BlockPos(1, 58, 0), null, 0) && !NoxMinado.excavableSeguro(roca, new BlockPos(1, 58, 0), new BlockPos(1, 58, 0), 5));

        BlockPos iniE = new BlockPos(0, 50, 0);
        Function<Function<BlockPos, BlockState>, BlockGetter> rocaE = extra -> mundo(p -> {
            BlockState e = extra.apply(p);
            if (e != null) return e;
            if (p.equals(iniE) || p.equals(iniE.above())) return s(Blocks.AIR); // el bolsillo de aire donde está Cobalt
            return s(Blocks.STONE);
        });
        Predicate<BlockState> hierroE = st -> NoxMinado.esObjetivo(st, "iron_ore");

        BlockPos venaAbajo = new BlockPos(0, 44, 0);
        BlockGetter pozo = rocaE.apply(p -> p.equals(venaAbajo) ? s(Blocks.IRON_ORE) : null);
        NoxMinado.PlanTunel bajada = NoxMinado.planificarTunelConCoste(pozo, iniE, hierroE, null, 0, 8, 32, null);
        check("coste exacto de un pozo de 5 bloques + veta debajo = 6 (la fórmula anterior contaba 10): 5 pasos de 1 celda nueva + la veta",
                bajada.costeProyectado() == 6 && bajada.celdas().size() == 6 && bajada.celdas().get(5).equals(venaAbajo));
        BlockPos venaCerca = new BlockPos(0, 47, 0);
        BlockGetter pozoCorto = rocaE.apply(p -> p.equals(venaCerca) ? s(Blocks.IRON_ORE) : null);
        NoxMinado.PlanTunel bajadaCorta = NoxMinado.planificarTunelConCoste(pozoCorto, iniE, hierroE, null, 0, 8, 32, null);
        check("coste exacto con la veta a 3 debajo = 3 (2 celdas + la veta): la veta no se cuenta dos veces aunque caiga en el hitbox del último paso",
                bajadaCorta.costeProyectado() == 3 && bajadaCorta.celdas().size() == 3);
        BlockGetter horizontal = rocaE.apply(p -> p.equals(new BlockPos(5, 50, 0)) ? s(Blocks.IRON_ORE) : null);
        NoxMinado.PlanTunel lado = NoxMinado.planificarTunelConCoste(horizontal, iniE, hierroE, null, 0, 8, 32, null);
        check("coste exacto en horizontal = 9 (4 pasos x 2 celdas + la veta; ahí no hay celdas compartidas)", lado.costeProyectado() == 9 && lado.celdas().size() == 9);
        check("el tope cuenta la veta: veta a 6 bloques de pozo -> con tope 6 SÍ, con tope 5 NO",
                !NoxMinado.planificarTunel(pozo, iniE, hierroE, null, 0, 8, 6, null).isEmpty() && NoxMinado.planificarTunel(pozo, iniE, hierroE, null, 0, 8, 5, null).isEmpty());

        java.util.Random azar = new java.util.Random(20260919L);
        int radioE = 3, maxE = 9, conPlan = 0, sinPlan = 0, malos = 0;
        String primerMalo = "";
        for (int w = 0; w < 120; w++) {
            int maxW = (w % 4 == 0) ? 4 : maxE;        // 1 de cada 4 mundos con un tope tan bajo que muchas vetas quedan fuera
            boolean sellado = (w % 8 == 0);            // 1 de cada 8: Cobalt encerrado entre tablones (no hay salida segura)
            java.util.Map<BlockPos, BlockState> cel = new java.util.HashMap<>();
            for (int dx = -radioE - 1; dx <= radioE + 1; dx++)
                for (int dy = -radioE - 1; dy <= radioE + 2; dy++)
                    for (int dz = -radioE - 1; dz <= radioE + 1; dz++) {
                        double sorteo = azar.nextDouble();
                        Block b = sorteo < 0.72 ? Blocks.STONE : sorteo < 0.82 ? Blocks.AIR : sorteo < 0.86 ? Blocks.WATER : sorteo < 0.89 ? Blocks.OAK_PLANKS
                                : sorteo < 0.92 ? Blocks.GRAVEL : sorteo < 0.95 ? Blocks.DIRT : Blocks.IRON_ORE;
                        cel.put(iniE.offset(dx, dy, dz), s(b));
                    }
            for (int k = 0; k < 2; k++) cel.put(iniE.offset(azar.nextInt(5) - 2, azar.nextInt(5) - 2, azar.nextInt(5) - 2), s(Blocks.IRON_ORE));
            cel.put(iniE, s(Blocks.AIR));
            cel.put(iniE.above(), s(Blocks.AIR));
            if (sellado) {
                for (BlockPos hueco : new BlockPos[]{iniE, iniE.above()})
                    for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
                        BlockPos v = hueco.relative(d);
                        if (!v.equals(iniE) && !v.equals(iniE.above())) cel.put(v, s(Blocks.OAK_PLANKS));
                    }
            }
            BlockGetter mundoAzar = mundo(p -> cel.getOrDefault(p, s(Blocks.STONE)));
            NoxMinado.PlanTunel pl = NoxMinado.planificarTunelConCoste(mundoAzar, iniE, hierroE, null, 0, radioE, maxW, null);
            boolean bien;
            if (pl.celdas().isEmpty()) {
                sinPlan++;
                bien = oraculo(mundoAzar, iniE, hierroE, radioE, maxW + 1) == maxW + 1; // ningún camino cuesta <= tope
            } else {
                conPlan++;
                Set<BlockPos> distintas = new HashSet<>(pl.celdas());
                boolean todasReales = pl.celdas().stream().noneMatch(p -> mundoAzar.getBlockState(p).isAir())
                        && pl.celdas().stream().allMatch(p -> NoxMinado.excavableSeguro(mundoAzar, p, null, 0));
                bien = pl.costeProyectado() == pl.celdas().size() && distintas.size() == pl.celdas().size() && todasReales
                        && pl.costeProyectado() <= maxW
                        && hierroE.test(mundoAzar.getBlockState(pl.celdas().get(pl.celdas().size() - 1)))
                        && oraculo(mundoAzar, iniE, hierroE, radioE, pl.costeProyectado()) == pl.costeProyectado(); // nadie lo mejora
            }
            if (!bien) { malos++; if (primerMalo.isEmpty()) primerMalo = "mundo " + w + " coste=" + pl.costeProyectado() + " celdas=" + pl.celdas().size(); }
        }
        check("fuerza bruta: 120 mundos aleatorios -> coste proyectado == bloques reales a picar Y es el mínimo exacto (fallos: " + malos + " " + primerMalo + ")", malos == 0);
        check("fuerza bruta: la muestra es significativa (planes con solución: " + conPlan + ", sin solución: " + sinPlan + ")", conPlan >= 30 && sinPlan >= 15);

        check("esMena: hierro, diamante, cualquiera y *_ore SÍ", NoxMinado.esMena("iron_ore") && NoxMinado.esMena("diamond") && NoxMinado.esMena("cualquiera")
                && NoxMinado.esMena("deepslate_redstone_ore") && NoxMinado.esMena("ancient_debris") && NoxMinado.esMena("coal"));
        check("esMena: piedra, tierra, troncos, tablones y bloques de hierro NO (se ven en superficie)", !NoxMinado.esMena("stone") && !NoxMinado.esMena("dirt")
                && !NoxMinado.esMena("log") && !NoxMinado.esMena("oak_planks") && !NoxMinado.esMena("iron_block"));
        check("alturaIdeal: diamante/redstone -58, oro -16, lapis 0, hierro 16, carbón 45, cobre 48, desconocido 0, Nether 15",
                NoxMinado.alturaIdeal("diamond_ore", false) == -58 && NoxMinado.alturaIdeal("redstone", false) == -58 && NoxMinado.alturaIdeal("gold_ore", false) == -16
                        && NoxMinado.alturaIdeal("lapis", false) == 0 && NoxMinado.alturaIdeal("iron_ore", false) == 16 && NoxMinado.alturaIdeal("coal_ore", false) == 45
                        && NoxMinado.alturaIdeal("copper_ore", false) == 48 && NoxMinado.alturaIdeal("cualquiera", false) == 0 && NoxMinado.alturaIdeal("ancient_debris", true) == 15);
        check("ripio: cobblestone, deepslate cobbled, tierra y granito SÍ; hierro en bruto, diamante y carbón NO",
                NoxMinado.esBasura(new ItemStack(Items.COBBLESTONE)) && NoxMinado.esBasura(new ItemStack(Items.COBBLED_DEEPSLATE)) && NoxMinado.esBasura(new ItemStack(Items.DIRT))
                        && NoxMinado.esBasura(new ItemStack(Items.GRANITE)) && !NoxMinado.esBasura(new ItemStack(Items.RAW_IRON)) && !NoxMinado.esBasura(new ItemStack(Items.DIAMOND))
                        && !NoxMinado.esBasura(new ItemStack(Items.COAL)) && !NoxMinado.esBasura(ItemStack.EMPTY));
        check("debeConservar: ripio solo hasta 64; lo valioso y lo pedido siempre",
                NoxMinado.debeConservar(new ItemStack(Items.COBBLESTONE), 10, false) && !NoxMinado.debeConservar(new ItemStack(Items.COBBLESTONE), 64, false)
                        && NoxMinado.debeConservar(new ItemStack(Items.COBBLESTONE), 500, true) && NoxMinado.debeConservar(new ItemStack(Items.DIAMOND), 999, false)
                        && NoxMinado.debeConservar(new ItemStack(Items.RAW_IRON), 999, false));

        net.minecraft.core.Direction este = net.minecraft.core.Direction.EAST;
        BlockPos frenteH = new BlockPos(0, 50, 0);
        Function<Function<BlockPos, BlockState>, BlockGetter> conRoca = extra -> mundo(p -> {
            BlockState e = extra.apply(p);
            if (e != null) return e;
            if (p.equals(frenteH) || p.equals(frenteH.above())) return s(Blocks.AIR); // el bolsillo de aire donde está Cobalt
            return p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR);
        });
        java.util.function.BiFunction<BlockGetter, List<BlockPos>, Boolean> continuo = (w, celdas) -> {
            Set<BlockPos> picado = new HashSet<>();
            boolean ok = true;
            for (BlockPos p : celdas) {
                boolean toca = false;
                for (net.minecraft.core.Direction d : net.minecraft.core.Direction.values()) {
                    BlockPos v = p.relative(d);
                    if (w.getBlockState(v).isAir() || picado.contains(v)) toca = true;
                }
                ok &= toca;
                picado.add(p);
            }
            return ok;
        };

        BlockGetter llana = conRoca.apply(p -> null);
        NoxMinado.Segmento recto = NoxMinado.planificarSegmento(llana, frenteH, este, false, -60, 8, null, 0, null, null);
        check("segmento recto en roca: 8 pasos, 16 bloques (pies y cabeza), frente en (8,50,0), continuo",
                recto.nodos() == 8 && recto.celdas().size() == 16 && recto.frente().equals(new BlockPos(8, 50, 0)) && recto.dir() == este && continuo.apply(llana, recto.celdas()));

        BlockGetter conAguaSeg = conRoca.apply(p -> p.equals(new BlockPos(5, 50, 1)) ? s(Blocks.WATER) : null);
        NoxMinado.Segmento juntoAgua = NoxMinado.planificarSegmento(conAguaSeg, frenteH, este, false, -60, 8, null, 0, null, null);
        check("segmento: se DETIENE antes del bloque pegado al agua (4 pasos) y no pica nada más allá",
                juntoAgua.nodos() == 4 && juntoAgua.celdas().stream().allMatch(p -> p.getX() <= 4));
        BlockGetter conLavaSeg = conRoca.apply(p -> p.equals(new BlockPos(3, 49, 0)) ? s(Blocks.LAVA) : null);
        check("segmento: lava bajo el camino (3,49,0) detiene el túnel antes de esa columna (2 pasos)",
                NoxMinado.planificarSegmento(conLavaSeg, frenteH, este, false, -60, 8, null, 0, null, null).nodos() == 2);
        BlockGetter conTablones = conRoca.apply(p -> p.equals(new BlockPos(3, 50, 0)) ? s(Blocks.OAK_PLANKS) : null);
        check("segmento: una construcción (tablones) en el camino lo detiene (2 pasos)", NoxMinado.planificarSegmento(conTablones, frenteH, este, false, -60, 8, null, 0, null, null).nodos() == 2);
        BlockGetter conGravaSeg = conRoca.apply(p -> p.equals(new BlockPos(2, 52, 0)) ? s(Blocks.GRAVEL) : null);
        check("segmento: grava sobre el techo del túnel lo detiene (1 paso)", NoxMinado.planificarSegmento(conGravaSeg, frenteH, este, false, -60, 8, null, 0, null, null).nodos() == 1);
        check("segmento: la zona de la base lo detiene (base en (4,50,0), radio 1.5 -> 2 pasos)", NoxMinado.planificarSegmento(llana, frenteH, este, false, -60, 8, new BlockPos(4, 50, 0), 1.5, null, null).nodos() == 2);
        check("segmento: un chunk sin cargar lo detiene (solo x<=3 cargado -> 3 pasos)", NoxMinado.planificarSegmento(llana, frenteH, este, false, -60, 8, null, 0, p -> p.getX() <= 3, null).nodos() == 3);
        check("segmento: un bloque vetado (ya descartado) lo detiene (1 paso)", NoxMinado.planificarSegmento(llana, frenteH, este, false, -60, 8, null, 0, null, new BlockPos(2, 50, 0)::equals).nodos() == 1);

        BlockPos superficie = new BlockPos(0, 61, 0);
        BlockGetter suelo = conRoca.apply(p -> null);
        NoxMinado.Segmento escalera = NoxMinado.planificarSegmento(suelo, superficie, este, true, 40, 8, null, 0, null, null);
        check("escalera: 8 pasos (adelante, abajo, adelante, abajo...) bajan 4 bloques: frente en (4,57,0), continua",
                escalera.nodos() == 8 && escalera.frente().equals(new BlockPos(4, 57, 0)) && !escalera.celdas().isEmpty() && continuo.apply(suelo, escalera.celdas()));
        check("escalera: respeta la altura mínima (yMinimo 59 -> no baja de y=59)", NoxMinado.planificarSegmento(suelo, superficie, este, true, 59, 8, null, 0, null, null).frente().getY() == 59);

        NoxMinado.Segmento girar = NoxMinado.elegirSegmento(conTablones, frenteH, este, false, -60, 8, null, 0, null, null);
        check("elegirSegmento: si seguir recto se atasca en 2 pasos, gira hacia un lado con más pasos (no retrocede)",
                girar != null && girar.dir() != este && girar.dir() != este.getOpposite() && girar.nodos() == 8);
        BlockGetter atrapado = conRoca.apply(p -> (p.equals(new BlockPos(1, 50, 0)) || p.equals(new BlockPos(0, 50, 1)) || p.equals(new BlockPos(0, 50, -1))) ? s(Blocks.OAK_PLANKS) : null);
        check("elegirSegmento: con las 3 salidas cerradas NO retrocede por donde vino -> null", NoxMinado.elegirSegmento(atrapado, frenteH, este, false, -60, 8, null, 0, null, null) == null);
        BlockGetter aire = mundo(p -> p.getY() <= 60 ? s(Blocks.STONE) : s(Blocks.AIR));
        check("elegirSegmento: avanzar por aire libre sin picar nada no cuenta como progreso -> null", NoxMinado.elegirSegmento(aire, superficie, null, false, -60, 8, null, 0, null, null) == null);
        check("elegirSegmento: sin dirección previa y todo igual -> elige NORTE (la primera)", NoxMinado.elegirSegmento(llana, frenteH, null, false, -60, 8, null, 0, null, null).dir() == net.minecraft.core.Direction.NORTH);

        BlockPos aguaLimpieza = new BlockPos(3, 63, 1);
        BlockGetter campo = mundo(p -> {
            if (p.equals(aguaLimpieza)) return s(Blocks.WATER);
            if (p.getY() == 64 && p.getZ() == 0 && p.getX() == 0) return s(Blocks.GRASS);
            if (p.getY() == 64 && p.getZ() == 0 && p.getX() == 1) return s(Blocks.OAK_PLANKS);
            if (p.getY() == 64 && p.getZ() == 0 && p.getX() == 2) return s(Blocks.CHEST);
            return p.getY() <= 63 ? s(Blocks.DIRT) : s(Blocks.AIR);
        });
        BlockPos ca = new BlockPos(0, 62, 0), cb = new BlockPos(3, 65, 0);
        List<BlockPos> lim = NoxMinado.bloquesALimpiar(campo, ca, cb, null, 0, 100);
        check("volumenCaja cuenta ambos extremos (4x4x1 = 16) y no depende del orden de las esquinas",
                NoxMinado.volumenCaja(0, 62, 0, 3, 65, 0) == 16 && NoxMinado.volumenCaja(3, 65, 0, 0, 62, 0) == 16);
        check("limpia hierba (1) + tierra (8) pero no madera, cofre ni aire; la tierra pegada al agua NO (8 en total)", lim.size() == 8);
        check("el bloque de tablones y el cofre nunca se despejan", !lim.contains(new BlockPos(1, 64, 0)) && !lim.contains(new BlockPos(2, 64, 0)));
        check("la tierra pegada al agua queda fuera (soltaría agua sobre la obra)", !lim.contains(new BlockPos(3, 63, 0)));
        check("orden de ARRIBA a ABAJO: primero la hierba (y=64), al final la capa y=62", lim.get(0).equals(new BlockPos(0, 64, 0)) && lim.get(lim.size() - 1).getY() == 62);
        List<BlockPos> limProt = NoxMinado.bloquesALimpiar(campo, ca, cb, new BlockPos(0, 63, 0), 1.5, 100);
        check("la zona de la base (radio 1.5 alrededor de (0,63,0)) queda protegida: quedan 3", limProt.size() == 3 && !limProt.contains(new BlockPos(0, 63, 0)));
        check("el tope 'max' se respeta", NoxMinado.bloquesALimpiar(campo, ca, cb, null, 0, 2).size() == 2);
        check("una caja gigante devuelve lista vacía (la orden se rechaza)", NoxMinado.bloquesALimpiar(campo, new BlockPos(0, 0, 0), new BlockPos(500, 200, 500), null, 0, 2000).isEmpty());
        check("limpiableSeguro: tierra sí; tablones, cofre, aire y agua no",
                NoxMinado.limpiableSeguro(campo, new BlockPos(1, 63, 0)) && !NoxMinado.limpiableSeguro(campo, new BlockPos(1, 64, 0))
                        && !NoxMinado.limpiableSeguro(campo, new BlockPos(2, 64, 0)) && !NoxMinado.limpiableSeguro(campo, new BlockPos(3, 65, 0))
                        && !NoxMinado.limpiableSeguro(campo, aguaLimpieza));

        check("esAlmacen: chest, trapped_chest, barrel y shulkers sí", NoxMinado.esAlmacen("chest") && NoxMinado.esAlmacen("trapped_chest")
                && NoxMinado.esAlmacen("barrel") && NoxMinado.esAlmacen("shulker_box") && NoxMinado.esAlmacen("red_shulker_box"));
        check("esAlmacen: convención de mods (_chest/_barrel/_crate) sí", NoxMinado.esAlmacen("iron_chest") && NoxMinado.esAlmacen("oak_barrel") && NoxMinado.esAlmacen("wooden_crate"));
        check("esAlmacen: horno, tolva, dispensador y cofre de ender NO", !NoxMinado.esAlmacen("furnace") && !NoxMinado.esAlmacen("hopper")
                && !NoxMinado.esAlmacen("dispenser") && !NoxMinado.esAlmacen("ender_chest") && !NoxMinado.esAlmacen("blast_furnace"));
        check("esAlmacen: null y vacío NO", !NoxMinado.esAlmacen(null) && !NoxMinado.esAlmacen(""));
        check("fundición: raw_iron, iron_ore y deepslate_iron_ore son mineral de 'iron'", NoxMinado.esMineralDeFundicion(new ItemStack(Items.RAW_IRON), "iron")
                && NoxMinado.esMineralDeFundicion(new ItemStack(Items.IRON_ORE), "iron") && NoxMinado.esMineralDeFundicion(new ItemStack(Items.DEEPSLATE_IRON_ORE), "iron"));
        check("fundición: pico, lingote y bloque de hierro NO son mineral", !NoxMinado.esMineralDeFundicion(new ItemStack(Items.IRON_PICKAXE), "iron")
                && !NoxMinado.esMineralDeFundicion(new ItemStack(Items.IRON_INGOT), "iron") && !NoxMinado.esMineralDeFundicion(new ItemStack(Items.IRON_BLOCK), "iron"));
        check("fundición: mineral de otro metal o pila vacía NO", !NoxMinado.esMineralDeFundicion(new ItemStack(Items.RAW_GOLD), "iron") && !NoxMinado.esMineralDeFundicion(ItemStack.EMPTY, "iron"));

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
