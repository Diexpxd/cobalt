package com.example.cobaltbot.util;

import net.minecraft.core.NonNullList;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.inventory.TransientCraftingContainer;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;
import net.minecraftforge.common.crafting.IShapedRecipe;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/** Crafteo universal de Cobalt: usa la MESA DE CRAFTEO DE SU INVENTARIO (una cuadrícula virtual de 3x3; no hace. */
public final class NoxCrafteo {
    private NoxCrafteo() {}

    public static final int MAX_PROFUNDIDAD = 3;
    public static final int MAX_NODOS = 600;
    public static final int MAX_CRAFTEOS = 64;
    public static final int MAX_UNIDADES = 256;
    private static final int MAX_CANDIDATOS_INGREDIENTE = 12;

    /** Una receta y cuántas veces se fabrica. */
    public record Paso(CraftingRecipe receta, int veces) {}

    /** Resultado de planificar: los pasos (en orden), o lo que falta. */
    public record Plan(List<Paso> pasos, Item objetivo, int unidades, Map<String, Integer> faltan, String motivo) {
        public boolean posible() { return motivo == null; }
        public int crafteos() { int n = 0; for (Paso p : pasos) n += p.veces(); return n; }
    }

    public static Map<Item, List<CraftingRecipe>> indice(Level nivel) {
        Map<Item, List<CraftingRecipe>> mapa = new HashMap<>();
        for (CraftingRecipe receta : nivel.getRecipeManager().getAllRecipesFor(RecipeType.CRAFTING)) {
            if (receta.isSpecial() || !receta.canCraftInDimensions(3, 3)) continue;
            ItemStack resultado = receta.getResultItem(nivel.registryAccess());
            if (resultado.isEmpty() || receta.getIngredients().isEmpty()) continue;
            mapa.computeIfAbsent(resultado.getItem(), k -> new ArrayList<>()).add(receta);
        }
        for (List<CraftingRecipe> lista : mapa.values()) lista.sort((a, b) -> Integer.compare(celdasUsadas(a), celdasUsadas(b)));
        return mapa;
    }

    private static int celdasUsadas(CraftingRecipe receta) {
        int n = 0;
        for (Ingredient i : receta.getIngredients()) if (!i.isEmpty()) n++;
        return n;
    }

    public static List<Item> resolver(String material, Map<Item, List<CraftingRecipe>> indice) {
        List<Item> exactos = new ArrayList<>();
        List<Item> sufijo = new ArrayList<>();
        if (material == null) return exactos;
        for (String parte : material.split(",")) {
            String m = parte.trim().toLowerCase(Locale.ROOT).replace(' ', '_');
            if (m.isEmpty()) continue;
            if (m.contains(":")) {
                ResourceLocation id = ResourceLocation.tryParse(m);
                Item item = id == null ? null : BuiltInRegistries.ITEM.getOptional(id).orElse(null);
                if (item != null && indice.containsKey(item) && !exactos.contains(item)) exactos.add(item);
                continue;
            }
            for (Item item : indice.keySet()) {
                String ruta = BuiltInRegistries.ITEM.getKey(item).getPath();
                if (ruta.equals(m)) { if (!exactos.contains(item)) exactos.add(item); }
                else if (ruta.endsWith("_" + m) && !sufijo.contains(item)) sufijo.add(item);
            }
        }
        sufijo.sort((a, b) -> Integer.compare(BuiltInRegistries.ITEM.getKey(a).getPath().length(), BuiltInRegistries.ITEM.getKey(b).getPath().length()));
        exactos.addAll(sufijo);
        return exactos;
    }

    /** Copia de un inventario para planificar sin tocar el real (sin límite de huecos). */
    static final class Inv {
        final List<ItemStack> pilas = new ArrayList<>();

        static Inv de(Container c) {
            Inv inv = new Inv();
            for (int i = 0; i < c.getContainerSize(); i++) if (!c.getItem(i).isEmpty()) inv.pilas.add(c.getItem(i).copy());
            return inv;
        }

        Inv copia() {
            Inv inv = new Inv();
            for (ItemStack p : pilas) inv.pilas.add(p.copy());
            return inv;
        }

        int cuenta(Ingredient ing) {
            int n = 0;
            for (ItemStack p : pilas) if (ing.test(p)) n += p.getCount();
            return n;
        }

        void quitar(Ingredient ing, int n) {
            for (ItemStack p : pilas) {
                if (n <= 0) break;
                if (!ing.test(p)) continue;
                int t = Math.min(n, p.getCount());
                p.shrink(t);
                n -= t;
            }
            pilas.removeIf(ItemStack::isEmpty);
        }

