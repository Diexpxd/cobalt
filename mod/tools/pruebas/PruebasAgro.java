import com.example.cobaltbot.util.NoxAgro;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;

import java.util.List;
import java.util.function.Function;

/** Pruebas del Bloque L (granjeo autónomo): cultivos maduros, semillas, replantado y búsqueda. */
public class PruebasAgro {
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

    static BlockState trigo(int edad) { return Blocks.WHEAT.defaultBlockState().setValue(CropBlock.AGE, edad); }

    public static void main(String[] a) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();

        check("maduro: trigo con edad 7 SÍ; con 0, 3 y 6 NO", NoxAgro.esCultivoMaduro(trigo(7)) && !NoxAgro.esCultivoMaduro(trigo(0)) && !NoxAgro.esCultivoMaduro(trigo(3)) && !NoxAgro.esCultivoMaduro(trigo(6)));
        check("maduro: zanahorias y patatas (edad 7) SÍ", NoxAgro.esCultivoMaduro(Blocks.CARROTS.defaultBlockState().setValue(CropBlock.AGE, 7))
                && NoxAgro.esCultivoMaduro(Blocks.POTATOES.defaultBlockState().setValue(CropBlock.AGE, 7)));
        check("maduro: remolacha madura es edad 3 (no 7)", NoxAgro.esCultivoMaduro(Blocks.BEETROOTS.defaultBlockState().setValue(net.minecraft.world.level.block.BeetrootBlock.AGE, 3))
                && !NoxAgro.esCultivoMaduro(Blocks.BEETROOTS.defaultBlockState().setValue(net.minecraft.world.level.block.BeetrootBlock.AGE, 2)));
        check("maduro: aire, hierba, tierra de cultivo, calabaza y sandía NO se tocan", !NoxAgro.esCultivoMaduro(Blocks.AIR.defaultBlockState()) && !NoxAgro.esCultivoMaduro(Blocks.GRASS.defaultBlockState())
                && !NoxAgro.esCultivoMaduro(Blocks.FARMLAND.defaultBlockState()) && !NoxAgro.esCultivoMaduro(Blocks.PUMPKIN.defaultBlockState()) && !NoxAgro.esCultivoMaduro(Blocks.MELON.defaultBlockState()));

        check("semilla: las semillas de trigo replantan trigo; el pan y el trigo suelto NO",
                NoxAgro.semillaDe(Blocks.WHEAT, new ItemStack(Items.WHEAT_SEEDS)) && !NoxAgro.semillaDe(Blocks.WHEAT, new ItemStack(Items.BREAD)) && !NoxAgro.semillaDe(Blocks.WHEAT, new ItemStack(Items.WHEAT)));
        check("semilla: la zanahoria replanta zanahorias, la patata patatas, y no se cruzan",
                NoxAgro.semillaDe(Blocks.CARROTS, new ItemStack(Items.CARROT)) && NoxAgro.semillaDe(Blocks.POTATOES, new ItemStack(Items.POTATO))
                        && !NoxAgro.semillaDe(Blocks.CARROTS, new ItemStack(Items.POTATO)) && !NoxAgro.semillaDe(Blocks.WHEAT, new ItemStack(Items.CARROT)));
        check("semilla: las semillas de remolacha replantan remolacha; pila vacía nunca", NoxAgro.semillaDe(Blocks.BEETROOTS, new ItemStack(Items.BEETROOT_SEEDS)) && !NoxAgro.semillaDe(Blocks.WHEAT, ItemStack.EMPTY));

        BlockGetter huerto = mundo(p -> {
            if (p.getY() == 63) return Blocks.FARMLAND.defaultBlockState();
            if (p.getY() == 64 && p.getZ() == 0) return trigo(p.getX() % 2 == 0 ? 7 : 2); // x par = madura, x impar = verde
            return Blocks.AIR.defaultBlockState();
        });
        check("replantar: sobre tierra de cultivo con el hueco libre SÍ", NoxAgro.puedeReplantar(huerto, new BlockPos(0, 64, 1)));
        check("replantar: sobre un cultivo que ya está NO (no está libre), ni sin tierra de cultivo debajo", !NoxAgro.puedeReplantar(huerto, new BlockPos(0, 64, 0)) && !NoxAgro.puedeReplantar(huerto, new BlockPos(0, 70, 0)));

        BlockPos centro = new BlockPos(0, 64, 0);
        List<BlockPos> maduros = NoxAgro.buscarMaduros(huerto, centro, 6, 100);
        check("buscar: solo los maduros (x par) dentro del radio 6: x = 0,2,4,6 y -2,-4,-6 -> 7", maduros.size() == 7 && maduros.stream().allMatch(p -> Math.abs(p.getX()) % 2 == 0));
        check("buscar: ordenados del más cercano al más lejano (el primero es el del centro)", maduros.get(0).equals(centro) && maduros.get(maduros.size() - 1).distSqr(centro) == 36.0);
        check("buscar: el tope 'max' se respeta y devuelve los MÁS cercanos", NoxAgro.buscarMaduros(huerto, centro, 6, 3).size() == 3 && NoxAgro.buscarMaduros(huerto, centro, 6, 3).stream().allMatch(p -> p.distSqr(centro) <= 4.0));
        check("buscar: radio 1 solo alcanza el cultivo maduro del propio centro", NoxAgro.buscarMaduros(huerto, centro, 1, 100).size() == 1);
        check("buscar: sin cultivos devuelve lista vacía", NoxAgro.buscarMaduros(mundo(p -> Blocks.AIR.defaultBlockState()), centro, 8, 100).isEmpty());

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
