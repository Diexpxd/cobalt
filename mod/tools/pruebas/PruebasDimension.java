import com.example.cobaltbot.util.NoxDimension;
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

import java.util.function.Function;

/** Pruebas de "seguir entre dimensiones": cuándo cruza y dónde aparece (nunca en un portal, en el vacío ni en lava). */
public class PruebasDimension {
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

    static boolean portalCerca(BlockGetter n, NoxDimension.Llegada l) {
        BlockPos p = BlockPos.containing(l.x(), l.y(), l.z());
        for (int dx = -1; dx <= 1; dx++) for (int dz = -1; dz <= 1; dz++) for (int dy = -1; dy <= 2; dy++) {
            if (n.getBlockState(p.offset(dx, dy, dz)).is(Blocks.NETHER_PORTAL)) return true;
        }
        return false;
    }

    public static void main(String[] a) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        for (Block b : new Block[]{Blocks.AIR, Blocks.STONE, Blocks.LAVA, Blocks.WATER, Blocks.NETHER_PORTAL, Blocks.CACTUS, Blocks.FIRE, Blocks.OBSIDIAN,
                Blocks.NETHERRACK, Blocks.OAK_FENCE, Blocks.MAGMA_BLOCK}) {
            b.getStateDefinition().getPossibleStates().forEach(BlockBehaviour.BlockStateBase::initCache);
        }
        BlockPos jugador = new BlockPos(0, 65, 0);

        check("seguir: lo sigue, sin tarea, cerca y visto hace poco -> cruza", NoxDimension.debeSeguir(true, false, false, 5, 12.0));
        check("seguir: si NO lo estaba siguiendo (guardia, quieto) no cruza", !NoxDimension.debeSeguir(false, false, false, 5, 12.0));
        check("seguir: con una tarea en curso (minando...) no cruza", !NoxDimension.debeSeguir(true, true, false, 5, 12.0));
        check("seguir: congelado por OMEGA no cruza", !NoxDimension.debeSeguir(true, false, true, 5, 12.0));
        check("seguir: a más de 40 bloques del dueño no cruza (40 exactos sí)", !NoxDimension.debeSeguir(true, false, false, 5, 40.1) && NoxDimension.debeSeguir(true, false, false, 5, 40.0));
        check("seguir: si hace más de 60 ticks que no ve al dueño no cruza (60 exactos sí)", !NoxDimension.debeSeguir(true, false, false, 61, 5.0) && NoxDimension.debeSeguir(true, false, false, 60, 5.0));
        check("seguir: datos raros (tiempo negativo, distancia NaN) no cruzan", !NoxDimension.debeSeguir(true, false, false, -1, 5.0) && !NoxDimension.debeSeguir(true, false, false, 5, Double.NaN));

        BlockGetter llano = mundo(p -> p.getY() <= 64 ? s(Blocks.NETHERRACK) : s(Blocks.AIR));
        NoxDimension.Llegada l = NoxDimension.buscarLlegada(llano, jugador);
        check("llegada: en suelo llano aparece CAMINANDO (sin vuelo) sobre el suelo, a la altura de los pies del jugador", l != null && !l.vuelo() && l.y() == 65.0);
        check("llegada: no se monta en el jugador: a >= 2 bloques de él", l != null && Math.hypot(l.x() - 0.5, l.z() - 0.5) >= 1.9);
        check("llegada: pero cerca (a 3 bloques o menos)", l != null && Math.hypot(l.x() - 0.5, l.z() - 0.5) <= 3.0);

        BlockGetter conPortal = mundo(p -> {
            if (p.getY() <= 64) return s(Blocks.NETHERRACK);
            boolean marco = p.getZ() == 0 && p.getX() >= -1 && p.getX() <= 2 && p.getY() >= 65 && p.getY() <= 69;
            if (marco) return (p.getX() >= 0 && p.getX() <= 1 && p.getY() >= 66 && p.getY() <= 68) ? s(Blocks.NETHER_PORTAL) : s(Blocks.OBSIDIAN);
            return s(Blocks.AIR);
        });
        NoxDimension.Llegada lp = NoxDimension.buscarLlegada(conPortal, new BlockPos(0, 66, 0));
        check("portal: con el jugador DENTRO del portal, Cobalt aparece en suelo firme fuera de él", lp != null && !lp.vuelo());
        check("portal: y a >= 2 bloques de cualquier bloque de portal (no vuelve a cruzar al instante)", lp != null && !portalCerca(conPortal, lp));
        BlockGetter soloPortal = mundo(p -> p.getY() <= 64 ? s(Blocks.NETHERRACK) : (p.getX() == 0 && p.getZ() == 0 && p.getY() >= 65 && p.getY() <= 67 ? s(Blocks.NETHER_PORTAL) : s(Blocks.AIR)));
        NoxDimension.Llegada l2 = NoxDimension.buscarLlegada(soloPortal, new BlockPos(0, 65, 0));
        check("portal: aunque el portal esté justo al lado, nunca elige un hueco pegado a él", l2 != null && !portalCerca(soloPortal, l2));

        BlockGetter cornisaPortal = mundo(p -> {
            if (p.getZ() == 0 && p.getY() <= 64 && p.getX() >= 1 && p.getX() <= 6) return s(Blocks.NETHERRACK);
            if (p.getX() == 3 && p.getZ() == 0 && p.getY() >= 65 && p.getY() <= 67) return s(Blocks.NETHER_PORTAL);
            return s(Blocks.AIR);
        });
        NoxDimension.Llegada lcp = NoxDimension.buscarLlegada(cornisaPortal, new BlockPos(1, 65, 0));
        check("portal: en una cornisa estrecha con el portal en medio elige el lado LEJANO (x>=5), no el hueco pegado al portal (x=4)",
                lcp != null && !lcp.vuelo() && lcp.x() >= 5.0 && !portalCerca(cornisaPortal, lcp));

