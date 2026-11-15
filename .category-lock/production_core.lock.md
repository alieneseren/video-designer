# 🔒 LOCK: PRODUCTION CORE (BASKETBOL DIŞI TÜM SİSTEMLER)
Tarih: 2026-11-13
Durum: KİLİTLİ (DOKUNULMAZ)

## Kilitli Dosyalar ve SHA256 Snapshot

- `src/aviation_media_fetcher.py` — SHA256: `3e4b7e20c219f7e532dabb67a693cb131ec8d00fb7bae34d4d52facc305e6dff`
- `src/aviation_research_engine.py` — SHA256: `f46324c79c75b1bcf26479d0441a81dab8a8f6f1db6a6672795bb93b8e677eda`
- `src/aviation_telemetry_engine.py` — SHA256: `c31e82b1d2b1851b199809bb912adbc67ddf0e2e12a293ae6e877805bcab8952`
- `src/crayon_combat_engine.py` — SHA256: `9cadfa4ec75a441da92cb261e15cb11e1613f3d44d0b261b1fe37f675fec563f`
- `src/financial_documentary_engine.py` — SHA256: `8778d6f1f6e118fb7a0517e604cfa8b98c94c5e5b3662033d1974679c5ec44f3`
- `src/story_animation_engine.py` — SHA256: `b062b896711f743846247604b83ad27ae50aa359a03ad723bcc9536725f7de47`
- `src/channel_manager.py` — SHA256: `b9b26fad9eab65a11186bbeeb82ed8621ef7814d906c54fa1bfc5fc3da73fbb2`
- `src/video_generator.py` — SHA256: `be6a5d5010e595b51167178d43a1aef3907289f22b604a3152c70a1ba99e0874`
- `src/server.py` — SHA256: `b769a2be9addb67d1fe7efa1a83f6470ce87a3dc4a83111b9a270199c1d0742c`
- `src/voice_clone_manager.py` — SHA256: `a272a98c139163082ea47cbe1f77bcca1ef287feb10b52a34beff7eb5c37e764`
- `src/remote_server_worker.py` — SHA256: `09a9e41689ac4b1de2671aeac1aa032d25260c6ab667b218d5e4e2e70756feba`
- `src/remote_runner.py` — SHA256: `96a7fd7207c69b1126dccfad2e8f3e0ce9357d753275943b7170d0324627eba3`

## Dokunulmazlık Kuralları
1. Havacılık, Askeri Çizim (Crayon), Finans ve Reddit Hikaye motorlarının fonksiyon imzaları ASLA değiştirilemez.
2. Server worker ve Channel manager ortak arayüzleri geriye dönük uyumlu kalmak zorundadır.
3. Basketbol geliştirmesi tamamen izole `src/modules/basketball/` altında çalışacak, bu dosyalarda tek bir bayt dahi oynama yapılmayacaktır.