import com.example.cobaltbot.util.NoxChip;
import com.example.cobaltbot.util.NoxCuerpo;
import com.example.cobaltbot.util.NoxJefes;
import com.example.cobaltbot.util.NoxSupervivencia;
import net.minecraft.SharedConstants;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/** Pruebas de las correcciones de la primera tanda de pruebas en juego: inventario en el chip, altura de jefes. */
public class PruebasCorreccion {
    static int fallos = 0;

    static void check(String nombre, boolean ok) {
        System.out.println((ok ? "OK   " : "FAIL ") + nombre);
        if (!ok) fallos++;
    }

    static boolean igual(SimpleContainer a, SimpleContainer b) {
        if (a.getContainerSize() != b.getContainerSize()) return false;
        for (int i = 0; i < a.getContainerSize(); i++) {
            if (!ItemStack.matches(a.getItem(i), b.getItem(i))) return false;
        }
        return true;
    }

    public static void main(String[] args) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();

        SimpleContainer inv = new SimpleContainer(36);
        inv.setItem(0, new ItemStack(Items.DIAMOND, 5));
        inv.setItem(7, new ItemStack(Items.COOKED_BEEF, 32));
        inv.setItem(35, new ItemStack(Items.IRON_PICKAXE)); // la última casilla (la que se perdía al morir con un cofre de 27)
        ItemStack nombrada = new ItemStack(Items.NETHERITE_SWORD);
        nombrada.setHoverName(net.minecraft.network.chat.Component.literal("Espada de prueba"));
        inv.setItem(20, nombrada);
        ListTag lista = NoxChip.serializar(inv);
        check("chip: se serializan solo las casillas con objetos (4)", lista.size() == 4);
        SimpleContainer restaurado = new SimpleContainer(36);
        restaurado.setItem(3, new ItemStack(Items.DIRT, 9)); // basura previa: debe desaparecer
        NoxChip.deserializar(lista, restaurado);
        check("chip: la copia restaurada es idéntica, casilla por casilla (incluida la 35 y el nombre personalizado)", igual(inv, restaurado));
        check("chip: lo que había antes en el destino se vacía (no se mezcla)", restaurado.getItem(3).isEmpty());
        check("chip: la casilla 35 conserva su objeto", restaurado.getItem(35).is(Items.IRON_PICKAXE) && restaurado.getItem(0).getCount() == 5);

        // el chip es un ItemStack con NBT
        ItemStack chip = new ItemStack(Items.PAPER);
        check("chip: sin nada guardado hayInventarioGuardado es falso y restaurar no toca nada", !NoxChip.hayInventarioGuardado(chip) && NoxChip.restaurarInventario(chip, restaurado) == 0 && igual(inv, restaurado));
        NoxChip.guardarInventario(chip, inv);
        check("chip: tras guardar hay inventario en el NBT del chip", NoxChip.hayInventarioGuardado(chip));
        SimpleContainer nuevo = new SimpleContainer(36);
        int n = NoxChip.restaurarInventario(chip, nuevo);
        check("chip: al desplegar se recupera TODO (5 + 32 + 1 + 1 = 39 objetos) idéntico", n == 39 && igual(inv, nuevo));
        ItemStack copiaChip = chip.copy(); // el chip sobrevive a guardarse/cargarse como cualquier ítem
        SimpleContainer tercero = new SimpleContainer(36);
        NoxChip.restaurarInventario(ItemStack.of(copiaChip.save(new CompoundTag())), tercero);
        check("chip: el inventario sobrevive a guardar y cargar el ítem entero (como al salir y entrar del mundo)", igual(inv, tercero));
        NoxChip.borrarInventarioGuardado(chip);
        check("chip: borrarlo (al morir Cobalt, para no duplicar lo que quedó en el cofre) lo deja sin copia", !NoxChip.hayInventarioGuardado(chip));
        ItemStack vacio = ItemStack.EMPTY;
        NoxChip.guardarInventario(vacio, inv);
        check("chip: sin chip (ItemStack vacío) nada revienta ni se guarda", !NoxChip.hayInventarioGuardado(vacio));
        NoxChip.guardarInventario(chip, new SimpleContainer(36));
        check("chip: un inventario vacío guardado cuenta como 'sin inventario'", !NoxChip.hayInventarioGuardado(chip));

        // NBT raro: casilla fuera de rango o basura
        ListTag raro = new ListTag();
        CompoundTag fuera = new CompoundTag();
        fuera.putByte("Slot", (byte) 120);
        new ItemStack(Items.GOLD_INGOT).save(fuera);
        raro.add(fuera);
        raro.add(new CompoundTag());
        SimpleContainer c2 = new SimpleContainer(36);
        NoxChip.deserializar(raro, c2);
        check("chip: NBT corrupto (casilla 120 o compuesto vacío) se ignora sin reventar", NoxChip.contarObjetos(c2) == 0);
        NoxChip.deserializar(null, c2);
        check("chip: lista nula tampoco revienta", NoxChip.contarObjetos(c2) == 0);

        // huella
        SimpleContainer h1 = new SimpleContainer(36), h2 = new SimpleContainer(36);
        h1.setItem(0, new ItemStack(Items.DIAMOND, 5));
        h2.setItem(0, new ItemStack(Items.DIAMOND, 5));
        int base = NoxChip.huella(h1);
        check("huella: contenidos iguales dan la misma huella", base == NoxChip.huella(h2));
        h2.getItem(0).grow(1);
        check("huella: cambiar la cantidad cambia la huella", base != NoxChip.huella(h2));
        h2.setItem(0, new ItemStack(Items.EMERALD, 5));
        check("huella: cambiar el objeto cambia la huella", base != NoxChip.huella(h2));
        h2.setItem(0, ItemStack.EMPTY);
        h2.setItem(1, new ItemStack(Items.DIAMOND, 5));
        check("huella: mover el mismo objeto a otra casilla cambia la huella", base != NoxChip.huella(h2));
        check("huella: contarObjetos suma las cantidades", NoxChip.contarObjetos(inv) == 39);

