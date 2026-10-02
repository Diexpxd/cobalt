import com.example.cobaltbot.util.NoxSupervivencia;
import com.example.cobaltbot.util.NoxSupervivencia.AtascoDetector;
import com.example.cobaltbot.util.NoxSupervivencia.AtascoDetector.Accion;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;

import java.util.function.Function;

/** Pruebas del Bloque B (supervivencia): lógica pura, sin abrir Minecraft. */
public class PruebasSupervivencia {
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

    public static void main(String[] a) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        for (Block b : new Block[]{Blocks.AIR, Blocks.STONE, Blocks.WATER, Blocks.LAVA}) {
            b.getStateDefinition().getPossibleStates().forEach(BlockBehaviour.BlockStateBase::initCache);
        }

        check("vida 14/50 (28%) con umbral 30 -> crítica", NoxSupervivencia.vidaCritica(14, 50, 30));
        check("vida 15/50 (30%) con umbral 30 -> NO crítica (estrictamente menor)", !NoxSupervivencia.vidaCritica(15, 50, 30));
        check("vida 50/50 -> no crítica", !NoxSupervivencia.vidaCritica(50, 50, 30));
        check("vida máxima 0 -> no crítica (sin división por cero)", !NoxSupervivencia.vidaCritica(0, 0, 30));
        check("histéresis: 20/50 (40%) aún NO recuperada (umbral 50)", !NoxSupervivencia.vidaRecuperada(20, 50, 50));
        check("histéresis: 25/50 (50%) recuperada", NoxSupervivencia.vidaRecuperada(25, 50, 50));
        check("curación mínima 2 aunque la nutrición sea 0", NoxSupervivencia.curacionPorNutricion(0) == 2.0F);
        check("pan (nutrición 5) cura 10", NoxSupervivencia.curacionPorNutricion(5) == 10.0F);

        SimpleContainer inv = new SimpleContainer(36);
        check("inventario vacío -> sin comida (-1)", NoxSupervivencia.mejorComida(inv, null) == -1);
        inv.addItem(new ItemStack(Items.ROTTEN_FLESH, 5));
        check("solo carne podrida (efecto perjudicial) -> NO se come (-1)", NoxSupervivencia.mejorComida(inv, null) == -1);
        inv.addItem(new ItemStack(Items.SPIDER_EYE, 2));
        check("ojo de araña (veneno) tampoco", NoxSupervivencia.mejorComida(inv, null) == -1);
        inv.addItem(new ItemStack(Items.BREAD, 3));
        int hueco = NoxSupervivencia.mejorComida(inv, null);
        check("con pan y carne podrida elige el pan", hueco >= 0 && inv.getItem(hueco).is(Items.BREAD));
        inv.addItem(new ItemStack(Items.COOKED_BEEF, 1));
        hueco = NoxSupervivencia.mejorComida(inv, null);
        check("con filete cocinado (nutrición 8) elige el filete", hueco >= 0 && inv.getItem(hueco).is(Items.COOKED_BEEF));
        inv.addItem(new ItemStack(Items.GOLDEN_APPLE, 1));
        check("la manzana dorada (efectos beneficiosos) cuenta como segura y no rompe la elección",
                NoxSupervivencia.mejorComida(inv, null) >= 0);
        SimpleContainer soloPiedra = new SimpleContainer(36);
        soloPiedra.addItem(new ItemStack(Items.COBBLESTONE, 64));
        check("ítems no comestibles -> -1", NoxSupervivencia.mejorComida(soloPiedra, null) == -1);

        double[] p = NoxSupervivencia.puntoDeHuida(0, 0, 3, 0, 14);
        check("huida: hostil al +X -> punto a -14 en X", Math.abs(p[0] + 14) < 1e-9 && Math.abs(p[1]) < 1e-9);
        p = NoxSupervivencia.puntoDeHuida(10, 10, 10, 4, 14);
        check("huida: hostil al -Z -> se mueve hacia +Z", Math.abs(p[0] - 10) < 1e-9 && Math.abs(p[1] - 24) < 1e-9);
        p = NoxSupervivencia.puntoDeHuida(0, 0, 3, 4, 10);
        check("huida en diagonal: el punto queda a exactamente 10 bloques", Math.abs(Math.hypot(p[0], p[1]) - 10) < 1e-9 && p[0] < 0 && p[1] < 0);
        p = NoxSupervivencia.puntoDeHuida(5, 5, 5, 5, 14);
        check("hostil encima: no da NaN (dirección arbitraria)", !Double.isNaN(p[0]) && !Double.isNaN(p[1]) && Math.abs(Math.hypot(p[0] - 5, p[1] - 5) - 14) < 1e-9);

        BlockState AIRE = Blocks.AIR.defaultBlockState(), PIEDRA = Blocks.STONE.defaultBlockState();
        BlockState LAVA = Blocks.LAVA.defaultBlockState(), AGUA = Blocks.WATER.defaultBlockState();
        BlockPos origen = new BlockPos(0, 64, 0);