        BlockGetter vacio = mundo(p -> s(Blocks.AIR));
        NoxDimension.Llegada lv = NoxDimension.buscarLlegada(vacio, new BlockPos(0, 100, 0));
        check("aire: sin nada debajo Cobalt aparece VOLANDO (no se cae)", lv != null && lv.vuelo() && Math.abs(lv.y() - 100.0) <= 3.0);
        BlockGetter sobreLava = mundo(p -> p.getY() <= 40 ? s(Blocks.LAVA) : s(Blocks.AIR));
        NoxDimension.Llegada ll = NoxDimension.buscarLlegada(sobreLava, new BlockPos(0, 70, 0));
        check("lava: flotando sobre un lago de lava aparece en vuelo, nunca dentro de la lava", ll != null && ll.vuelo() && ll.y() >= 67.0);
        BlockGetter rasLava = mundo(p -> p.getY() <= 65 ? s(Blocks.LAVA) : s(Blocks.AIR));
        NoxDimension.Llegada lr = NoxDimension.buscarLlegada(rasLava, new BlockPos(0, 66, 0));
        check("lava: con la lava justo debajo (aire sobre la superficie) NO cuenta como suelo: aparece en vuelo y fuera de la lava", lr != null && lr.vuelo() && lr.y() >= 66.0);

        BlockGetter lavaTodo = mundo(p -> s(Blocks.LAVA));
        check("lava: rodeado de lava por todas partes -> null (no aparece, se avisa)", NoxDimension.buscarLlegada(lavaTodo, jugador) == null);
        BlockGetter enterrado = mundo(p -> s(Blocks.STONE));
        check("roca: dentro de roca maciza -> null", NoxDimension.buscarLlegada(enterrado, jugador) == null);
        BlockGetter agua = mundo(p -> p.getY() <= 70 ? s(Blocks.WATER) : s(Blocks.AIR));
        NoxDimension.Llegada la = NoxDimension.buscarLlegada(agua, new BlockPos(0, 71, 0));
        check("agua: sobre un océano aparece en el aire sobre la superficie, en vuelo (no en el agua)", la != null && la.vuelo() && la.y() >= 71.0);
        BlockGetter cactus = mundo(p -> p.getY() <= 63 ? s(Blocks.STONE) : (p.getY() == 64 ? s(Blocks.CACTUS) : s(Blocks.AIR)));
        NoxDimension.Llegada lc = NoxDimension.buscarLlegada(cactus, new BlockPos(0, 65, 0));
        check("peligro: un suelo de cactus no es suelo firme (vuelo)", lc != null && lc.vuelo());
        BlockGetter magma = mundo(p -> p.getY() <= 64 ? s(Blocks.MAGMA_BLOCK) : s(Blocks.AIR));
        check("peligro: un suelo de bloques de magma tampoco", NoxDimension.buscarLlegada(magma, new BlockPos(0, 65, 0)).vuelo());
        BlockGetter fuego = mundo(p -> p.getY() <= 64 ? s(Blocks.NETHERRACK) : (Math.abs(p.getX()) <= 1 && Math.abs(p.getZ()) <= 1 && p.getY() == 65 ? s(Blocks.FIRE) : s(Blocks.AIR)));
        NoxDimension.Llegada lf = NoxDimension.buscarLlegada(fuego, new BlockPos(0, 65, 0));
        check("peligro: el fuego se evita (aparece fuera del corro de llamas)", lf != null && !lf.vuelo() && (Math.abs(lf.x() - 0.5) > 1.5 || Math.abs(lf.z() - 0.5) > 1.5));

        BlockGetter cornisa = mundo(p -> (p.getX() >= 3 && p.getY() <= 64) ? s(Blocks.STONE) : s(Blocks.AIR));
        NoxDimension.Llegada lco = NoxDimension.buscarLlegada(cornisa, new BlockPos(0, 65, 0));
        check("preferencia: prefiere suelo firme a 3 bloques (caminando) antes que aire junto al jugador (volando)", lco != null && !lco.vuelo() && lco.x() >= 3.0);
        BlockGetter minimo = mundo(p -> (p.getX() == 0 && p.getZ() == 0 && p.getY() <= 64) ? s(Blocks.STONE) : s(Blocks.AIR));
        NoxDimension.Llegada lm = NoxDimension.buscarLlegada(minimo, new BlockPos(0, 65, 0));
        check("preferencia: sobre un pilar de un bloque (solo hay suelo bajo el jugador) usa ese suelo, sin vuelo", lm != null && !lm.vuelo() && lm.x() == 0.5 && lm.z() == 0.5);
        BlockGetter techoBajo = mundo(p -> p.getY() <= 64 ? s(Blocks.NETHERRACK) : (p.getY() == 66 ? s(Blocks.NETHERRACK) : s(Blocks.AIR)));
        NoxDimension.Llegada lb = NoxDimension.buscarLlegada(techoBajo, new BlockPos(0, 65, 0));
        check("hueco: con un techo a 1 bloque sobre el suelo NO cabe Cobalt (1,8): nunca elige y=65 ni y=66 (dentro de la roca), sino encima del techo (y=67) sobre suelo firme",
                lb != null && lb.y() == 67.0 && !lb.vuelo());
        BlockGetter altoMundo = mundo(p -> s(Blocks.AIR));
        NoxDimension.Llegada lal = NoxDimension.buscarLlegada(altoMundo, new BlockPos(0, 318, 0));
        check("limite: cerca del techo del mundo la llegada no sale del rango construible", lal != null && lal.y() <= 320.0 - 3.0 && lal.y() >= -63.0);

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