        check("altura: dentro de la banda no se toca (ancla 80, y=85)", NoxJefes.limitarAltura(85.0, 80.0, 14.0, 4.0) == 85.0);
        check("altura: un jefe en el cielo (y=200) no sube a Cobalt más de 14 sobre el dueño: 94", NoxJefes.limitarAltura(200.0, 80.0, 14.0, 4.0) == 94.0);
        check("altura: tampoco baja de 4 bajo el ancla: 76", NoxJefes.limitarAltura(10.0, 80.0, 14.0, 4.0) == 76.0);
        check("altura: los bordes exactos se respetan", NoxJefes.limitarAltura(94.0, 80.0, 14.0, 4.0) == 94.0 && NoxJefes.limitarAltura(76.0, 80.0, 14.0, 4.0) == 76.0);

        check("vuelo: de cerca (<= 12) sigue a 1,3 como siempre", NoxCuerpo.velocidadSeguimientoVuelo(5.0, 3.0) == 1.3 && NoxCuerpo.velocidadSeguimientoVuelo(12.0, 3.0) == 1.3);
        check("vuelo: a 24 bloques acelera (2,3) y a 36 llega a 3,0 (el tope)", Math.abs(NoxCuerpo.velocidadSeguimientoVuelo(24.0, 3.0) - 2.3) < 1e-9 && NoxCuerpo.velocidadSeguimientoVuelo(36.0, 3.0) == 3.0);
        check("vuelo: nunca pasa del tope, aunque esté a 500 bloques", NoxCuerpo.velocidadSeguimientoVuelo(500.0, 3.0) == 3.0 && NoxCuerpo.velocidadSeguimientoVuelo(500.0, 2.0) == 2.0);
        check("vuelo: un tope raro (menor que la base) nunca la baja de 1,3; NaN tampoco", NoxCuerpo.velocidadSeguimientoVuelo(40.0, 0.5) == 1.3 && NoxCuerpo.velocidadSeguimientoVuelo(Double.NaN, 3.0) == 1.3);
        check("vuelo: crece con la distancia (monótono)", NoxCuerpo.velocidadSeguimientoVuelo(18.0, 3.0) < NoxCuerpo.velocidadSeguimientoVuelo(30.0, 3.0));

        check("huida: recuperado pero con 4 s de huida por cumplir NO vuelve al combate (el fallo: comer curaba y 'recuperaba' al instante)",
                !NoxSupervivencia.puedeVolverAlCombate(31.0f, 50.0f, 50.0, 80));
        check("huida: recuperado y con la huida cumplida SÍ vuelve", NoxSupervivencia.puedeVolverAlCombate(31.0f, 50.0f, 50.0, 0) && NoxSupervivencia.puedeVolverAlCombate(31.0f, 50.0f, 50.0, -10));
        check("huida: cumplida la huida pero sin recuperarse (15/50) NO vuelve", !NoxSupervivencia.puedeVolverAlCombate(15.0f, 50.0f, 50.0, 0));

        check("vuelo directo: en el destino (distancia 0) no se mueve", NoxCuerpo.velocidadObjetivoVuelo(0.0, 1.3) == 0.0);
        check("vuelo directo: lejos, 1,3 -> 0,39 bloques/tick (~7,8 bloques/s) y 3,0 -> 0,90", Math.abs(NoxCuerpo.velocidadObjetivoVuelo(50.0, 1.3) - 0.39) < 1e-9 && Math.abs(NoxCuerpo.velocidadObjetivoVuelo(50.0, 3.0) - 0.90) < 1e-9);
        check("vuelo directo: frena al acercarse (a 0,8 bloques 0,32 y a 0,5 bloques con modificador 3,0 solo 0,2) y nunca pasa de la velocidad máxima (1 bloque con 1,3 = 0,39)", Math.abs(NoxCuerpo.velocidadObjetivoVuelo(0.8, 1.3) - 0.32) < 1e-9 && Math.abs(NoxCuerpo.velocidadObjetivoVuelo(0.5, 3.0) - 0.2) < 1e-9 && Math.abs(NoxCuerpo.velocidadObjetivoVuelo(1.0, 1.3) - 0.39) < 1e-9);
        check("vuelo directo: crece con el modificador (más lejos acelera más)", NoxCuerpo.velocidadObjetivoVuelo(40.0, 1.3) < NoxCuerpo.velocidadObjetivoVuelo(40.0, 2.5));
        check("vuelo directo: datos raros (NaN, negativos) dan 0, nunca NaN ni negativo", NoxCuerpo.velocidadObjetivoVuelo(Double.NaN, 1.3) == 0.0 && NoxCuerpo.velocidadObjetivoVuelo(10.0, -1.0) == 0.0 && NoxCuerpo.velocidadObjetivoVuelo(-5.0, 1.3) == 0.0);
        double alcanzada = 0.0, objetivoV = NoxCuerpo.velocidadObjetivoVuelo(30.0, 1.3);
        for (int i = 0; i < 20; i++) alcanzada += (objetivoV - alcanzada) * 0.3; // la aceleración suave del control
        check("vuelo directo: la aceleración suave llega al 99 % de la velocidad objetivo en 20 ticks (1 s)", alcanzada / objetivoV > 0.99 && alcanzada <= objetivoV);

        System.out.println(fallos == 0 ? "\nRESULTADO: TODO OK" : "\nRESULTADO: " + fallos + " FALLOS");
        System.exit(fallos == 0 ? 0 : 1);
    }
}
