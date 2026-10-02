import com.example.cobaltbot.util.NoxTerreno;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;

import java.util.List;
import java.util.function.Function;

/** Pruebas del Bloque N (terreno): superficie, plan de aplanado y búsqueda de fluidos. */
public class PruebasTerreno {
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

    public static void main(String[] a) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        for (Block b : new Block[]{Blocks.AIR, Blocks.STONE, Blocks.DIRT, Blocks.GRASS_BLOCK, Blocks.WATER, Blocks.LAVA, Blocks.OAK_LOG,
                Blocks.OAK_LEAVES, Blocks.OAK_PLANKS, Blocks.CHEST, Blocks.GRASS, Blocks.SAND, Blocks.DIAMOND_ORE, Blocks.DEEPSLATE_IRON_ORE,
                Blocks.ANCIENT_DEBRIS, Blocks.GLASS}) {
            b.getStateDefinition().getPossibleStates().forEach(BlockBehaviour.BlockStateBase::initCache);
        }

        BlockGetter llano = mundo(p -> p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR));
        int[] sup = NoxTerreno.superficie(llano, 3, 3, 100, 0);
        check("superficie: un suelo llano en y=64 da {64, SUELO}", sup[0] == 64 && sup[1] == NoxTerreno.SUELO);
        BlockGetter conHojas = mundo(p -> p.getY() <= 64 ? s(Blocks.STONE) : (p.getY() == 70 || p.getY() == 71 ? s(Blocks.OAK_LEAVES) : s(Blocks.AIR)));
        check("superficie: la copa de un árbol (hojas) se atraviesa: el terreno sigue siendo y=64", NoxTerreno.superficie(conHojas, 0, 0, 100, 0)[0] == 64);
        BlockGetter conHierba = mundo(p -> p.getY() <= 64 ? s(Blocks.STONE) : (p.getY() == 65 ? s(Blocks.GRASS) : s(Blocks.AIR)));
        check("superficie: la hierba alta no cuenta como suelo", NoxTerreno.superficie(conHierba, 0, 0, 100, 0)[0] == 64);
        BlockGetter lago = mundo(p -> p.getY() <= 60 ? s(Blocks.STONE) : (p.getY() <= 64 ? s(Blocks.WATER) : s(Blocks.AIR)));
        int[] l = NoxTerreno.superficie(lago, 0, 0, 100, 0);
        check("superficie: un lago da {64, AGUA}", l[0] == 64 && l[1] == NoxTerreno.AGUA);
        BlockGetter lagoLava = mundo(p -> p.getY() <= 60 ? s(Blocks.STONE) : (p.getY() <= 63 ? s(Blocks.LAVA) : s(Blocks.AIR)));
        check("superficie: la lava se distingue del agua", NoxTerreno.superficie(lagoLava, 0, 0, 100, 0)[1] == NoxTerreno.LAVA);
        BlockGetter tejado = mundo(p -> p.getY() <= 64 ? s(Blocks.STONE) : (p.getY() == 65 ? s(Blocks.OAK_PLANKS) : s(Blocks.AIR)));
        int[] t = NoxTerreno.superficie(tejado, 0, 0, 100, 0);
        check("superficie: un tejado de tablones es OBSTACULO (no suelo natural) en y=65", t[0] == 65 && t[1] == NoxTerreno.OBSTACULO);
        check("superficie: un cofre también es OBSTACULO", NoxTerreno.superficie(mundo(p -> p.getY() == 65 ? s(Blocks.CHEST) : (p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR))), 0, 0, 100, 0)[1] == NoxTerreno.OBSTACULO);
        int[] vacio = NoxTerreno.superficie(mundo(p -> s(Blocks.AIR)), 0, 0, 100, 10);
        check("superficie: sin nada devuelve {yMin-1, VACIO}", vacio[0] == 9 && vacio[1] == NoxTerreno.VACIO);

        BlockGetter relieve = mundo(p -> {
            int alto = 64;
            if (p.getX() >= 2 && p.getX() <= 3 && p.getZ() >= 0 && p.getZ() <= 1) alto = 67;
            if (p.getX() == 6 && p.getZ() >= 0 && p.getZ() <= 1) alto = 62;
            if (p.getY() <= alto) return p.getY() == alto ? s(Blocks.DIRT) : s(Blocks.STONE);
            return s(Blocks.AIR);
        });
        NoxTerreno.PlanAplanado plan = NoxTerreno.planAplanado(relieve, 0, 0, 7, 1, 64, null, 0, null, 4000);
        check("aplanado: 16 columnas (8 x 2), ninguna bloqueada", plan.columnas() == 16 && plan.columnasBloqueadas() == 0);
        check("aplanado: la colina (4 columnas x 3 de alto) da 12 bloques a cavar", plan.cavar().size() == 12);
        check("aplanado: se cava DE ARRIBA ABAJO y solo por encima del nivel objetivo (y 65-67)", plan.cavar().get(0).getY() == 67 && plan.cavar().get(plan.cavar().size() - 1).getY() == 65
                && plan.cavar().stream().allMatch(p -> p.getY() > 64));
        check("aplanado: el valle (2 columnas x 2 de hondo) da 4 bloques a rellenar (y 63 y 64 en x=6)", plan.rellenar().size() == 4 && plan.rellenar().stream().allMatch(p -> p.getX() == 6 && p.getY() >= 63 && p.getY() <= 64));
        check("aplanado: se rellena DE ABAJO ARRIBA", plan.rellenar().get(0).getY() == 63 && plan.rellenar().get(3).getY() == 64);
        check("aplanado: no está truncado", !plan.truncado());

        BlockGetter conObstaculos = mundo(p -> {
            if (p.getX() == 1 && p.getZ() == 0 && p.getY() == 66) return s(Blocks.CHEST);   // construcción sobre la columna x=1
            if (p.getX() == 1 && p.getZ() == 0 && p.getY() <= 65) return s(Blocks.STONE);
            if (p.getX() == 3 && p.getZ() == 0 && p.getY() <= 64) return p.getY() == 64 ? s(Blocks.WATER) : s(Blocks.STONE); // lago
            if (p.getX() == 5 && p.getZ() == 0) return s(Blocks.AIR);                                                        // precipicio sin fondo
            return p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR);
        });
        NoxTerreno.PlanAplanado bl = NoxTerreno.planAplanado(conObstaculos, 0, 0, 6, 0, 64, null, 0, null, 4000);
        check("aplanado: una columna con un cofre encima, un lago y un precipicio se DEJAN (3 bloqueadas de 7) y no se toca nada de ellas",
                bl.columnas() == 7 && bl.columnasBloqueadas() == 3 && bl.cavar().stream().noneMatch(p -> p.getX() == 1) && bl.rellenar().stream().noneMatch(p -> p.getX() == 3 || p.getX() == 5));
        BlockGetter picoJunto = mundo(p -> {
            if (p.getX() == 0 && p.getZ() == 0 && p.getY() == 65) return s(Blocks.STONE);
            if (p.getX() == 1 && p.getZ() == 0 && p.getY() == 65) return s(Blocks.WATER);
            return p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR);
        });
        NoxTerreno.PlanAplanado pj = NoxTerreno.planAplanado(picoJunto, 0, 0, 0, 0, 64, null, 0, null, 4000);
        check("aplanado: un bloque de la colina con agua en una cara NO se cava (columna bloqueada)", pj.cavar().isEmpty() && pj.columnasBloqueadas() == 1);
        NoxTerreno.PlanAplanado prot = NoxTerreno.planAplanado(relieve, 0, 0, 7, 1, 64, new BlockPos(2, 64, 0), 3.0, null, 4000);
        check("aplanado: la zona de la base queda protegida (esas columnas no se tocan)", prot.columnasBloqueadas() >= 4 && prot.cavar().size() < plan.cavar().size());
        NoxTerreno.PlanAplanado sinCargar = NoxTerreno.planAplanado(relieve, 0, 0, 7, 1, 64, null, 0, p -> p.getX() < 4, 4000);
        check("aplanado: las columnas en chunks sin cargar se tratan como bloqueadas", sinCargar.columnasBloqueadas() == 8);
        NoxTerreno.PlanAplanado corto = NoxTerreno.planAplanado(relieve, 0, 0, 7, 1, 64, null, 0, null, 5);
        check("aplanado: el tope de bloques trunca el plan y lo dice", corto.truncado() && corto.cavar().size() + corto.rellenar().size() <= 5 + 4);
        BlockGetter montana = mundo(p -> p.getY() <= 64 + 20 ? s(Blocks.STONE) : s(Blocks.AIR));
        check("aplanado: una montaña de 20 de alto (más de MAX_CORTE) NO se aplana", NoxTerreno.planAplanado(montana, 0, 0, 1, 1, 64, null, 0, null, 4000).cavar().isEmpty());
        BlockGetter foso = mundo(p -> p.getY() <= 64 - 20 ? s(Blocks.STONE) : s(Blocks.AIR));
        check("aplanado: un foso de 20 de hondo (más de MAX_RELLENO) NO se rellena", NoxTerreno.planAplanado(foso, 0, 0, 1, 1, 64, null, 0, null, 4000).rellenar().isEmpty());
        check("aplanado: las esquinas invertidas (x2 < x1) dan el mismo plan", NoxTerreno.planAplanado(relieve, 7, 1, 0, 0, 64, null, 0, null, 4000).cavar().size() == plan.cavar().size());

        BlockGetter duna = mundo(p -> p.getX() == 0 && p.getZ() == 0 ? (p.getY() <= 66 ? s(Blocks.SAND) : s(Blocks.AIR)) : (p.getY() <= 64 ? s(Blocks.SAND) : s(Blocks.AIR)));
        NoxTerreno.PlanAplanado pd = NoxTerreno.planAplanado(duna, 0, 0, 1, 0, 64, null, 0, null, 4000);
        check("aplanado: una duna de ARENA (2 de alto) sí se corta (en túneles la arena no se pica, aquí sí)", pd.cavar().size() == 2 && pd.columnasBloqueadas() == 0);
        BlockGetter casaSobre = mundo(p -> p.getY() == 65 ? s(Blocks.OAK_PLANKS) : (p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR)));
        check("aplanado: tablones (una construcción) encima de la columna la BLOQUEAN", NoxTerreno.planAplanado(casaSobre, 0, 0, 0, 0, 64, null, 0, null, 4000).columnasBloqueadas() == 1);
        check("cavableSeguro: piedra y arena sí; tablones, cofre, aire y agua no",
                NoxTerreno.cavableSeguro(llano, new BlockPos(0, 64, 0), null, 0) && NoxTerreno.cavableSeguro(duna, new BlockPos(0, 66, 0), null, 0)
                        && !NoxTerreno.cavableSeguro(casaSobre, new BlockPos(0, 65, 0), null, 0) && !NoxTerreno.cavableSeguro(llano, new BlockPos(0, 70, 0), null, 0));

        BlockGetter macizo = mundo(p -> p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR));
        BlockGetter conVeta = mundo(p -> p.getX() == 0 && p.getY() == 30 && p.getZ() == 0 ? s(Blocks.DIAMOND_ORE) : (p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR)));
        BlockPos veta = new BlockPos(0, 30, 0);
        check("rayos X: una mena ENTERRADA no se revela", !NoxTerreno.debeRevelar(conVeta, veta, conVeta.getBlockState(veta)));
        BlockGetter vetaAlAire = mundo(p -> p.getX() == 0 && p.getY() == 30 && p.getZ() == 0 ? s(Blocks.DIAMOND_ORE) : (p.getY() == 30 && p.getX() == 1 && p.getZ() == 0 ? s(Blocks.AIR) : (p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR))));
        check("rayos X: la misma mena con una cara al aire SÍ se ve", NoxTerreno.debeRevelar(vetaAlAire, veta, vetaAlAire.getBlockState(veta)));
        BlockGetter vetaTrasCristal = mundo(p -> p.getX() == 0 && p.getY() == 30 && p.getZ() == 0 ? s(Blocks.DIAMOND_ORE) : (p.getX() == 1 && p.getY() == 30 && p.getZ() == 0 ? s(Blocks.GLASS) : (p.getY() <= 64 ? s(Blocks.STONE) : s(Blocks.AIR))));
        check("rayos X: una mena tras un cristal también se ve (el cristal no oculta)", NoxTerreno.debeRevelar(vetaTrasCristal, veta, vetaTrasCristal.getBlockState(veta)));
        check("rayos X: la piedra macizo enterrada SÍ se cuenta (una estructura sólida se copia entera)", NoxTerreno.debeRevelar(macizo, new BlockPos(0, 30, 0), s(Blocks.STONE)));
        check("rayos X: menas de pizarra abisal y escombros antiguos también cuentan como menas", NoxTerreno.esMenaOculta(s(Blocks.DEEPSLATE_IRON_ORE)) && NoxTerreno.esMenaOculta(s(Blocks.ANCIENT_DEBRIS)) && !NoxTerreno.esMenaOculta(s(Blocks.STONE)) && !NoxTerreno.esMenaOculta(s(Blocks.OAK_PLANKS)));

        BlockGetter pozaLava = mundo(p -> {
            if (p.getY() <= 60) return s(Blocks.STONE);
            if (p.getY() >= 61 && p.getY() <= 63 && Math.abs(p.getX()) <= 2 && Math.abs(p.getZ()) <= 2) return s(Blocks.LAVA);
            return s(Blocks.AIR);
        });
        List<BlockPos> lava = NoxTerreno.buscarFluido(pozaLava, new BlockPos(0, 63, 0), 6, true, 1000);
        check("fluidos: una poza de lava de 5x5x3 = 75 celdas", lava.size() == 75);
        check("fluidos: se ordenan de ARRIBA a ABAJO (primero y=63) y la primera es la más cercana al centro", lava.get(0).getY() == 63 && lava.get(0).equals(new BlockPos(0, 63, 0)) && lava.get(74).getY() == 61);
        check("fluidos: buscar AGUA no encuentra la lava (y viceversa)", NoxTerreno.buscarFluido(pozaLava, new BlockPos(0, 63, 0), 6, false, 1000).isEmpty());
        check("fluidos: el tope 'max' se respeta y devuelve las de arriba", NoxTerreno.buscarFluido(pozaLava, new BlockPos(0, 63, 0), 6, true, 10).size() == 10 && NoxTerreno.buscarFluido(pozaLava, new BlockPos(0, 63, 0), 6, true, 10).stream().allMatch(p -> p.getY() == 63));
        check("fluidos: el radio limita la búsqueda (radio 1 = solo el entorno inmediato)", NoxTerreno.buscarFluido(pozaLava, new BlockPos(0, 63, 0), 1, true, 1000).size() <= 7);
        check("fluidos: tocaFluido detecta un vecino de lava y no confunde con agua", NoxTerreno.tocaFluido(pozaLava, new BlockPos(3, 63, 0), true) && !NoxTerreno.tocaFluido(pozaLava, new BlockPos(3, 63, 0), false) && !NoxTerreno.tocaFluido(pozaLava, new BlockPos(5, 63, 0), true));

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
