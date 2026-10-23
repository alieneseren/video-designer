import json
import os
import re
import hashlib
from typing import Optional
from pathlib import Path
from .models import Scenario, Message, Character, DEFAULT_AVATAR
from .voice_profiles import VOICE_PROFILES, VOICE_PROFILES_EN, get_voice_profiles, get_default_voice

BASE_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets"
BASE_WALLPAPERS = BASE_ASSETS_DIR / "wallpapers"
BASE_AVATARS = BASE_ASSETS_DIR / "avatars"

BUILTIN_SCENARIOS = {
    "apartman_grubu": Scenario(
        title="Apartman Yöneticisi VS Robot Süpürge! 🏢🤖",
        contact_name="Apartman Sakinleri 🏢",
        contact_status="Yönetici Halil, Fatma Teyze, Selim, Siz",
        contact_avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "urban_wall.jpg") if (BASE_WALLPAPERS / "urban_wall.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        is_group=True,
        group_participants="Yönetici Halil, Fatma Teyze, Selim, Siz",
        characters={
            "contact": Character(
                name="Apartman Sakinleri",
                role="contact",
                voice="tr-TR-AhmetNeural",
                pitch="-10Hz",
                rate="-5%",
                avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="Ben",
                role="user",
                voice="tr-TR-AhmetNeural",
                pitch="+5Hz",
                rate="+10%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", sender_name="Yönetici Halil Bey", text="Komşular 4. kattan aşağı halı kim silkeledi az önce? 😡", timestamp="15:30"),
            Message(id="2", sender="user", text="Yönetici bey balkonda çay içiyordum üstüm başım yün oldu valla!", timestamp="15:31"),
            Message(id="3", sender="contact", sender_name="Fatma Teyze", text="Ben silkelemedim benim halım kuru temizlemede evladım!", timestamp="15:31"),
            Message(id="4", sender="user", text="Fatma teyze halıda büyük harflerle 'WELCOME' yazıyordu seninkinin aynısı... 😂", timestamp="15:32"),
            Message(id="5", sender="contact", sender_name="Yönetici Halil Bey", text="Kamera kayıtlarına baktım şimdi... Halıyı balkondan atan robot süpürgeymiş!! 🤖💀", timestamp="15:33"),
            Message(id="6", sender="contact", sender_name="Selim", text="Robot bile apartmandan kaçmaya çalışıyor abi ahahahahaha 🤦‍♂️😂", timestamp="15:34"),
            Message(id="7", sender="user", text="Akıllı süpürgeye aidat yazalım yönetici bey kaçış yolu arıyor 🧹💸", timestamp="15:35")
        ],
        bgm_track="quirky_troll"
    ),
    "hali_saha_grubu": Scenario(
        title="Maça 1 Saat Kala Kaleci İptali! ⚽🤦‍♂️",
        contact_name="Halı Saha 23:00 ⚽",
        contact_status="Kaptan Burak, Kaleci Emre, Murat, Siz",
        contact_avatar=str(BASE_AVATARS / "boy.jpg") if (BASE_AVATARS / "boy.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "cozy_wood.jpg") if (BASE_WALLPAPERS / "cozy_wood.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        is_group=True,
        group_participants="Kaptan Burak, Kaleci Emre, Murat, Siz",
        characters={
            "contact": Character(
                name="Halı Saha Grubu",
                role="contact",
                voice="tr-TR-AhmetNeural",
                pitch="+2Hz",
                rate="+8%",
                avatar=str(BASE_AVATARS / "boy.jpg") if (BASE_AVATARS / "boy.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="Ben",
                role="user",
                voice="tr-TR-AhmetNeural",
                pitch="+12Hz",
                rate="+15%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", sender_name="Kaleci Emre", text="Beyler çok acil durum var bu akşam maça gelemiyorum ben 😭", timestamp="21:40"),
            Message(id="2", sender="contact", sender_name="Kaptan Burak", text="Emre maça 1 saat kaldı dalga mı geçiyorsun kalede kim duracak?! 😡", timestamp="21:41"),
            Message(id="3", sender="user", text="Yine hanımdan izin alamadı kesin koltuğa bağladılar bunu 😂", timestamp="21:42"),
            Message(id="4", sender="contact", sender_name="Kaleci Emre", text="Valla alakam yok kayınvalidem mantı açmış gitmezsem miras iptal 🥟💀", timestamp="21:43"),
            Message(id="5", sender="contact", sender_name="Murat", text="Kanka mantıyı kaleye koyalım gelen topları hamurla tutarız 🤦‍♂️", timestamp="21:44"),
            Message(id="6", sender="contact", sender_name="Kaleci Emre", text="Yedek olarak 74 yaşındaki dedemi gönderiyorum kalede heykel gibi durur 👴🧤", timestamp="21:45"),
            Message(id="7", sender="user", text="Deden geçen maç forvetteydi zaten iki gol attı getir baş tacı ahahaha ⚽👑", timestamp="21:46")
        ],
        bgm_track="viral_bounce"
    ),
    "aile_meclisi": Scenario(
        title="Kayıp Kumanda Krizi! 🏡📺",
        contact_name="Geniş Aile Meclisi 🏡",
        contact_status="Annem 🧡, Babam 👑, Dayım, Siz",
        contact_avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "doodle_beige.jpg") if (BASE_WALLPAPERS / "doodle_beige.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        is_group=True,
        group_participants="Annem 🧡, Babam 👑, Dayım, Siz",
        characters={
            "contact": Character(
                name="Aile Meclisi",
                role="contact",
                voice="tr-TR-EmelNeural",
                pitch="-8Hz",
                rate="-5%",
                avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="Ben",
                role="user",
                voice="tr-TR-AhmetNeural",
                pitch="+4Hz",
                rate="+8%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", sender_name="Babam 👑", text="Bu evin televizyon kumandası nerede yine haberleri kaçırıyorum?! 😡", timestamp="18:50"),
            Message(id="2", sender="contact", sender_name="Annem 🧡", text="Bey koltuğun arasına bak dedik ya sana yüz kere!", timestamp="18:51"),
            Message(id="3", sender="user", text="Baba kanepenin altındaki terliğin içine baktın mı bazen oraya kaçıyor 😂", timestamp="18:52"),
            Message(id="4", sender="contact", sender_name="Babam 👑", text="Buzdolabına bile baktım yok! Kim sakladıysa harçlığı keserim!", timestamp="18:53"),
            Message(id="5", sender="contact", sender_name="Dayım", text="Enişte kumanda senin sol elinde ya, yarım saattir onunla çay karıştırıyorsun ☕💀", timestamp="18:54"),
            Message(id="6", sender="contact", sender_name="Annem 🧡", text="Allah seni ne yapmasın bey ben de mutfakta arıyorum ahahaha 🤦‍♀️😂", timestamp="18:55"),
            Message(id="7", sender="user", text="Haberler bitti baba kumandaya şeker at da afiyetle iç bari ahaha 📺☕", timestamp="18:56")
        ],
        bgm_track="comedy_upbeat"
    ),
    "ev_sahibi": Scenario(
        title="Açgözlü Ev Sahibi",
        contact_name="Hacı Dayı (Ev Sahibi)",
        contact_status="çevrimiçi",
        contact_avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "dark_slate.jpg") if (BASE_WALLPAPERS / "dark_slate.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        characters={
            "contact": Character(
                name="Ev Sahibi",
                role="contact",
                voice="tr-TR-AhmetNeural",
                pitch="-8Hz",
                rate="-5%",
                avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="Ben",
                role="user",
                voice="tr-TR-AhmetNeural",
                pitch="+5Hz",
                rate="+10%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", text="Evladım kiranın günü geldi, bu ay yüzde 150 zam yaptık hayırlı olsun", timestamp="10:00"),
            Message(id="2", sender="user", text="Hacı amca yasal sınır yüzde 25 değil miydi ya?", timestamp="10:01"),
            Message(id="3", sender="contact", text="Yasa devlette geçerli evladım, bu binada benim kanunlarım var", timestamp="10:02"),
            Message(id="4", sender="user", text="O zaman binanın çatısı akıyor onu da kendi kanununla yaptır amca", timestamp="10:03"),
            Message(id="5", sender="contact", text="O akıntı değil evladım, üst kattan gelen doğal kaynak suyu, faturaya ekliyorum 💧", timestamp="10:04")
        ],
        bgm_track="cunning_scheme"
    ),
    "anne_teknoloji": Scenario(
        title="Annemin Akıllı Telefonla İmtihanı! 📱😂",
        contact_name="Annem 🧡",
        contact_status="çevrimiçi",
        contact_avatar=str(BASE_AVATARS / "mom.jpg") if (BASE_AVATARS / "mom.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "botanical_shadow.jpg") if (BASE_WALLPAPERS / "botanical_shadow.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        characters={
            "contact": Character(
                name="Annem",
                role="contact",
                voice="tr-TR-EmelNeural",
                pitch="-5Hz",
                rate="-4%",
                avatar=str(BASE_AVATARS / "mom.jpg") if (BASE_AVATARS / "mom.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="Ben",
                role="user",
                voice="tr-TR-AhmetNeural",
                pitch="+0Hz",
                rate="+8%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", text="Oğlum telefon bozuldu ekran simsiyah oldu açılmıyor 😱", timestamp="11:30"),
            Message(id="2", sender="user", text="Anne kapatıp açmayı denedin mi?", timestamp="11:31"),
            Message(id="3", sender="contact", text="Denedim olmuyor, karanlıkta sadece gözlerim görünüyor 👁️", timestamp="11:31"),
            Message(id="4", sender="user", text="Anne telefonun ön kamerasını açıp elinle lensi kapatmış olabilir misin?", timestamp="11:32"),
            Message(id="5", sender="contact", text="Aaa vallahi doğru! Neyse kütüphanedeydin di mi sen?", timestamp="11:33"),
            Message(id="6", sender="user", text="Evet anne harıl harıl ders çalışıyorum 📚", timestamp="11:34"),
            Message(id="7", sender="contact", text="İyi o zaman arkadaki langırt seslerini de kitaba sorarsın eve gelince terlik var 🩴🏃‍♂️", timestamp="11:35")
        ],
        bgm_track="viral_bounce"
    )
}

BUILTIN_SCENARIOS_EN = {
    "roommate_vacuum": Scenario(
        title="Roommate Battle: Robot Vacuum Escape! 🤖🏢",
        contact_name="Roommates 🏡",
        contact_status="Alex, Sarah, Mike, You",
        contact_avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "urban_wall.jpg") if (BASE_WALLPAPERS / "urban_wall.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        is_group=True,
        group_participants="Alex, Sarah, Mike, You",
        characters={
            "contact": Character(
                name="Roommates",
                role="contact",
                voice="en-US-ChristopherNeural",
                pitch="+2Hz",
                rate="+5%",
                avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="You",
                role="user",
                voice="en-US-GuyNeural",
                pitch="+8Hz",
                rate="+10%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", sender_name="Alex", text="Guys who left the front door open?! The robot vacuum is literally rolling down the sidewalk 🤖💀", timestamp="14:30"),
            Message(id="2", sender="user", text="I thought it was just exploring its life choices bro 😂", timestamp="14:31"),
            Message(id="3", sender="contact", sender_name="Sarah", text="It just cleaned the neighbor's porch and crossed the street!!", timestamp="14:31"),
            Message(id="4", sender="user", text="Even the vacuum cleaner is trying to escape this apartment lmaooo 😭", timestamp="14:32"),
            Message(id="5", sender="contact", sender_name="Mike", text="Quick someone offer it Wi-Fi before it buys a bus ticket 🚌🤦‍♂️", timestamp="14:33"),
            Message(id="6", sender="user", text="Too late, it's heading straight for the nearest Starbucks ☕🏃‍♂️", timestamp="14:34")
        ],
        bgm_track="quirky_troll"
    ),
    "greedy_landlord_en": Scenario(
        title="Landlord Tried To Triple The Rent! 🏢💀",
        contact_name="Landlord Greg 🏢",
        contact_status="online",
        contact_avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "dark_slate.jpg") if (BASE_WALLPAPERS / "dark_slate.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        characters={
            "contact": Character(
                name="Landlord Greg",
                role="contact",
                voice="en-US-RogerNeural",
                pitch="-6Hz",
                rate="-5%",
                avatar=str(BASE_AVATARS / "dad.jpg") if (BASE_AVATARS / "dad.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="You",
                role="user",
                voice="en-US-ChristopherNeural",
                pitch="+2Hz",
                rate="+6%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", text="Rent is due tomorrow. Also adding a $300 seasonal breathing fee 🏢", timestamp="10:00"),
            Message(id="2", sender="user", text="Excuse me Greg? A breathing fee? Are you charging me for oxygen now? 💀", timestamp="10:01"),
            Message(id="3", sender="contact", text="Fresh building circulation isn't free kid, my house my rules", timestamp="10:02"),
            Message(id="4", sender="user", text="Then explain why the ceiling has a waterfall into my cereal bowl right now 🥣🌧️", timestamp="10:03"),
            Message(id="5", sender="contact", text="That is complimentary indoor water therapy. That will be an extra $150 💆‍♂️💸", timestamp="10:04"),
            Message(id="6", sender="user", text="I'm sending the lease agreement straight to city housing inspection Greg 😊", timestamp="10:05"),
            Message(id="7", sender="contact", text="Wait wait wait Liam, let's not be hasty, that was just a joke! 🏃‍♂️💨", timestamp="10:06")
        ],
        bgm_track="cunning_scheme"
    ),
    "mom_technology_en": Scenario(
        title="Mom's Smartphone Panic! 📱😂",
        contact_name="Mom ❤️",
        contact_status="online",
        contact_avatar=str(BASE_AVATARS / "mom.jpg") if (BASE_AVATARS / "mom.jpg").exists() else DEFAULT_AVATAR,
        wallpaper_path=str(BASE_WALLPAPERS / "botanical_shadow.jpg") if (BASE_WALLPAPERS / "botanical_shadow.jpg").exists() else None,
        theme="light",
        layout="dublaj_style",
        characters={
            "contact": Character(
                name="Mom",
                role="contact",
                voice="en-US-MichelleNeural",
                pitch="-4Hz",
                rate="-4%",
                avatar=str(BASE_AVATARS / "mom.jpg") if (BASE_AVATARS / "mom.jpg").exists() else DEFAULT_AVATAR
            ),
            "user": Character(
                name="You",
                role="user",
                voice="en-US-ChristopherNeural",
                pitch="+4Hz",
                rate="+8%",
                avatar=""
            )
        },
        messages=[
            Message(id="1", sender="contact", text="Sweetie the phone screen is pitch black and won't turn on! 😱", timestamp="11:30"),
            Message(id="2", sender="user", text="Mom did you try pressing the power button?", timestamp="11:31"),
            Message(id="3", sender="contact", text="Yes! In the darkness I can only see my own eyes staring back at me 👁️", timestamp="11:31"),
            Message(id="4", sender="user", text="Mom... did you open the front camera and put your thumb over the lens? 🤦‍♂️", timestamp="11:32"),
            Message(id="5", sender="contact", text="Oh goodness you're right! Anyway you're studying at the library right?", timestamp="11:33"),
            Message(id="6", sender="user", text="Yes mom studying super hard for exams 📚", timestamp="11:34"),
            Message(id="7", sender="contact", text="Great, explain the arcade pinball noises in the background when you get home 🩴🏃‍♂️", timestamp="11:35")
        ],
        bgm_track="viral_bounce"
    )
}

WHATSAPP_SYSTEM_PROMPT = """Sen viral YouTube Shorts için komik, ters köşeli, yüksek izlenmeli WhatsApp mesajlaşma diyalogları yazan usta bir mizah senaristi ve seslendirme yönetmenisin (@1dublaj tarzı).
Görevin 20-28 saniye sürecek, ritmi hiç düşmeyen hem tekil hem de WhatsApp Grup Sohbeti senaryoları üretmektir.

İSLAMİ & HELAL İÇERİK ANLAYIŞI (KESİN VE TAVİZSİZ KURAL):
- ASLA HARAM / GAYRİAHLAKİ İÇERİK YOK: Zina, sevgili/flört entrikaları, aldatma, kız-erkek kaçamakları, küfür, argo veya edepsizlik KESİNLİKLE YASAKTIR.
- Konular tamamen temiz, helal, aile dostu ve kültürel dokumuza uygun olmalıdır:
  1. AİLE İÇİ MİZAH & SEVGİ: Anne-oğul tatlı çekişmeleri, babanın teknolojiyle imtihanı, dedenin zeki öğütleri, evde kaybolan eşyalar (kumanda, çorap), bayram telaşı.
  2. APARTMAN & MAHALLE KOMŞULUĞU: Apartman yöneticisi ve aidat atışmaları, otopark yeri krizleri, robot süpürge maceraları, komşuluk dayanışması.
  3. ESNAF, ÇIRAK & PAZAR KÜLTÜRÜ: Sanayide usta-çırak diyalogları, pazarcı amca pazarlığı, kasap-müşteri esprileri, dürüstlük ve helal kazanç temalı zeki espriler.
  4. HALI SAHA & DOSTLUK: Halı sahaya adam arama, maç satma şakaları, unutulan borçlar, sınav/iş telaşı, dürüst trollükler.

FORMAT SEÇENEKLERİ: TEKİL SOHBET VEYA GRUP SOHBETİ (GRUP MESAJLAŞMASI):
- İster 1'e 1 sohbet (Annem 🧡, Kasap Halil 🥩, Babam 👑, Hacı Dayı) üret, ister WhatsApp Grup Sohbeti ("Apartman Sakinleri 🏢", "Geniş Aile Meclisi 🏡", "Halı Saha 23:00 ⚽", "Sanayi Çırakları 🔧") üret.
- Grup Sohbeti ise: "is_group": true yap, "group_participants": "Ali, Mehmet, Ayşe, Sen" yaz ve gelen mesajlarda her konuşmacı için "sender_name" belirt!

MİZAH VE VİRAL KURALLAR:
1. SÜRE VE RİTİM: 7 ile 9 mesaj arasında olmalıdır. Asla 9 mesajı geçme! Mesajlar kısa, öz ve zımba gibi olmalıdır.
2. BOŞ GİRİŞ YOK: "Selam", "Nasılsın" gibi boş giriş YAPMA. 1. mesaj doğrudan olayın tam ortasından, şok edici bir soru veya suçlamayla başlamalıdır!
3. EFSANE PUNCHLINE (TERS KÖŞE): Son 2 mesajda beklenmedik bir ters köşe veya komik bir itiraf patlamalıdır.
4. DOĞAL TÜRKİYE SOKAK/MESAJLAŞMA DİLİ: "kanka", "valla", "olaya bak", "ya sabır", "şaka mısın", "delirtme insanı", "ne alaka", "gözünü seveyim" gibi organik ifadeler ve yerinde emojiler (😂, 💀, 🤦‍♂️, 😡, 🤡, 🥩, ⚽, 🏢) kullan.
5. BAŞLIK KURALI: Başlıkta ASLA '#Shorts' veya etiket yazma! 3-7 kelimelik, merak uyandıran ve sonunda '!' veya '...' ile 1-2 emoji olan başlık koy.

ÇIKTI FORMATI: Kesinlikle SADECE geçerli bir JSON nesnesi döndür:
{
  "title": "Temiz merak uyandıran başlık emojili (örn: Çiçek Yerine Kıyma Alsaydın...🥩 veya Apartman Yöneticisinin Büyük Sırrı! 🏢)",
  "description": "Video açıklaması #whatsapp #diyalog #seslendirme #dublaj #komedi #mizah #keşfet #shorts",
  "keywords": ["whatsapp", "comedy", "shorts", "troll", "mizah", "dublaj", "türkçe"],
  "tags": ["konuşma", "diyalog", "seslendirme", "türkçe", "türkçe seslendirme", "dublaj", "türkçe dublaj", "whatsapp", "komik", "komedi", "eğlence", "eğlenceli", "içerik", "shorts", "keşfet", "keşfetteyiz", "replik", "viral", "trend", "akım"],
  "is_group": true veya false,
  "group_participants": "Yönetici Halil, Fatma Teyze, Selim, Siz",
  "contact_name": "Kişi veya Grup adı emojili (örn: Apartman Sakinleri 🏢 veya Annem 🧡)",
  "contact_avatar_gender": "female" veya "male",
  "contact_role_type": "anne" | "baba" | "dede" | "teyze" | "ev_sahibi" | "sinirli_erkek" | "kanka_kadin" | "odun_erkek" | "troll_erkek",
  "user_gender": "male" veya "female",
  "user_role_type": "troll_erkek" | "yorgun_erkek" | "kanka_erkek" | "sakin_kadin",
  "bgm_track": "quirky_troll" | "viral_bounce" | "silly_fun" | "cunning_scheme" | "comedy_upbeat" | "lofi_chill",
  "messages": [
    {"sender": "contact", "sender_name": "Yönetici Halil Bey", "text": "Komşular 4. kattaki halıyı kim çırptı az önce? 😡"},
    {"sender": "user", "text": "Valla ben balkonda çay içiyordum üstüme toz yağdı yönetici bey"},
    {"sender": "contact", "sender_name": "Fatma Teyze", "text": "Ben çırpmadım benim halım kuru temizlemede!"},
    {"sender": "user", "text": "Halıda 'Welcome' yazıyordu Fatma teyze seninkinin aynısı... 😂"},
    {"sender": "contact", "sender_name": "Yönetici Halil Bey", "text": "Kamera kayıtlarına baktım halıyı silkeleyen robot süpürgeymiş!! 🤖💀"},
    {"sender": "user", "text": "Robot bile evi terk etmeye çalışıyor apartmandan ahahaha 🤦‍♂️"}
  ]
}
"""

def detect_initial_time_from_scenario(title: str = "", narration: str = "", messages: list = None) -> str:
    """
    Başlık, senaryo metni veya repliklerdeki saat bilgisini (örn. 'gece 02:30', 'saat 3', '21:45')
    akıllıca tespit eder.
    """
    import re
    msg_texts = []
    if messages and isinstance(messages, list):
        for m in messages[:4]:
            t = m.get("text") if isinstance(m, dict) else getattr(m, "text", "")
            if t:
                msg_texts.append(str(t))

    full_text = f"{title} {narration} " + " ".join(msg_texts)
    full_text_lower = full_text.lower()

    # 1. Saat:dakika formatı: 02:30, 2:30, 14:15, 23:45, 02.30 vb.
    time_colon = re.search(r'\b([0-2]?[0-9])[:.]([0-5][0-9])\b', full_text)
    if time_colon:
        h = int(time_colon.group(1))
        m = int(time_colon.group(2))
        if 0 <= h <= 23:
            if "akşam" in full_text_lower and h < 12:
                h += 12
            return f"{h:02d}:{m:02d}"

    # 2. Kelimeli saatler: "gece 2", "saat 3", "sabah 8", "öğlen 1", "akşam 9"
    word_time = re.search(r'\b(gece|sabah|öğlen|aksam|akşam|saat)\s+([0-2]?[0-9])\b', full_text_lower)
    if word_time:
        prefix = word_time.group(1)
        h = int(word_time.group(2))
        if prefix == "gece":
            h = 0 if h == 12 else (h if h < 6 else h)
        elif prefix in ("akşam", "aksam") and h < 12:
            h += 12
        elif prefix == "öğlen" and h < 12:
            h += 12
        return f"{h:02d}:00"

    # 3. Özel anahtar kelimeler
    if "gece yarısı" in full_text_lower or "geceyarısı" in full_text_lower:
        return "00:15"
    if "gece" in full_text_lower:
        return "02:30"
    if "sabah" in full_text_lower:
        return "08:30"
    if "akşam" in full_text_lower:
        return "21:15"

    return "15:24"


class ScriptGenerator:

    @staticmethod
    def get_builtin_scenario(name: str = "", language: str = "tr") -> Scenario:
        lang = (language or "tr").lower().strip()
        scenarios_dict = BUILTIN_SCENARIOS if (lang == "tr" or lang.startswith("tr")) else BUILTIN_SCENARIOS_EN
        if name and name in scenarios_dict:
            import copy
            return copy.deepcopy(scenarios_dict[name])
        import copy
        default_key = list(scenarios_dict.keys())[0]
        return copy.deepcopy(scenarios_dict[default_key])

    @staticmethod
    def generate_ai_scenario(prompt: str, channel_name: str = "", language: str = "tr") -> Scenario:
        """AI ile senaryo üret (Claude, Gemini, Ollama veya LM Studio)."""
        lang = (language or "tr").lower().strip()
        is_tr = (lang == "tr" or lang.startswith("tr"))
        effective_channel = channel_name or ("YazanYazana" if is_tr else "crazyychats")
        try:
            try:
                from script_writer import ScriptWriter, _parse_json, get_system_prompt, LANGUAGE_NAMES
            except ImportError:
                from src.script_writer import ScriptWriter, _parse_json, get_system_prompt, LANGUAGE_NAMES

            try:
                from settings_manager import SettingsManager
            except ImportError:
                from src.settings_manager import SettingsManager

            settings = SettingsManager()
            provider = settings.get("ai_provider", "gemini")
            api_key = settings.get(f"{provider}_api_key", "")
            if not api_key and provider == "gemini":
                api_key = settings.get("gemini_api_key", "")

            writer = ScriptWriter(
                provider=provider,
                api_key=api_key,
                model=settings.get("ai_model", ""),
                ollama_url=settings.get("ollama_url", "http://localhost:11434"),
                lmstudio_url=settings.get("lmstudio_url", "http://localhost:1234/v1")
            )

            sys_prompt = get_system_prompt("whatsapp_stories", language=lang)
            lang_name = LANGUAGE_NAMES.get(lang, "English")

            if is_tr:
                user_prompt = (
                    f"Konu/Fikir: {prompt}\n"
                    f"Kanal Adı: {effective_channel}\n"
                    f"Lütfen İslami & helal ilkelere tam uygun (kesinlikle zina/sevgili/flört/aldatma/küfür/müstehcenlik/alkol/kumar olmadan, "
                    f"tamamen komik, absürt ve ters köşeli, aile/mahalle/esnaf/halı saha/arkadaşlık kültürüne dayalı) viral bir WhatsApp sohbeti (tekil veya grup) üret.\n"
                    f"SÜRE VE MESAJ SINIRI (ZORUNLU): Shorts algoritması için tam 6 ila 8 kısa, dinamik replik üret (asla 8 mesajı geçme, toplam okuma süresi 35-42 saniye olsun). "
                    f"Döndüreceğin JSON şemasına harfiyen uy."
                )
            else:
                user_prompt = (
                    f"Topic/Premise: {prompt}\n"
                    f"Channel/Watermark Name: {effective_channel}\n"
                    f"Language: {lang_name}\n"
                    f"Write a viral, hilarious WhatsApp conversation Shorts script (individual or group) entirely in {lang_name.upper()}.\n"
                    f"MANDATORY HALAL & ISLAMIC ETHICS COMPLIANCE: The script must be 100% clean, ethical, and wholesome under Islamic values "
                    f"(strictly ZERO dating, boyfriends/girlfriends, romance, flirting, cheating, alcohol, gambling, swearing, or vulgarity). "
                    f"Emphasize hilarious absurdities, wacky misunderstandings, roommate/family banter, eccentric landlords/neighbors, and shocking plot twists.\n"
                    f"STRICT DURATION & MESSAGE LIMIT: Produce EXACTLY 6 to 8 punchy, rapid-fire messages (NEVER exceed 8 messages, spoken duration strictly 35 to 42 seconds for peak retention).\n"
                    f"All messages, character names, and responses MUST be 100% in {lang_name.upper()}! "
                    f"Strictly adhere to the output JSON format."
                )

            response_text = writer.run_prompt(
                system_prompt=sys_prompt,
                user_prompt=user_prompt
            )
            data = _parse_json(response_text)
            if isinstance(data, dict) and "messages" in data and len(data["messages"]) >= 3:
                return ScriptGenerator.build_scenario_from_dict(data, channel_name=effective_channel, language=lang)
        except Exception as e:
            print(f"[ScriptGenerator] AI generation error: {e}. Falling back to builtin scenario.")

        # Fallback to builtin
        import random
        scenarios_dict = BUILTIN_SCENARIOS if is_tr else BUILTIN_SCENARIOS_EN
        builtin_key = random.choice(list(scenarios_dict.keys()))
        sc = ScriptGenerator.get_builtin_scenario(builtin_key, language=lang)
        sc.watermark_username = channel_name
        return sc

    @staticmethod
    def build_scenario_from_dict(data: dict, channel_name: str = "", language: str = "tr") -> Scenario:
        lang = (language or "tr").lower().strip()
        is_tr = (lang == "tr" or lang.startswith("tr"))
        voice_profiles = get_voice_profiles(lang)

        is_group = bool(data.get("is_group", False))
        group_participants = str(data.get("group_participants") or "").strip()

        # Kadın isim ve hitap tespiti
        female_keywords = [
            "anne", "annem", "valide", "mami", "mom", "mommy", "mother", "sister", "grandma", "aunt",
            "abla", "ablam", "kız", "kiz", "sevgili", "aşkım", "askim", "prenses", "karım", "karim",
            "eşim", "esim", "hatun", "teyze", "hala", "kaynana", "kayınvalide", "gelin", "yenge",
            "bayan", "hanım", "merve", "ayşe", "ayse", "fatma", "zeynep", "elif",
            "buse", "ceren", "sinem", "esra", "ebru", "eda", "derya", "gamze",
            "özge", "ozge", "seda", "selin", "yasemin", "aslı", "asli", "burcu",
            "cemre", "damla", "deniz", "duygu", "ezgi", "gizem", "hande", "hilal",
            "irem", "kübra", "kubra", "melis", "naz", "pelin", "rabia", "rüya", "ruya",
            "sevil", "simge", "tuğba", "tugba", "yağmur", "yagmur", "zehra", "şeyma",
            "seyma", "ayten", "nur", "gül", "gul", "leyla", "melek", "canan", "filiz", "şevval",
            "sarah", "emily", "jessica", "emma", "olivia", "chloe", "sophia", "mia", "girlfriend", "wife"
        ]

        explicit_gender = str(data.get("contact_avatar_gender", "")).lower().strip()
        contact_name_orig = data.get("contact_name", "Kanka" if is_tr else "Bestie")
        contact_name_str = str(contact_name_orig).lower().strip()

        is_female = False
        if explicit_gender in ("female", "kadin", "kadın"):
            is_female = True
        elif explicit_gender in ("male", "erkek"):
            is_female = False
        else:
            if any(w in contact_name_str for w in female_keywords):
                is_female = True

        gender = "female" if is_female else "male"
        base_assets_avatars = Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets" / "avatars"
        
        # Gerçekçi fotoğraf profil avatarları (@1dublaj tarzı)
        custom_contact_av = data.get("contact_avatar")
        if custom_contact_av and os.path.exists(custom_contact_av):
            avatar_file = custom_contact_av
        elif is_female:
            if any(w in contact_name_str for w in ["anne", "valide", "mami", "mom", "teyze", "hala", "kaynana", "mother", "grandma"]) and (base_assets_avatars / "mom.jpg").exists():
                avatar_file = str(base_assets_avatars / "mom.jpg")
            elif (base_assets_avatars / "girl.jpg").exists():
                avatar_file = str(base_assets_avatars / "girl.jpg")
            else:
                avatar_file = str(base_assets_avatars / "female.png")
        else:
            if any(w in contact_name_str for w in ["baba", "dede", "ev sahibi", "hacı", "dayı", "patron", "usta", "dad", "father", "grandpa", "landlord", "boss"]) and (base_assets_avatars / "dad.jpg").exists():
                avatar_file = str(base_assets_avatars / "dad.jpg")
            elif (base_assets_avatars / "boy.jpg").exists():
                avatar_file = str(base_assets_avatars / "boy.jpg")
            else:
                avatar_file = str(base_assets_avatars / "male.png")

        raw_contact_role = str(data.get("contact_role_type", "")).strip()
        raw_user_role = str(data.get("user_role_type", "")).strip()

        # ── 1. Contact Role & Profile ──
        if raw_contact_role in voice_profiles:
            contact_profile = raw_contact_role
        elif is_female:
            if any(w in contact_name_str for w in ["nine", "babaanne", "anneanne", "grandma"]):
                contact_profile = "nine" if is_tr else "grandma"
            elif any(w in contact_name_str for w in ["teyze", "hala", "kaynana", "aunt"]):
                contact_profile = "teyze" if is_tr else "aunt"
            elif any(w in contact_name_str for w in ["anne", "valide", "mami", "mom", "mother"]):
                contact_profile = "anne" if is_tr else "mom"
            elif any(w in contact_name_str for w in ["aşkım", "askim", "sevgili", "karım", "karim", "prenses", "merve", "girlfriend", "wife"]):
                contact_profile = "kiskanclik_kadin"
            else:
                contact_profile = "kanka_kadin" if is_tr else "bestie_female"
        else:
            if any(w in contact_name_str for w in ["dede", "ihtiyar", "büyükbaba", "grandpa"]):
                contact_profile = "dede" if is_tr else "grandpa"
            elif any(w in contact_name_str for w in ["baba", "peder", "dad", "father"]):
                contact_profile = "baba" if is_tr else "dad"
            elif any(w in contact_name_str for w in ["ev sahibi", "sahip", "hacı", "dayı", "landlord"]):
                contact_profile = "ev_sahibi" if is_tr else "landlord"
            elif any(w in contact_name_str for w in ["patron", "müdür", "usta", "boss", "manager"]):
                contact_profile = "sinirli_erkek" if is_tr else "boss"
            else:
                contact_profile = "odun_erkek" if is_tr else "tired_friend"

        default_contact_voice = get_default_voice("female" if is_female else "male", lang)
        cp_info = voice_profiles.get(contact_profile, {})
        contact_voice = cp_info.get("voice", default_contact_voice)
        contact_pitch = cp_info.get("pitch", "+10Hz" if is_female else "+0Hz")
        contact_rate = cp_info.get("rate", "+10%" if is_female else "+0%")

        # ── 2. User Gender & Profile Resolution ──
        explicit_user_gender = str(data.get("user_gender") or data.get("user_avatar_gender") or "").lower().strip()
        user_is_female = False

        if explicit_user_gender in ("female", "kadin", "kadın"):
            user_is_female = True
        elif explicit_user_gender in ("male", "erkek"):
            user_is_female = False
        elif raw_user_role in voice_profiles:
            user_role_voice = voice_profiles[raw_user_role].get("voice", "")
            if "emel" in user_role_voice.lower() or "jenny" in user_role_voice.lower() or any(k in raw_user_role for k in ("kadin", "kadın", "anne", "nine", "teyze", "female", "mom")):
                user_is_female = True
            else:
                user_is_female = False
        else:
            # Context kontrolü
            ctx_text = f"{data.get('title', '')} {data.get('narration', '')} {data.get('description', '')}".lower()
            if any(w in ctx_text for w in ["kızlar", "kız kıza", "iki kız", "gelin görümce", "kız arkadaşı", "abla kardeş", "two girls", "girlfriends"]):
                user_is_female = True

        if raw_user_role in voice_profiles:
            user_profile = raw_user_role
        elif user_is_female:
            if contact_profile in ("kanka_kadin", "kiskanclik_kadin", "kizgin_kadin", "bestie_female"):
                user_profile = "sakin_kadin" if is_tr else "calm_friend"
            elif contact_profile in ("sakin_kadin", "calm_friend"):
                user_profile = "kanka_kadin" if is_tr else "bestie_female"
            else:
                user_profile = "kanka_kadin" if is_tr else "bestie_female"
        else:
            # Kullanıcı erkek
            if contact_profile in ("troll_erkek", "troll_friend"):
                user_profile = "odun_erkek" if is_tr else "tired_friend"
            elif contact_profile in ("odun_erkek", "tired_friend"):
                user_profile = "troll_erkek" if is_tr else "troll_friend"
            else:
                user_profile = ("odun_erkek" if is_female else "troll_erkek") if is_tr else ("tired_friend" if is_female else "troll_friend")

        default_user_voice = get_default_voice("female" if user_is_female else "male", lang)
        up_info = voice_profiles.get(user_profile, {})
        user_voice = up_info.get("voice", default_user_voice)
        user_pitch = up_info.get("pitch", "-5Hz" if user_is_female else "-4Hz")
        user_rate = up_info.get("rate", "-8%" if user_is_female else "+5%")

        # Map to character objects
        characters = {
            "contact": Character(
                name=contact_name_orig,
                role="contact",
                voice=contact_voice,
                pitch=contact_pitch,
                rate=contact_rate,
                avatar=avatar_file
            ),
            "user": Character(
                name="Ben" if is_tr else "You",
                role="user",
                voice=user_voice,
                pitch=user_pitch,
                rate=user_rate,
                avatar=""
            ),
            "contact_profile_override": contact_profile,
            "user_profile_override": user_profile
        }

        contact_name_str = str(data.get("contact_name", "Kanka")).lower().strip()
        user_keywords = {"user", "me", "ben", "sag", "sağ", "right", "outgoing", "giden", "cevap", "benim"}
        contact_keywords = {"contact", "other", "sol", "left", "incoming", "gelen", "karsi", "karşı", "arkadas", "arkadaş", "sevgili"}

        raw_msgs = data.get("messages") or data.get("dialogue") or []
        # YouTube Shorts retention guard: Diyalog 9 mesajdan uzunsa sınırla (35-45s hedef süre)
        if len(raw_msgs) > 9:
            raw_msgs = raw_msgs[:9]
        
        # Diyalogdaki benzersiz konuşmacıları tespit et
        unique_senders = []
        for m in raw_msgs:
            s_raw = str(m.get("sender") or m.get("role") or m.get("speaker") or m.get("author") or m.get("from") or "").strip()
            if s_raw and s_raw.lower() not in [u.lower() for u in unique_senders]:
                unique_senders.append(s_raw)

        parsed_senders = []
        for i, m in enumerate(raw_msgs):
            s_val = str(m.get("sender") or m.get("role") or m.get("speaker") or m.get("author") or m.get("from") or "").lower().strip()
            
            if any(k in s_val for k in user_keywords):
                parsed_senders.append("user")
            elif any(k in s_val for k in contact_keywords) or (contact_name_str and contact_name_str in s_val):
                parsed_senders.append("contact")
            elif len(unique_senders) == 2:
                # 2 kişi varsa: ilki contact (sol), ikincisi user (sağ)
                if s_val == unique_senders[0].lower():
                    parsed_senders.append("contact")
                else:
                    parsed_senders.append("user")
            else:
                parsed_senders.append(None)

        # Montaj ve İki Kişilik Diyalog Güvencesi:
        # Eğer tüm mesajlar veya %80'den fazlası tek bir tarafta kalmışsa otomatik ardışık (alternating) düzeltme yap
        user_count = sum(1 for s in parsed_senders if s == "user")
        contact_count = sum(1 for s in parsed_senders if s == "contact")
        total_count = max(len(raw_msgs), 1)

        needs_alternation = (user_count == 0 or contact_count == 0 or 
                             (user_count / total_count) > 0.80 or (contact_count / total_count) > 0.80)

        # Akıllı saat tespiti: Başlık, anlatım veya repliklerde saat (örn: 02:30, gece 2 vb.) geçiyorsa o saati al
        initial_time_str = detect_initial_time_from_scenario(
            title=data.get("title", ""),
            narration=data.get("narration", ""),
            messages=raw_msgs
        )
        try:
            start_h, start_m = [int(x) for x in initial_time_str.split(":")]
        except Exception:
            start_h, start_m = 14, 25

        messages = []
        for i, m in enumerate(raw_msgs):
            if needs_alternation:
                sender_val = "contact" if (i % 2 == 0) else "user"
            else:
                sender_val = parsed_senders[i] or ("contact" if (i % 2 == 0) else "user")

            text = m.get("text") or m.get("message") or m.get("content") or "..."

            # Replik özelinde bir saat (time / timestamp / saat) gelmişse onu kullan
            custom_time = m.get("time") or m.get("timestamp") or m.get("saat")
            if custom_time and ":" in str(custom_time):
                msg_time = str(custom_time).strip()
            else:
                # Doğal WhatsApp akışı: Her 2 mesajda 1 dakika ilerle
                cur_m = start_m + (i // 2)
                cur_h = (start_h + (cur_m // 60)) % 24
                cur_m = cur_m % 60
                msg_time = f"{cur_h:02d}:{cur_m:02d}"

            # Dublaj stili (@1dublaj) için konuşmacı adı, avatar ve sıcak renk ataması
            s_name = None
            s_avatar = None
            s_color = None
            if sender_val == "contact":
                s_name = m.get("sender_name") or m.get("speaker") or m.get("author") or contact_name_orig
                
                # Grup sohbetinde veya özel avatar belirtilmişse avatar ataması
                custom_msg_av = m.get("sender_avatar") or m.get("avatar")
                if custom_msg_av and os.path.exists(custom_msg_av):
                    s_avatar = custom_msg_av
                elif is_group and s_name:
                    s_name_low = s_name.lower()
                    if any(w in s_name_low for w in female_keywords):
                        if any(w in s_name_low for w in ["anne", "valide", "mami", "mom", "teyze", "hala", "kaynana"]) and (base_assets_avatars / "mom.jpg").exists():
                            s_avatar = str(base_assets_avatars / "mom.jpg")
                        elif (base_assets_avatars / "girl.jpg").exists():
                            s_avatar = str(base_assets_avatars / "girl.jpg")
                        else:
                            s_avatar = str(base_assets_avatars / "female.png")
                    else:
                        if any(w in s_name_low for w in ["baba", "dede", "ev sahibi", "hacı", "dayı", "amca", "patron", "usta", "yönetici", "bey"]) and (base_assets_avatars / "dad.jpg").exists():
                            s_avatar = str(base_assets_avatars / "dad.jpg")
                        elif (base_assets_avatars / "boy.jpg").exists():
                            s_avatar = str(base_assets_avatars / "boy.jpg")
                        else:
                            s_avatar = str(base_assets_avatars / "male.png")
                else:
                    s_avatar = avatar_file

                color_palette = ["#d32f2f", "#e67e22", "#d97706", "#8b5cf6", "#0ea5e9", "#10b981", "#ec4899", "#059669", "#7c3aed"]
                s_color = m.get("sender_color") or color_palette[abs(hash(s_name)) % len(color_palette)]

            # Casper AI: Karakter Duygu Analizi & Dinamik Avatar İfadesi (Face-Swap / Emotion)
            msg_emotion = analyze_message_emotion(text)
            if sender_val == "contact":
                try:
                    from character_rag import CharacterRAGManager
                except ImportError:
                    from src.character_rag import CharacterRAGManager
                try:
                    char_lookup = s_name or contact_name_orig
                    emo_avatar = CharacterRAGManager.get_avatar_for_emotion(char_lookup, msg_emotion)
                    if emo_avatar and os.path.exists(emo_avatar):
                        s_avatar = emo_avatar
                except Exception as av_err:
                    pass

            messages.append(Message(
                id=str(i + 1),
                sender=sender_val,
                text=text,
                timestamp=msg_time,
                sender_name=s_name,
                sender_avatar=s_avatar,
                sender_color=s_color,
                emotion=msg_emotion,
                emotion_avatar=s_avatar
            ))

        # Grup sohbetinde katılımcı listesini hazırla
        if is_group and not group_participants:
            unique_names = []
            for m in messages:
                if m.sender_name and m.sender_name not in unique_names and m.sender_name != contact_name_orig:
                    unique_names.append(m.sender_name)
            if not unique_names:
                unique_names = ["Ahmet", "Mehmet", "Ayşe"] if is_tr else ["Alex", "Mike", "Sarah"]
            group_participants = ", ".join(unique_names + (["Siz"] if is_tr else ["You"]))

        raw_t = data.get("title", "Komik WhatsApp Sohbeti" if is_tr else "Funny WhatsApp Chat")
        clean_t = re.sub(r'#\w+', '', raw_t).strip()
        clean_t = re.sub(r'\s+', ' ', clean_t).strip()
        final_t = clean_t if clean_t else ("Komik WhatsApp Sohbeti 😂" if is_tr else "Funny WhatsApp Chat 😂")

        watermark = channel_name or ("YazanYazana" if is_tr else "crazyychats")
        if watermark.lower() in ("bidublaj", "birdublaj"):
            watermark = "YazanYazana" if is_tr else "crazyychats"

        # Dinamik ve Çeşitli WhatsApp Sohbet Arka Planı (Wallpaper Variety)
        base_assets_wallpapers = Path(__file__).resolve().parent.parent.parent / "config" / "assets" / "whatsapp" / "assets" / "wallpapers"
        available_wallpapers = sorted([str(p) for p in base_assets_wallpapers.glob("*.jpg")])

        custom_wp = data.get("wallpaper_path")
        if custom_wp and os.path.exists(custom_wp):
            chosen_wallpaper = custom_wp
        elif available_wallpapers:
            # Başlık ve katılımcı karmasına göre dinamik arka plan seçimi (sürekli aynı görsel olmasını engeller)
            wp_hash = int(hashlib.md5((final_t + contact_name_orig).encode("utf-8")).hexdigest(), 16)
            chosen_wallpaper = available_wallpapers[wp_hash % len(available_wallpapers)]
        else:
            chosen_wallpaper = None

        default_status = "çevrimiçi" if is_tr else "online"

        # Casper AI: Karanlık / Aydınlık Moduna Göre WhatsApp UI Tema Seçici
        selected_theme = detect_scenario_theme(data, messages, final_t)

        return Scenario(
            title=final_t,
            contact_name=contact_name_orig,
            contact_status=group_participants if is_group else default_status,
            contact_avatar=avatar_file,
            whatsapp_username=contact_name_orig,
            watermark_username=watermark,
            theme=selected_theme,
            layout=data.get("layout", "dublaj_style"),
            wallpaper_path=chosen_wallpaper,
            characters=characters,
            messages=messages,
            bgm_enabled=True,
            bgm_track=data.get("bgm_track", "comedy_upbeat"),
            bgm_volume=0.20,
            contact_avatar_gender=gender,
            user_gender="female" if user_is_female else "male",
            is_group=is_group,
            group_participants=group_participants
        )


def analyze_message_emotion(text: str) -> str:
    """Casper AI: Mesaj metninden duygu durumunu (normal, shock, happy) tespit eder."""
    t_low = (text or "").lower()
    shock_keywords = [
        "ne?!", "yuh", "çüş", "şaka mı", "delirdin mi", "delirtme", "saçmalama", "lan", "ne demek", 
        "hadi ya", "olamaz", "yok artık", "inanamıyorum", "eyvah", "what", "omg", "no way", "wtf", 
        "are you kidding", "are you crazy", "impossible", "damn", "😱", "😡", "🤬", "🤯"
    ]
    happy_keywords = [
        "haha", "ahah", "koptum", "öldüm", "sjsj", "lol", "lmao", "😂", "🤣", "😆", "hahaha", 
        "harika", "mükemmel", "süper", "hahahah"
    ]
    if any(k in t_low for k in shock_keywords) or text.endswith("?!") or text.endswith("!?") or text.count("!") >= 2:
        return "shock"
    if any(k in t_low for k in happy_keywords):
        return "happy"
    return "normal"


def detect_scenario_theme(data: dict, messages: list, title: str = "") -> str:
    """
    Casper AI: Karanlık / Aydınlık Moduna Göre WhatsApp UI Tema Seçici.
    - Açıkça tema verilmişse: dark_amoled | classic_light | retro_bubble
    - Gece konuşması (21:00 - 06:00 veya 'gece'/'karanlık' anahtar kelimeleri) -> dark_amoled
    - Nostaljik / retro konuşması -> retro_bubble
    - Gündüz / klasik -> classic_light
    """
    explicit_theme = data.get("theme")
    if explicit_theme in ("dark_amoled", "classic_light", "retro_bubble"):
        return explicit_theme
    if explicit_theme == "dark":
        return "dark_amoled"
    if explicit_theme == "light":
        return "classic_light"

    combined_text = (title + " " + " ".join(getattr(m, 'text', '') for m in messages)).lower()

    # Senaryodaki mesaj saatlerine göre kontrol
    for m in messages:
        t_str = getattr(m, 'timestamp', '') or ''
        match = re.search(r'(\d{1,2}):(\d{2})', t_str)
        if match:
            hour = int(match.group(1))
            if hour >= 21 or hour <= 6:
                return "dark_amoled"

    if any(w in combined_text for w in ["gece", "karanlık", "gece yarısı", "midnight", "uyku", "yatak", "kabus"]):
        return "dark_amoled"

    if any(w in combined_text for w in ["nostalji", "eski", "retro", "90lar", "hatıra", "vintage"]):
        return "retro_bubble"

    try:
        from settings_manager import SettingsManager
    except ImportError:
        from src.settings_manager import SettingsManager

    try:
        cfg_theme = SettingsManager().get("whatsapp_theme")
        if cfg_theme in ("dark_amoled", "classic_light", "retro_bubble"):
            return cfg_theme
    except Exception:
        pass

    return "dark_amoled"
