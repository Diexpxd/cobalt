package com.example.cobaltbot.util;

import net.minecraft.server.level.ServerChunkCache;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;

import java.util.Comparator;
import java.util.List;

/** El chunk loader de Cobalt: en vez de /forceload (que se GUARDA en el mundo y pisa los del jugador) usa. */
public final class NoxChunkLoader {
    private NoxChunkLoader() {}

    public static final int TIMEOUT_TICKS = 40;
    public static final TicketType<ChunkPos> TICKET = TicketType.create("cobalt_carga", Comparator.comparingLong(ChunkPos::toLong), TIMEOUT_TICKS);

    public static void mantener(ServerLevel nivel, List<int[]> chunks) {
        ServerChunkCache cache = nivel.getChunkSource();
        for (int[] c : chunks) {
            ChunkPos pos = new ChunkPos(c[0], c[1]);
            cache.addRegionTicket(TICKET, pos, 2, pos);
        }
    }

    public static void soltar(ServerLevel nivel, List<int[]> chunks) {
        ServerChunkCache cache = nivel.getChunkSource();
        for (int[] c : chunks) {
            ChunkPos pos = new ChunkPos(c[0], c[1]);
            cache.removeRegionTicket(TICKET, pos, 2, pos);
        }
    }
}