        BlockGetter llano = mundo(q -> q.getY() <= 60 ? PIEDRA : AIRE);
        BlockPos sitio = NoxSupervivencia.buscarSitioSeguro(llano, origen, 10);
        check("suelo llano: aterriza justo debajo (pies en y=61, distancia 0)", sitio != null && sitio.getY() == 61 && sitio.getX() == 0 && sitio.getZ() == 0);

        // Charco de lava 3x3 en y=60 (x,z de -1 a 1) justo debajo
        BlockGetter conLava = mundo(q -> (q.getY() == 60 && Math.abs(q.getX()) <= 1 && Math.abs(q.getZ()) <= 1) ? LAVA : (q.getY() <= 60 ? PIEDRA : AIRE));
        sitio = NoxSupervivencia.buscarSitioSeguro(conLava, origen, 10);
        check("charco de lava debajo: encuentra un sitio", sitio != null);
        check("el sitio queda a >= 3 bloques del borde de la lava (su anillo de seguridad la excluye)",
                sitio != null && Math.max(Math.abs(sitio.getX()), Math.abs(sitio.getZ())) >= 3 && sitio.getY() == 61);
        check("es el MÁS cercano de los seguros (distancia horizontal 3)", sitio != null && sitio.getX() * sitio.getX() + sitio.getZ() * sitio.getZ() == 9);
        check("con radio 2 no hay ningún sitio seguro -> null", NoxSupervivencia.buscarSitioSeguro(conLava, origen, 2) == null);

        check("todo agua -> null (no se aterriza en agua)", NoxSupervivencia.buscarSitioSeguro(mundo(q -> q.getY() <= 60 ? AGUA : AIRE), origen, 8) == null);
        BlockPos sobreTecho = NoxSupervivencia.buscarSitioSeguro(mundo(q -> q.getY() <= 60 || q.getY() == 62 ? PIEDRA : AIRE), origen, 8);
        check("techo de UNA capa con cielo abierto encima: aterriza SOBRE el techo (pies en y=63)", sobreTecho != null && sobreTecho.getY() == 63);
        check("cueva cerrada (roca gruesa de y=62 a 80, sin hueco arriba) -> null",
                NoxSupervivencia.buscarSitioSeguro(mundo(q -> (q.getY() <= 60 || (q.getY() >= 62 && q.getY() <= 80)) ? PIEDRA : AIRE), origen, 8) == null);
        check("vacío total (sin suelo) -> null", NoxSupervivencia.buscarSitioSeguro(mundo(q -> AIRE), origen, 8) == null);

        AtascoDetector d = new AtascoDetector();
        Accion r = Accion.NADA;
        for (int i = 0; i < 30; i++) r = d.actualizar(5, 64, 5, false, 10);
        check("no quiere moverse -> nunca se considera atascado", r == Accion.NADA);

        d = new AtascoDetector();
        boolean todoNada = true;
        for (int i = 0; i < 40; i++) todoNada &= d.actualizar(i * 1.0, 64, 0, true, 10) == Accion.NADA;
        check("avanzando 1 bloque por llamada -> NADA siempre", todoNada);

        d = new AtascoDetector();
        Accion[] secuencia = new Accion[20];
        for (int i = 0; i < 20; i++) secuencia[i] = d.actualizar(5, 64, 5, true, 10);
        check("atascado: las primeras 6 llamadas (referencia + 50 ticks) son NADA",
                secuencia[0] == Accion.NADA && secuencia[1] == Accion.NADA && secuencia[5] == Accion.NADA);
        check("atascado: a los 60 ticks (llamada 7) pide SALTAR", secuencia[6] == Accion.SALTAR);
        check("atascado: 6 llamadas más -> pide VOLAR", secuencia[12] == Accion.VOLAR && secuencia[7] == Accion.NADA);
        check("sigue atascado en vuelo: vuelve a pedir VOLAR a los 3 s siguientes", secuencia[18] == Accion.VOLAR);

        d = new AtascoDetector();
        for (int i = 0; i < 7; i++) d.actualizar(5, 64, 5, true, 10); // llega a SALTAR
        d.actualizar(9, 64, 5, true, 10);                            // avanza 4 bloques: se reinicia
        Accion tras = Accion.NADA;
        for (int i = 0; i < 6; i++) tras = d.actualizar(9, 64, 5, true, 10);
        check("tras avanzar, un nuevo atasco empieza otra vez por SALTAR (no por VOLAR)", tras == Accion.SALTAR);

        d = new AtascoDetector();
        for (int i = 0; i < 4; i++) d.actualizar(5, 64, 5, true, 10);
        d.actualizar(5, 64, 5, false, 10);                           // deja de querer moverse: reinicia
        Accion tras2 = Accion.NADA;
        for (int i = 0; i < 6; i++) tras2 = d.actualizar(5, 64, 5, true, 10);
        check("dejar de querer moverse a mitad reinicia la cuenta (no hay SALTAR prematuro)", tras2 == Accion.NADA);

        d = new AtascoDetector();
        Accion tembleque = Accion.NADA;
        for (int i = 0; i < 7; i++) tembleque = d.actualizar(5 + (i % 2) * 0.3, 64, 5, true, 10);
        check("un temblor de 0.3 bloques NO cuenta como avanzar (atasco real)", tembleque == Accion.SALTAR);

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
