package com.example.cobaltbot.util;

import com.mojang.datafixers.util.Pair;
import net.minecraft.core.BlockPos;
import net.minecraft.world.Container;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.state.BlockState;

/** Lógica PURA, sin estado del juego, para poder probarla sin abrir Minecraft (ver tools/pruebas/PruebasSupervivencia.java). */
public final class NoxSupervivencia {

    private NoxSupervivencia() {}

    public static boolean vidaCritica(float vida, float vidaMax, double umbralPct) {
        return vidaMax > 0 && (100.0D * vida / vidaMax) < umbralPct;
    }

    public static boolean vidaRecuperada(float vida, float vidaMax, double umbralPct) {
        return vidaMax > 0 && (100.0D * vida / vidaMax) >= umbralPct;
    }

    public static float curacionPorNutricion(int nutricion) {
        return Math.max(2.0F, nutricion * 2.0F);
    }

    public static boolean esComidaSegura(FoodProperties comida) {
        for (Pair<MobEffectInstance, Float> efecto : comida.getEffects()) {
            if (efecto.getFirst().getEffect().getCategory() == MobEffectCategory.HARMFUL) {
                return false;
            }
        }
        return true;
    }

    public static int mejorComida(Container inventario, LivingEntity comensal) {
        int mejor = -1;
        int mejorNutricion = -1;
        for (int i = 0; i < inventario.getContainerSize(); i++) {
            ItemStack pila = inventario.getItem(i);
            if (pila.isEmpty() || !pila.getItem().isEdible()) continue;
            FoodProperties comida = pila.getItem().getFoodProperties(pila, comensal);
            if (comida == null || !esComidaSegura(comida)) continue;
            if (comida.getNutrition() > mejorNutricion) {
                mejor = i;
                mejorNutricion = comida.getNutrition();
            }
        }
        return mejor;
    }

    public static double[] puntoDeHuida(double bx, double bz, double hx, double hz, double distancia) {
        double dx = bx - hx;
        double dz = bz - hz;
        double largo = Math.sqrt(dx * dx + dz * dz);
        if (largo < 1.0E-3D) {
            dx = 1.0D;
            dz = 0.0D;
            largo = 1.0D;
        }
        return new double[]{bx + dx / largo * distancia, bz + dz / largo * distancia};
    }

    public static BlockPos buscarSitioSeguro(BlockGetter nivel, BlockPos origen, int radio) {
        BlockPos mejor = null;
        double mejorDistancia = Double.MAX_VALUE;
        for (int dx = -radio; dx <= radio; dx++) {
            for (int dz = -radio; dz <= radio; dz++) {
                double distancia = dx * dx + dz * dz;
                if (distancia > (double) radio * radio || distancia >= mejorDistancia) continue;
                BlockPos pies = primerSueloSeguro(nivel, origen.offset(dx, 0, dz));
                if (pies != null) {
                    mejor = pies;
                    mejorDistancia = distancia;
                }
            }
        }
        return mejor;
    }

    private static BlockPos primerSueloSeguro(BlockGetter nivel, BlockPos columna) {
        for (int y = columna.getY() + 6; y >= columna.getY() - 12; y--) {
            BlockPos suelo = new BlockPos(columna.getX(), y, columna.getZ());
            BlockState estado = nivel.getBlockState(suelo);
            if (!estado.getFluidState().isEmpty()) return null;   // agua o lava: esta columna no sirve
            if (!estado.blocksMotion()) continue;                 // aire, hierba...: sigue bajando
            BlockPos pies = suelo.above();
            if (!nivel.getBlockState(pies).isAir() || !nivel.getBlockState(pies.above()).isAir()) return null; // sin hueco
            if (NoxSensorWriter.clasificarTerreno(nivel, pies) != NoxSensorWriter.TERRENO_SEGURO) return null;  // lava/fuego/agua cerca
            return pies;
        }
        return null;
    }

    /** Detecta que Cobalt QUIERE moverse pero no avanza. */
    public static final class AtascoDetector {
        public enum Accion { NADA, SALTAR, VOLAR }

        public static final int TICKS_ATASCO = 60;            // 3 s
        private static final double MOVIMIENTO_MINIMO = 0.5D; // bloques

        private boolean iniciado = false;
        private double refX, refY, refZ;
        private int ticksSinProgreso = 0;
        private int nivel = 0;

        public void reiniciar() {
            iniciado = false;
            ticksSinProgreso = 0;
            nivel = 0;
        }

        public Accion actualizar(double x, double y, double z, boolean quiereMoverse, int ticksTranscurridos) {
            if (!quiereMoverse) {
                reiniciar();
                return Accion.NADA;
            }
            if (!iniciado) {
                fijarReferencia(x, y, z);
                return Accion.NADA;
            }
            double dx = x - refX, dy = y - refY, dz = z - refZ;
            if (Math.sqrt(dx * dx + dy * dy + dz * dz) >= MOVIMIENTO_MINIMO) {
                fijarReferencia(x, y, z); // avanza: todo en orden
                nivel = 0;
                return Accion.NADA;
            }
            ticksSinProgreso += ticksTranscurridos;
            if (ticksSinProgreso >= TICKS_ATASCO) {
                ticksSinProgreso = 0;
                nivel++;
                return nivel == 1 ? Accion.SALTAR : Accion.VOLAR;
            }
            return Accion.NADA;
        }

        private void fijarReferencia(double x, double y, double z) {
            iniciado = true;
            refX = x;
            refY = y;
            refZ = z;
            ticksSinProgreso = 0;
        }
    }

    public static boolean puedeVolverAlCombate(float vida, float vidaMax, double umbralRecuperadaPct, int huidaRestanteTicks) {
        return vidaRecuperada(vida, vidaMax, umbralRecuperadaPct) && huidaRestanteTicks <= 0;
    }
}