        void anadir(ItemStack pieza) {
            for (ItemStack p : pilas) {
                if (ItemStack.isSameItemSameTags(p, pieza)) { p.grow(pieza.getCount()); return; }
            }
            pilas.add(pieza.copy());
        }

        int cuentaItem(Item item) {
            int n = 0;
            for (ItemStack p : pilas) if (p.is(item)) n += p.getCount();
            return n;
        }
    }

    private static final class Contexto {
        final Level nivel;
        final Map<Item, List<CraftingRecipe>> indice;
        int nodos = 0;

        Contexto(Level nivel, Map<Item, List<CraftingRecipe>> indice) {
            this.nivel = nivel;
            this.indice = indice;
        }
    }

    public static Plan planificar(String material, int unidades, Container inventario, Level nivel) {
        Map<Item, List<CraftingRecipe>> indice = indice(nivel);
        List<Item> candidatos = resolver(material, indice);
        int cantidad = Math.max(1, Math.min(MAX_UNIDADES, unidades));
        if (candidatos.isEmpty()) return new Plan(List.of(), null, cantidad, Map.of(), "no conozco ninguna receta de mesa de crafteo para '" + material + "'");
        Plan primero = null;
        for (Item objetivo : candidatos) {
            Contexto ctx = new Contexto(nivel, indice);
            List<Paso> pasos = new ArrayList<>();
            Map<String, Integer> faltan = new LinkedHashMap<>();
            Inv inv = Inv.de(inventario);
            boolean ok = fabricar(objetivo, cantidad, inv, 0, new HashSet<>(), ctx, pasos, faltan);
            int total = 0;
            for (Paso p : pasos) total += p.veces();
            if (ok && total > MAX_CRAFTEOS) return new Plan(List.of(), objetivo, cantidad, Map.of(), "son demasiados pasos (" + total + " crafteos; máximo " + MAX_CRAFTEOS + "): pídeme menos unidades");
            if (ok) return new Plan(pasos, objetivo, cantidad, Map.of(), null);
            if (primero == null) primero = new Plan(List.of(), objetivo, cantidad, faltan, "me faltan materiales");
        }
        return primero;
    }

    private static boolean fabricar(Item objetivo, int unidades, Inv inv, int profundidad, Set<Item> ruta, Contexto ctx, List<Paso> pasos, Map<String, Integer> faltan) {
        if (profundidad > MAX_PROFUNDIDAD || ++ctx.nodos > MAX_NODOS || ruta.contains(objetivo)) return false;
        List<CraftingRecipe> recetas = ctx.indice.get(objetivo);
        if (recetas == null) return false;
        Set<Item> nuevaRuta = new HashSet<>(ruta);
        nuevaRuta.add(objetivo);
        Map<String, Integer> primerosFaltan = null;
        for (CraftingRecipe receta : recetas) {
            int porVez = Math.max(1, receta.getResultItem(ctx.nivel.registryAccess()).getCount());
            int veces = (unidades + porVez - 1) / porVez;
            Inv copia = inv.copia();
            List<Paso> sub = new ArrayList<>();
            Map<String, Integer> faltaReceta = new LinkedHashMap<>();
            boolean ok = true;
            for (Map.Entry<Ingredient, Integer> g : agrupar(receta).entrySet()) {
                Ingredient ing = g.getKey();
                int necesita = g.getValue() * veces;
                int hay = copia.cuenta(ing);
                if (hay >= necesita) { copia.quitar(ing, necesita); continue; }
                copia.quitar(ing, hay);
                if (!fabricarIngrediente(ing, necesita - hay, copia, profundidad + 1, nuevaRuta, ctx, sub, faltaReceta)) { ok = false; break; }
            }
            if (!ok) {
                if (primerosFaltan == null) primerosFaltan = faltaReceta;
                continue;
            }
            pasos.addAll(sub);
            pasos.add(new Paso(receta, veces));
            inv.pilas.clear();
            inv.pilas.addAll(copia.pilas);
            ItemStack producto = receta.getResultItem(ctx.nivel.registryAccess()).copy();
            producto.setCount(producto.getCount() * veces);
            inv.anadir(producto);
            for (ItemStack resto : restos(receta)) { if (!resto.isEmpty()) { ItemStack r = resto.copy(); r.setCount(r.getCount() * veces); inv.anadir(r); } }
            return true;
        }
        if (primerosFaltan != null) primerosFaltan.forEach((k, v) -> faltan.merge(k, v, Integer::sum));
        return false;
    }

