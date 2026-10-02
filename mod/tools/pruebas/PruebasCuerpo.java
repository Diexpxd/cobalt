import com.example.cobaltbot.util.NoxCuerpo;
import com.example.cobaltbot.util.NoxJefes;
import com.example.cobaltbot.util.NoxTools;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CampfireBlock;

/** Pruebas del Bloque F (cimientos del cuerpo): trampas, bot_id, HALT_ALL y Fase Extrema. */
public class PruebasCuerpo {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    public static void main(String[] a) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();

        check("trampa: TNT expuesta", "tnt".equals(NoxCuerpo.tipoDeTrampa(Blocks.TNT.defaultBlockState())));
        check("trampa: placas de presión (piedra, madera, pesadas)", "pressure_plate".equals(NoxCuerpo.tipoDeTrampa(Blocks.STONE_PRESSURE_PLATE.defaultBlockState()))
                && "pressure_plate".equals(NoxCuerpo.tipoDeTrampa(Blocks.OAK_PRESSURE_PLATE.defaultBlockState()))
                && "pressure_plate".equals(NoxCuerpo.tipoDeTrampa(Blocks.HEAVY_WEIGHTED_PRESSURE_PLATE.defaultBlockState())));
        check("trampa: hilo trampa y su gancho", "tripwire".equals(NoxCuerpo.tipoDeTrampa(Blocks.TRIPWIRE.defaultBlockState()))
                && "tripwire".equals(NoxCuerpo.tipoDeTrampa(Blocks.TRIPWIRE_HOOK.defaultBlockState())));
        check("trampa: telaraña", "cobweb".equals(NoxCuerpo.tipoDeTrampa(Blocks.COBWEB.defaultBlockState())));
        check("trampa: sculk shrieker y sensor", "sculk_shrieker".equals(NoxCuerpo.tipoDeTrampa(Blocks.SCULK_SHRIEKER.defaultBlockState()))
                && "sculk_sensor".equals(NoxCuerpo.tipoDeTrampa(Blocks.SCULK_SENSOR.defaultBlockState())));
        check("trampa: magma, cactus, bayas, nieve polvo, rosa del Wither", "magma".equals(NoxCuerpo.tipoDeTrampa(Blocks.MAGMA_BLOCK.defaultBlockState()))
                && "cactus".equals(NoxCuerpo.tipoDeTrampa(Blocks.CACTUS.defaultBlockState())) && "berry_bush".equals(NoxCuerpo.tipoDeTrampa(Blocks.SWEET_BERRY_BUSH.defaultBlockState()))
                && "powder_snow".equals(NoxCuerpo.tipoDeTrampa(Blocks.POWDER_SNOW.defaultBlockState())) && "wither_rose".equals(NoxCuerpo.tipoDeTrampa(Blocks.WITHER_ROSE.defaultBlockState())));
        check("trampa: fuego", "fire".equals(NoxCuerpo.tipoDeTrampa(Blocks.FIRE.defaultBlockState())));
        check("trampa: hoguera encendida SÍ, apagada NO", "campfire".equals(NoxCuerpo.tipoDeTrampa(Blocks.CAMPFIRE.defaultBlockState()))
                && NoxCuerpo.tipoDeTrampa(Blocks.CAMPFIRE.defaultBlockState().setValue(CampfireBlock.LIT, false)) == null);
        check("bloques inocuos: piedra, tablones, cofre, agua, aire NO son trampas", NoxCuerpo.tipoDeTrampa(Blocks.STONE.defaultBlockState()) == null
                && NoxCuerpo.tipoDeTrampa(Blocks.OAK_PLANKS.defaultBlockState()) == null && NoxCuerpo.tipoDeTrampa(Blocks.CHEST.defaultBlockState()) == null
                && NoxCuerpo.tipoDeTrampa(Blocks.WATER.defaultBlockState()) == null && NoxCuerpo.tipoDeTrampa(Blocks.AIR.defaultBlockState()) == null);

        check("bot_id: sin id, vacío, '*' y el propio id (cualquier caja) se aceptan", NoxCuerpo.aceptaOrden(null) && NoxCuerpo.aceptaOrden("") && NoxCuerpo.aceptaOrden("  ")
                && NoxCuerpo.aceptaOrden("*") && NoxCuerpo.aceptaOrden("Cobalt_1") && NoxCuerpo.aceptaOrden("cobalt_1"));
        check("bot_id: la orden de OTRO bot se ignora", !NoxCuerpo.aceptaOrden("Cobalt_2") && !NoxCuerpo.aceptaOrden("Nox"));

        check("HALT_ALL: texto suelto, en JSON, con minúsculas y dentro de un array", NoxCuerpo.contieneHaltAll("HALT_ALL") && NoxCuerpo.contieneHaltAll("halt_all")
                && NoxCuerpo.contieneHaltAll("[{\"action\": \"HALT_ALL\"}]") && NoxCuerpo.contieneHaltAll("{roto ... Halt_All"));
        check("HALT_ALL: no salta con órdenes normales ni con null", !NoxCuerpo.contieneHaltAll("[{\"action\":\"stop\"}]") && !NoxCuerpo.contieneHaltAll("halt") && !NoxCuerpo.contieneHaltAll(null));

