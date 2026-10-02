package com.example.cobaltbot.registry;

import com.example.cobaltbot.CobaltMod;
import com.example.cobaltbot.item.NoxSummonerItem;
import net.minecraft.world.item.Item;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

public class ModItems {
    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(ForgeRegistries.ITEMS, CobaltMod.MOD_ID);

    public static final RegistryObject<Item> NOX_SUMMONER = ITEMS.register("nox_summoner",
            () -> new NoxSummonerItem(new Item.Properties().stacksTo(1)));

    public static void register(IEventBus eventBus) {
        ITEMS.register(eventBus);
    }
}
