import com.example.cobaltbot.util.NoxSensorWriter;
import com.example.cobaltbot.util.NoxTools;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.FluidState;
import java.util.function.Function;

public class PruebasSensores {
    static int fallos = 0;
    static void check(String nombre, boolean ok) { System.out.println((ok ? "OK   " : "FAIL ") + nombre); if (!ok) fallos++; }

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
        for (net.minecraft.world.level.block.Block b : new net.minecraft.world.level.block.Block[]{Blocks.AIR, Blocks.STONE, Blocks.WATER, Blocks.LAVA, Blocks.GRASS}) b.getStateDefinition().getPossibleStates().forEach(net.minecraft.world.level.block.state.BlockBehaviour.BlockStateBase::initCache); // sin FML nadie inicializa la caché de estados

        check("iron_pickaxe  -> pickaxe (NO axe)", "pickaxe".equals(NoxTools.tipoDeHerramienta(new ItemStack(Items.IRON_PICKAXE))));
        check("esHerramienta(pico, 'axe') == false   <- el bug", !NoxTools.esHerramienta(new ItemStack(Items.IRON_PICKAXE), "axe"));
        check("esHerramienta(pico, 'pickaxe') == true", NoxTools.esHerramienta(new ItemStack(Items.NETHERITE_PICKAXE), "pickaxe"));
        check("diamond_axe   -> axe", NoxTools.esHerramienta(new ItemStack(Items.DIAMOND_AXE), "axe"));
        check("esHerramienta(hacha, 'pickaxe') == false", !NoxTools.esHerramienta(new ItemStack(Items.DIAMOND_AXE), "pickaxe"));
        check("wooden_sword  -> sword", "sword".equals(NoxTools.tipoDeHerramienta(new ItemStack(Items.WOODEN_SWORD))));
        check("stone_shovel  -> shovel", "shovel".equals(NoxTools.tipoDeHerramienta(new ItemStack(Items.STONE_SHOVEL))));
        check("golden_hoe    -> hoe", "hoe".equals(NoxTools.tipoDeHerramienta(new ItemStack(Items.GOLDEN_HOE))));
        check("shears / stick / cobblestone / vacío -> null",
                NoxTools.tipoDeHerramienta(new ItemStack(Items.SHEARS)) == null && NoxTools.tipoDeHerramienta(new ItemStack(Items.STICK)) == null
                && NoxTools.tipoDeHerramienta(new ItemStack(Items.COBBLESTONE)) == null && NoxTools.tipoDeHerramienta(ItemStack.EMPTY) == null);

        SimpleContainer inv = new SimpleContainer(36);
        inv.addItem(new ItemStack(Items.IRON_PICKAXE));
        check("inventario con solo un pico -> tools=[pickaxe]", NoxSensorWriter.resumirInventario(inv).get("tools").toString().equals("[\"pickaxe\"]"));

        double LIBRE = -1.2, LENTA = -0.2;
        check("caída libre + suelo a 12 -> vuela", NoxSensorWriter.debeVolarPorCaida(LIBRE, 12, false));
        check("caída libre + vacío (-1) -> vuela", NoxSensorWriter.debeVolarPorCaida(LIBRE, -1, false));
        check("caída libre + suelo a 4 (umbral) -> vuela", NoxSensorWriter.debeVolarPorCaida(LIBRE, 4, false));
        check("caída libre + suelo a 3 -> NO vuela (caída corta)", !NoxSensorWriter.debeVolarPorCaida(LIBRE, 3, false));
        check("caída libre + suelo a 2 pero LAVA abajo -> vuela", NoxSensorWriter.debeVolarPorCaida(LIBRE, 2, true));
        check("velocidad -0.2 (salto/escalón) + vacío -> NO vuela", !NoxSensorWriter.debeVolarPorCaida(LENTA, -1, true));
        check("velocidad justo en el umbral (-0.35) cuenta como caída", NoxSensorWriter.debeVolarPorCaida(-0.35, 20, false));
        check("velocidad subiendo (+0.4) -> NO vuela", !NoxSensorWriter.debeVolarPorCaida(0.4, -1, true));

        BlockPos pies = new BlockPos(0, 70, 0);
        BlockState AIRE = Blocks.AIR.defaultBlockState();
        check("aire y piedra en y=60 -> 9 bloques libres (69..61)",
                NoxSensorWriter.distanciaAlSuelo(mundo(p -> p.getY() <= 60 ? Blocks.STONE.defaultBlockState() : AIRE), pies, 32) == 9);
        check("piedra justo debajo (y=69) -> 0", NoxSensorWriter.distanciaAlSuelo(mundo(p -> p.getY() <= 69 ? Blocks.STONE.defaultBlockState() : AIRE), pies, 32) == 0);
        check("todo aire -> -1 (vacío)", NoxSensorWriter.distanciaAlSuelo(mundo(p -> AIRE), pies, 32) == -1);
        check("suelo a 40 bloques (fuera del alcance de 32) -> -1", NoxSensorWriter.distanciaAlSuelo(mundo(p -> p.getY() <= 29 ? Blocks.STONE.defaultBlockState() : AIRE), pies, 32) == -1);
        check("agua en y=65 cuenta como suelo (amortigua) -> 4",
                NoxSensorWriter.distanciaAlSuelo(mundo(p -> p.getY() == 65 ? Blocks.WATER.defaultBlockState() : AIRE), pies, 32) == 4);
        check("lava en y=66 cuenta como 'suelo' -> 3 (y es la que activa 'suelo no seguro')",
                NoxSensorWriter.distanciaAlSuelo(mundo(p -> p.getY() == 66 ? Blocks.LAVA.defaultBlockState() : AIRE), pies, 32) == 3);
        check("hierba alta NO es suelo (sigue bajando hasta la piedra en y=60)",
                NoxSensorWriter.distanciaAlSuelo(mundo(p -> p.getY() <= 60 ? Blocks.STONE.defaultBlockState() : p.getY() == 65 ? Blocks.GRASS.defaultBlockState() : AIRE), pies, 32) == 9);

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