        check("mega-jefe: 300 de vida sí, 299 no", NoxCuerpo.esMegaJefe(300.0F) && NoxCuerpo.esMegaJefe(1000.0F) && !NoxCuerpo.esMegaJefe(299.0F));
        NoxJefes.ParametrosKiting jefe = NoxJefes.parametros(true, false), extremo = NoxJefes.parametros(true, true), normal = NoxJefes.parametros(false, true);
        check("kiting: la Fase Extrema retrocede/mantiene/limita más lejos que un jefe normal y sin melee ni EMP",
                extremo.retroceso() > jefe.retroceso() && extremo.ideal() > jefe.ideal() && extremo.max() > jefe.max() && !extremo.permiteMelee() && !extremo.permiteEmp());
        check("kiting: sin jefe la Fase Extrema no se aplica (parámetros normales); el jefe normal no cambia",
                normal.ideal() == NoxJefes.parametros(false).ideal() && jefe.ideal() == NoxJefes.parametros(true).ideal());

        double[] dentro = NoxCuerpo.limitarAGuardia(3.0, 4.0, 0.0, 0.0, 10.0);
        check("guardia: un punto dentro del radio no se toca", dentro[0] == 3.0 && dentro[1] == 4.0);
        double[] fuera = NoxCuerpo.limitarAGuardia(30.0, 40.0, 0.0, 0.0, 10.0);
        check("guardia: un punto fuera se lleva al borde del círculo, en la misma dirección (6, 8)", Math.abs(fuera[0] - 6.0) < 1e-9 && Math.abs(fuera[1] - 8.0) < 1e-9);
        double[] centrado = NoxCuerpo.limitarAGuardia(105.0, -20.0, 100.0, -20.0, 4.0);
        check("guardia: con ancla desplazada (100,-20) y punto a 5 -> queda a 4 del ancla", Math.abs(centrado[0] - 104.0) < 1e-9 && Math.abs(centrado[1] + 20.0) < 1e-9);
        double[] enAncla = NoxCuerpo.limitarAGuardia(7.0, 7.0, 7.0, 7.0, 3.0);
        check("guardia: el propio ancla no produce NaN", enAncla[0] == 7.0 && enAncla[1] == 7.0);

        check("línea de tiro: un jugador justo en medio (a 5 de 10) SÍ", NoxCuerpo.jugadorEnLineaDeTiro(0, 0, 0, 10, 0, 0, 5, 0.5, 0, 1.6));
        check("línea de tiro: un jugador a 3 bloques del lado NO", !NoxCuerpo.jugadorEnLineaDeTiro(0, 0, 0, 10, 0, 0, 5, 0, 3, 1.6));
        check("línea de tiro: un jugador DETRÁS del que dispara no cuenta (el segmento acaba en él)", !NoxCuerpo.jugadorEnLineaDeTiro(0, 0, 0, 10, 0, 0, -5, 0, 0, 1.6));
        check("línea de tiro: un jugador MÁS ALLÁ del blanco no cuenta", !NoxCuerpo.jugadorEnLineaDeTiro(0, 0, 0, 10, 0, 0, 15, 0, 0, 1.6));
        check("línea de tiro: ni de altura (2 bloques por encima de la línea) cuenta", !NoxCuerpo.jugadorEnLineaDeTiro(0, 0, 0, 10, 0, 0, 5, 2.0, 0, 1.6));
        check("distancia punto-segmento: diagonal (3,4 -> 5) y segmento degenerado", Math.abs(NoxCuerpo.distanciaPuntoASegmento(0, 0, 0, 0, 0, 0, 3, 4, 0) - 5.0) < 1e-9
                && Math.abs(NoxCuerpo.distanciaPuntoASegmento(0, 0, 0, 10, 0, 0, 5, 3, 0) - 3.0) < 1e-9);

        ItemStack pico = new ItemStack(Items.IRON_PICKAXE);
        check("durabilidad: un pico nuevo tiene 100 % y no es frágil", NoxTools.durabilidadRestantePct(pico) == 100.0 && !NoxTools.esFragil(pico));
        pico.setDamageValue(pico.getMaxDamage() / 2);
        check("durabilidad: a la mitad ~50 % y no es frágil", Math.abs(NoxTools.durabilidadRestantePct(pico) - 50.0) < 1.0 && !NoxTools.esFragil(pico));
        pico.setDamageValue((int) (pico.getMaxDamage() * 0.96D));
        check("durabilidad: al 96 % de desgaste (4 % restante) SÍ es frágil", NoxTools.esFragil(pico) && NoxTools.durabilidadRestantePct(pico) < 5.0);
        pico.setDamageValue((int) (pico.getMaxDamage() * 0.94D));
        check("durabilidad: al 6 % restante NO es frágil todavía", !NoxTools.esFragil(pico));
        pico.setDamageValue(pico.getMaxDamage() - 1);
        check("durabilidad: a 1 usos de romperse es frágil", NoxTools.esFragil(pico));
        check("durabilidad: objetos que no se desgastan (bloque, comida, pila vacía) nunca son frágiles y valen 100 %",
                !NoxTools.esFragil(new ItemStack(Items.COOKED_BEEF)) && !NoxTools.esFragil(new ItemStack(Items.STONE)) && !NoxTools.esFragil(ItemStack.EMPTY)
                        && NoxTools.durabilidadRestantePct(ItemStack.EMPTY) == 100.0 && NoxTools.durabilidadRestantePct(new ItemStack(Items.STONE)) == 100.0);
        ItemStack espada = new ItemStack(Items.DIAMOND_SWORD);
        espada.setDamageValue(espada.getMaxDamage() - 5);
        check("durabilidad: también las armas (espada de diamante con 5 usos)", NoxTools.esFragil(espada));

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