    private static boolean fabricarIngrediente(Ingredient ing, int n, Inv inv, int profundidad, Set<Item> ruta, Contexto ctx, List<Paso> pasos, Map<String, Integer> faltan) {
        List<Item> candidatos = new ArrayList<>();
        for (ItemStack s : ing.getItems()) if (!candidatos.contains(s.getItem()) && !s.isEmpty()) candidatos.add(s.getItem());
        candidatos.sort((a, b) -> Boolean.compare(ctx.indice.containsKey(b), ctx.indice.containsKey(a)));
        int probados = 0;
        for (Item c : candidatos) {
            if (probados++ >= MAX_CANDIDATOS_INGREDIENTE) break;
            Inv prueba = inv.copia();
            List<Paso> sub = new ArrayList<>();
            if (fabricar(c, n, prueba, profundidad, ruta, ctx, sub, new LinkedHashMap<>())) {
                prueba.quitar(ing, n);
                inv.pilas.clear();
                inv.pilas.addAll(prueba.pilas);
                pasos.addAll(sub);
                return true;
            }
        }
        String nombre = candidatos.isEmpty() ? "?" : BuiltInRegistries.ITEM.getKey(candidatos.get(0)).toString();
        faltan.merge(nombre, n, Integer::sum);
        return false;
    }

    private static Map<Ingredient, Integer> agrupar(CraftingRecipe receta) {
        Map<Ingredient, Integer> grupos = new LinkedHashMap<>();
        for (Ingredient ing : receta.getIngredients()) {
            if (ing.isEmpty()) continue;
            Ingredient clave = null;
            for (Ingredient otro : grupos.keySet()) if (mismoIngrediente(otro, ing)) { clave = otro; break; }
            if (clave == null) grupos.put(ing, 1); else grupos.merge(clave, 1, Integer::sum);
        }
        return grupos;
    }

    private static boolean mismoIngrediente(Ingredient a, Ingredient b) {
        if (a == b) return true;
        ItemStack[] x = a.getItems(), y = b.getItems();
        if (x.length != y.length) return false;
        for (int i = 0; i < x.length; i++) if (!ItemStack.isSameItemSameTags(x[i], y[i])) return false;
        return true;
    }

    private static List<ItemStack> restos(CraftingRecipe receta) {
        List<ItemStack> lista = new ArrayList<>();
        for (Ingredient ing : receta.getIngredients()) {
            if (ing.isEmpty()) continue;
            for (ItemStack s : ing.getItems()) { if (s.hasCraftingRemainingItem()) { lista.add(s.getCraftingRemainingItem()); } break; }
        }
        return lista;
    }

    private static final class MenuFalso extends AbstractContainerMenu {
        MenuFalso() { super((MenuType<?>) null, -1); }
        @Override public ItemStack quickMoveStack(Player p, int i) { return ItemStack.EMPTY; }
        @Override public boolean stillValid(Player p) { return true; }
    }

    public static List<ItemStack> ejecutar(CraftingRecipe receta, Container inventario, Level nivel) {
        CraftingContainer rejilla = new TransientCraftingContainer(new MenuFalso(), 3, 3);
        int ancho = 3, alto = 3;
        List<Ingredient> celdas = new ArrayList<>(receta.getIngredients());
        boolean conForma = receta instanceof IShapedRecipe<?>;
        int w = conForma ? ((IShapedRecipe<?>) receta).getRecipeWidth() : 0;
        int[] restante = new int[inventario.getContainerSize()];
        for (int i = 0; i < restante.length; i++) restante[i] = inventario.getItem(i).getCount();
        int[] slotDe = new int[9];
        java.util.Arrays.fill(slotDe, -1);
        for (int k = 0; k < celdas.size() && k < 9; k++) {
            Ingredient ing = celdas.get(k);
            if (ing.isEmpty()) continue;
            int celda = conForma ? (k % w) + (k / w) * ancho : k;
            if (celda >= ancho * alto) return null;
            int elegido = -1;
            for (int s = 0; s < restante.length && elegido < 0; s++) if (restante[s] > 0 && ing.test(inventario.getItem(s))) elegido = s;
            if (elegido < 0) return null;
            restante[elegido]--;
            slotDe[celda] = elegido;
            rejilla.setItem(celda, inventario.getItem(elegido).copyWithCount(1));
        }
        if (!receta.matches(rejilla, nivel)) return null;
        ItemStack producto = receta.assemble(rejilla, nivel.registryAccess());
        if (producto.isEmpty()) return null;
        NonNullList<ItemStack> restos = receta.getRemainingItems(rejilla);
        for (int c = 0; c < 9; c++) if (slotDe[c] >= 0) inventario.getItem(slotDe[c]).shrink(1);
        List<ItemStack> salida = new ArrayList<>();
        salida.add(producto);
        for (ItemStack r : restos) if (!r.isEmpty()) salida.add(r);
        return salida;
    }
}
