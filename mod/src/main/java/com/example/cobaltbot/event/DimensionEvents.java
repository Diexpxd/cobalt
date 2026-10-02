package com.example.cobaltbot.event;

import com.example.cobaltbot.CobaltMod;
import com.example.cobaltbot.entity.CobaltEntity;
import com.example.cobaltbot.util.NoxConfig;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/** Seguir al dueño entre dimensiones. */
@Mod.EventBusSubscriber(modid = CobaltMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class DimensionEvents {

    private static final int RETRASO_TICKS = 5;

    private static final class Pendiente {
        final UUID cobalt;
        final UUID jugador;
        final ResourceKey<Level> desde;
        int ticks = RETRASO_TICKS;

        Pendiente(UUID cobalt, UUID jugador, ResourceKey<Level> desde) {
            this.cobalt = cobalt;
            this.jugador = jugador;
            this.desde = desde;
        }
    }

    private static final List<Pendiente> PENDIENTES = new ArrayList<>();

    private DimensionEvents() {}

    @SubscribeEvent
    public static void alCambiarDeDimension(PlayerEvent.PlayerChangedDimensionEvent evento) {
        if (!(evento.getEntity() instanceof ServerPlayer jugador) || !NoxConfig.activo("seguir_dimension")) return;
        MinecraftServer servidor = jugador.getServer();
        ServerLevel desde = servidor == null ? null : servidor.getLevel(evento.getFrom());
        if (desde == null) return;
        for (Entity e : desde.getAllEntities()) {
            if (e instanceof CobaltEntity cobalt && jugador.getUUID().equals(cobalt.getOwnerUUID()) && cobalt.puedeSeguirEntreDimensiones()) {
                PENDIENTES.add(new Pendiente(cobalt.getUUID(), jugador.getUUID(), evento.getFrom()));
                break;
            }
        }
    }

    @SubscribeEvent
    public static void alTickDelServidor(TickEvent.ServerTickEvent evento) {
        if (evento.phase != TickEvent.Phase.END || PENDIENTES.isEmpty()) return;
        List<Pendiente> listos = new ArrayList<>();
        PENDIENTES.removeIf(p -> {
            if (--p.ticks > 0) return false;
            listos.add(p);
            return true;
        });
        for (Pendiente p : listos) ejecutar(evento.getServer(), p);
    }

    private static void ejecutar(MinecraftServer servidor, Pendiente p) {
        try {
            ServerPlayer jugador = servidor.getPlayerList().getPlayer(p.jugador);
            ServerLevel desde = servidor.getLevel(p.desde);
            if (jugador == null || desde == null || jugador.level() == desde) return; // se desconectó o ya volvió
            if (desde.getEntity(p.cobalt) instanceof CobaltEntity cobalt && cobalt.isAlive()) cobalt.cruzarDimension(jugador);
        } catch (Exception e) {
            com.mojang.logging.LogUtils.getLogger().error("[Cobalt] Falló al seguir al dueño a otra dimensión", e);
        }
    }
}
