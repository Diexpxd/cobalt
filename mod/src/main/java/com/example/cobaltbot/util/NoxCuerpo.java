package com.example.cobaltbot.util;

import net.minecraft.world.level.block.BaseFireBlock;
import net.minecraft.world.level.block.BasePressurePlateBlock;
import net.minecraft.world.level.block.CactusBlock;
import net.minecraft.world.level.block.CampfireBlock;
import net.minecraft.world.level.block.MagmaBlock;
import net.minecraft.world.level.block.PowderSnowBlock;
import net.minecraft.world.level.block.SculkSensorBlock;
import net.minecraft.world.level.block.SculkShriekerBlock;
import net.minecraft.world.level.block.SweetBerryBushBlock;
import net.minecraft.world.level.block.TntBlock;
import net.minecraft.world.level.block.TripWireBlock;
import net.minecraft.world.level.block.TripWireHookBlock;
import net.minecraft.world.level.block.WebBlock;
import net.minecraft.world.level.block.WitherRoseBlock;
import net.minecraft.world.level.block.state.BlockState;

import java.util.Locale;

/** Reglas PURAS de los sensores y primitivas que Python usa para decidir. */
public final class NoxCuerpo {

    private NoxCuerpo() {}

    public static final String BOT_ID = "Cobalt_1";

    public static final float VIDA_MEGA_JEFE = 300.0F;

    public static boolean aceptaOrden(String botIdOrden) {
        if (botIdOrden == null) return true;
        String id = botIdOrden.trim();
        return id.isEmpty() || id.equals("*") || id.equalsIgnoreCase(BOT_ID);
    }

    public static boolean contieneHaltAll(String contenido) {
        return contenido != null && contenido.toUpperCase(Locale.ROOT).contains("HALT_ALL");
    }

    public static boolean esMegaJefe(float vidaMax) {
        return vidaMax >= VIDA_MEGA_JEFE;
    }

    public static double[] limitarAGuardia(double x, double z, double ax, double az, double radio) {
        double dx = x - ax, dz = z - az;
        double d = Math.sqrt(dx * dx + dz * dz);
        if (d <= radio || d < 1.0E-9D) return new double[]{x, z};
        double f = radio / d;
        return new double[]{ax + dx * f, az + dz * f};
    }

    public static double distanciaPuntoASegmento(double ax, double ay, double az, double bx, double by, double bz, double px, double py, double pz) {
        double abx = bx - ax, aby = by - ay, abz = bz - az;
        double largo2 = abx * abx + aby * aby + abz * abz;
        double t = largo2 < 1.0E-12D ? 0.0D : ((px - ax) * abx + (py - ay) * aby + (pz - az) * abz) / largo2;
        t = Math.max(0.0D, Math.min(1.0D, t));
        double cx = ax + abx * t - px, cy = ay + aby * t - py, cz = az + abz * t - pz;
        return Math.sqrt(cx * cx + cy * cy + cz * cz);
    }

    public static boolean jugadorEnLineaDeTiro(double ax, double ay, double az, double bx, double by, double bz, double px, double py, double pz, double margen) {
        return distanciaPuntoASegmento(ax, ay, az, bx, by, bz, px, py, pz) < margen;
    }

    public static String tipoDeTrampa(BlockState estado) {
        var bloque = estado.getBlock();
        if (bloque instanceof TntBlock) return "tnt";
        if (bloque instanceof BasePressurePlateBlock) return "pressure_plate";
        if (bloque instanceof TripWireBlock || bloque instanceof TripWireHookBlock) return "tripwire";
        if (bloque instanceof WebBlock) return "cobweb";
        if (bloque instanceof SculkShriekerBlock) return "sculk_shrieker";
        if (bloque instanceof SculkSensorBlock) return "sculk_sensor";
        if (bloque instanceof MagmaBlock) return "magma";
        if (bloque instanceof CactusBlock) return "cactus";
        if (bloque instanceof SweetBerryBushBlock) return "berry_bush";
        if (bloque instanceof PowderSnowBlock) return "powder_snow";
        if (bloque instanceof WitherRoseBlock) return "wither_rose";
        if (bloque instanceof BaseFireBlock) return "fire";
        if (bloque instanceof CampfireBlock && estado.getValue(CampfireBlock.LIT)) return "campfire";
        return null;
    }

    public static double velocidadSeguimientoVuelo(double distancia, double maximo) {
        double base = 1.3D;
        if (Double.isNaN(distancia) || distancia <= 12.0D) return base;
        return Math.min(Math.max(base, maximo), base + (distancia - 12.0D) / 12.0D);
    }

    public static double velocidadObjetivoVuelo(double distancia, double modificador) {
        if (Double.isNaN(distancia) || Double.isNaN(modificador) || distancia <= 0.0D || modificador <= 0.0D) return 0.0D;
        return Math.min(distancia * 0.4D, 0.30D * modificador);
    }
}
