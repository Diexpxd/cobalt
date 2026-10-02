import com.example.cobaltbot.util.NoxBloques;
import net.minecraft.SharedConstants;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.Half;

/** Pruebas de H5 (schematics): estados de bloque y el ítem que hace falta para colocarlos. */
public class PruebasBloques {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    public static void main(String[] a) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();

        BlockState escalera = Blocks.OAK_STAIRS.defaultBlockState();
        NoxBloques.Resultado r = NoxBloques.aplicarPropiedades(escalera, "facing=east,half=top");
        check("escalera 'facing=east,half=top': orientación y mitad aplicadas (2 aplicadas, 0 ignoradas)",
                r.estado().getValue(StairBlock.FACING) == Direction.EAST && r.estado().getValue(StairBlock.HALF) == Half.TOP && r.aplicadas() == 2 && r.ignoradas() == 0);
        check("y el resto del estado no cambia (sigue siendo la misma escalera, sin agua)", r.estado().is(Blocks.OAK_STAIRS) && !r.estado().getValue(BlockStateProperties.WATERLOGGED));

        r = NoxBloques.aplicarPropiedades(escalera, "colour=red");
        check("propiedad que no existe en ese bloque: se ignora y se cuenta (estado intacto)", r.estado() == escalera && r.aplicadas() == 0 && r.ignoradas() == 1);
        r = NoxBloques.aplicarPropiedades(escalera, "facing=up");
        check("valor inválido para esa propiedad (una escalera no mira 'up'): se ignora", r.estado() == escalera && r.ignoradas() == 1);
        r = NoxBloques.aplicarPropiedades(escalera, "facing=south,colour=red,half=medio");
        check("mezcla: aplica lo válido (facing=south) e ignora lo demás (2 ignoradas)", r.estado().getValue(StairBlock.FACING) == Direction.SOUTH && r.aplicadas() == 1 && r.ignoradas() == 2);

        for (String vacio : new String[] {null, "", "   "}) {
            r = NoxBloques.aplicarPropiedades(escalera, vacio);
            check("sin propiedades (" + (vacio == null ? "null" : "'" + vacio + "'") + "): devuelve el mismo estado, 0 y 0", r.estado() == escalera && r.aplicadas() == 0 && r.ignoradas() == 0);
        }
        check("base null: no lanza y devuelve null", NoxBloques.aplicarPropiedades(null, "facing=east").estado() == null);
        for (String roto : new String[] {"facing", "=east", "facing=", "=", "facing==east"}) {
            r = NoxBloques.aplicarPropiedades(escalera, roto);
            check("mal formada '" + roto + "': no lanza y no cambia nada", r.estado() == escalera && r.aplicadas() == 0);
        }
        r = NoxBloques.aplicarPropiedades(escalera, " facing = west , half = top ,, ");
        check("los espacios se toleran y las comas vacías no cuentan como error", r.estado().getValue(StairBlock.FACING) == Direction.WEST && r.estado().getValue(StairBlock.HALF) == Half.TOP && r.aplicadas() == 2 && r.ignoradas() == 0);

        BlockState trigo = Blocks.WHEAT.defaultBlockState();
        check("propiedad entera: age=7 se aplica", NoxBloques.aplicarPropiedades(trigo, "age=7").estado().getValue(CropBlock.AGE) == 7);
        check("entero fuera de rango (age=99) o no numérico (age=x): se ignora", NoxBloques.aplicarPropiedades(trigo, "age=99").estado() == trigo && NoxBloques.aplicarPropiedades(trigo, "age=x").estado() == trigo);
        check("propiedad booleana: waterlogged=true se aplica", NoxBloques.aplicarPropiedades(escalera, "waterlogged=true").estado().getValue(BlockStateProperties.WATERLOGGED));
        check("una puerta: half=upper y hinge=right", NoxBloques.aplicarPropiedades(Blocks.OAK_DOOR.defaultBlockState(), "half=upper,hinge=right").aplicadas() == 2);

        r = NoxBloques.aplicarPropiedades(escalera, "facing=east," + "x".repeat(400));
        check("entrada absurdamente larga: se descarta entera (no se aplica ni siquiera lo válido del principio)", r.estado() == escalera && r.aplicadas() == 0 && r.ignoradas() == 1);
        StringBuilder muchas = new StringBuilder("facing=east");
        for (int i = 0; i < 40; i++) muchas.append(",p").append(i).append("=1");
        r = NoxBloques.aplicarPropiedades(escalera, muchas.toString());
        check("más de 24 propiedades: se corta (aplica facing, ignora el resto sin recorrerlo todo)", r.estado().getValue(StairBlock.FACING) == Direction.EAST && r.aplicadas() == 1 && r.ignoradas() >= 1 && r.ignoradas() <= 24);

        check("bloqueDe: 'minecraft:stone' es piedra", NoxBloques.bloqueDe("minecraft:stone") == Blocks.STONE);
        check("bloqueDe: aire, id inexistente, id inválido y vacío -> null", NoxBloques.bloqueDe("minecraft:air") == null && NoxBloques.bloqueDe("minecraft:no_existe") == null
                && NoxBloques.bloqueDe("Esto NO es un id!") == null && NoxBloques.bloqueDe("") == null && NoxBloques.bloqueDe(null) == null);

        check("itemDe: piedra -> item piedra; antorcha de pared -> antorcha; cartel de pared -> cartel; polvo de redstone -> redstone",
                NoxBloques.itemDe(Blocks.STONE) == Items.STONE && NoxBloques.itemDe(Blocks.WALL_TORCH) == Items.TORCH && NoxBloques.itemDe(Blocks.OAK_WALL_SIGN) == Items.OAK_SIGN
                        && NoxBloques.itemDe(Blocks.REDSTONE_WIRE) == Items.REDSTONE);
        check("itemDe: agua, lava y null no tienen ítem (null)", NoxBloques.itemDe(Blocks.WATER) == null && NoxBloques.itemDe(Blocks.LAVA) == null && NoxBloques.itemDe(null) == null);
        check("idDe: 'minecraft:torch'; null -> ''", NoxBloques.idDe(Items.TORCH).equals("minecraft:torch") && NoxBloques.idDe(null).isEmpty());

        System.out.println(fallos == 0 ? "\nPRUEBAS DE BLOQUES OK" : "\nFALLOS: " + fallos);
        System.exit(fallos == 0 ? 0 : 1);
    }
}
