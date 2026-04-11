"""Multilingual support for TaxiBek bot."""

LANGS = {
    "uz": "O'zbek",
    "uz_cyr": "Ўзбек",
    "kk": "Қазақ",
    "ru": "Русский",
}

_t = {
    # ── Language selection ─────────────────────────────────────────────────
    "lang_select": {
        "uz": "🌐 Tilni tanlang:",
        "uz_cyr": "🌐 Тилни танланг:",
        "kk": "🌐 Тілді таңдаңыз:",
        "ru": "🌐 Выберите язык:",
    },
    "lang_changed": {
        "uz": "✅ Til o'zgartirildi",
        "uz_cyr": "✅ Тил ўзгартирилди",
        "kk": "✅ Тіл өзгертілді",
        "ru": "✅ Язык изменён",
    },

    # ── /start & Registration ─────────────────────────────────────────────
    "welcome": {
        "uz": "🚕 <b>TaxiBek</b> ga xush kelibsiz!\n\nSiz kimsiz?",
        "uz_cyr": "🚕 <b>TaxiBek</b> га хуш келибсиз!\n\nСиз кимсиз?",
        "kk": "🚕 <b>TaxiBek</b> ге қош келдіңіз!\n\nСіз кімсіз?",
        "ru": "🚕 Добро пожаловать в <b>TaxiBek</b>!\n\nКто вы?",
    },
    "role_client": {
        "uz": "👤 Yo'lovchiman",
        "uz_cyr": "👤 Йўловчиман",
        "kk": "👤 Жолаушымын",
        "ru": "👤 Я пассажир",
    },
    "role_driver": {
        "uz": "🚗 Haydovchiman",
        "uz_cyr": "🚗 Ҳайдовчиман",
        "kk": "🚗 Жүргізушімін",
        "ru": "🚗 Я водитель",
    },
    "enter_name": {
        "uz": "📝 <b>Ismingizni</b> kiriting:",
        "uz_cyr": "📝 <b>Исмингизни</b> киритинг:",
        "kk": "📝 <b>Атыңызды</b> жазыңыз:",
        "ru": "📝 Введите <b>ваше имя</b>:",
    },
    "name_too_short": {
        "uz": "❌ Iltimos, to'liq ismingizni kiriting:",
        "uz_cyr": "❌ Илтимос, тўлиқ исмингизни киритинг:",
        "kk": "❌ Толық атыңызды жазыңыз:",
        "ru": "❌ Пожалуйста, введите полное имя:",
    },
    "thanks_name": {
        "uz": "👋 Rahmat, <b>{name}</b>!\n\n📞 Telefon raqamingizni yuboring:",
        "uz_cyr": "👋 Раҳмат, <b>{name}</b>!\n\n📞 Телефон рақамингизни юборинг:",
        "kk": "👋 Рахмет, <b>{name}</b>!\n\n📞 Телефон нөміріңізді жіберіңіз:",
        "ru": "👋 Спасибо, <b>{name}</b>!\n\n📞 Отправьте ваш номер телефона:",
    },
    "phone_accepted": {
        "uz": "✅ Telefon qabul qilindi.",
        "uz_cyr": "✅ Телефон қабул қилинди.",
        "kk": "✅ Телефон қабылданды.",
        "ru": "✅ Телефон принят.",
    },
    "phone_invalid": {
        "uz": "❌ Noto'g'ri format! Masalan: <code>+998901234567</code>",
        "uz_cyr": "❌ Нотўғри формат! Масалан: <code>+998901234567</code>",
        "kk": "❌ Қате формат! Мысалы: <code>+998901234567</code>",
        "ru": "❌ Неверный формат! Например: <code>+998901234567</code>",
    },
    "phone_btn": {
        "uz": "📞 Telefon raqamni yuborish",
        "uz_cyr": "📞 Телефон рақамни юбориш",
        "kk": "📞 Телефон нөмірін жіберу",
        "ru": "📞 Отправить номер телефона",
    },
    "select_region": {
        "uz": "📍 Viloyatingizni tanlang:",
        "uz_cyr": "📍 Вилоятингизни танланг:",
        "kk": "📍 Облысыңызды таңдаңыз:",
        "ru": "📍 Выберите область:",
    },
    "select_district": {
        "uz": "Tumaningizni tanlang:",
        "uz_cyr": "Туманингизни танланг:",
        "kk": "Ауданыңызды таңдаңыз:",
        "ru": "Выберите район:",
    },
    "select_route": {
        "uz": "🛣 Yo'nalishingizni tanlang:",
        "uz_cyr": "🛣 Йўналишингизни танланг:",
        "kk": "🛣 Бағытыңызды таңдаңыз:",
        "ru": "🛣 Выберите маршрут:",
    },
    "select_first_route": {
        "uz": "📍 Birinchi yo'nalishingizni tanlang.\n\nViloyatingizni tanlang:",
        "uz_cyr": "📍 Биринчи йўналишингизни танланг.\n\nВилоятингизни танланг:",
        "kk": "📍 Бірінші бағытыңызды таңдаңыз.\n\nОблысыңызды таңдаңыз:",
        "ru": "📍 Выберите первый маршрут.\n\nВыберите область:",
    },
    "no_routes": {
        "uz": "😔 Hozircha faol yo'nalishlar yo'q. Keyinroq urinib ko'ring.",
        "uz_cyr": "😔 Ҳозирча фаол йўналишлар йўқ. Кейинроқ уриниб кўринг.",
        "kk": "😔 Қазір белсенді бағыттар жоқ. Кейінірек көріңіз.",
        "ru": "😔 Пока нет активных маршрутов. Попробуйте позже.",
    },
    "reg_success": {
        "uz": "✅ <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n👤 {name}\n📞 {phone}\n🛣 Yo'nalish: <b>{route}</b>\n\nQo'shimcha yo'nalishlar qo'shish uchun\n\"🛣 Mening yo'nalishlarim\" tugmasini bosing.",
        "uz_cyr": "✅ <b>Рўйхатдан муваффақиятли ўтдингиз!</b>\n\n👤 {name}\n📞 {phone}\n🛣 Йўналиш: <b>{route}</b>",
        "kk": "✅ <b>Тіркеу сәтті аяқталды!</b>\n\n👤 {name}\n📞 {phone}\n🛣 Бағыт: <b>{route}</b>",
        "ru": "✅ <b>Регистрация успешна!</b>\n\n👤 {name}\n📞 {phone}\n🛣 Маршрут: <b>{route}</b>",
    },
    "cancelled": {
        "uz": "❌ Bekor qilindi.\n/start — qaytadan boshlash",
        "uz_cyr": "❌ Бекор қилинди.\n/start — қайтадан бошлаш",
        "kk": "❌ Бас тартылды.\n/start — қайта бастау",
        "ru": "❌ Отменено.\n/start — начать заново",
    },
    "blocked": {
        "uz": "🚫 Sizning akkauntingiz bloklangan.",
        "uz_cyr": "🚫 Сизнинг аккаунтингиз блокланган.",
        "kk": "🚫 Сіздің аккаунтыңыз бұғатталған.",
        "ru": "🚫 Ваш аккаунт заблокирован.",
    },
    "hello": {
        "uz": "👋 Salom, <b>{name}</b>!",
        "uz_cyr": "👋 Салом, <b>{name}</b>!",
        "kk": "👋 Сәлем, <b>{name}</b>!",
        "ru": "👋 Привет, <b>{name}</b>!",
    },
    "register_first": {
        "uz": "Avval /start orqali ro'yxatdan o'ting.",
        "uz_cyr": "Аввал /start орқали рўйхатдан ўтинг.",
        "kk": "Алдымен /start арқылы тіркеліңіз.",
        "ru": "Сначала зарегистрируйтесь через /start.",
    },
    "main_menu": {
        "uz": "Asosiy menyu:",
        "uz_cyr": "Асосий меню:",
        "kk": "Басты мәзір:",
        "ru": "Главное меню:",
    },

    # ── Menu buttons ──────────────────────────────────────────────────────
    "btn_taxi": {
        "uz": "🚕 Taxi chaqirish",
        "uz_cyr": "🚕 Такси чақириш",
        "kk": "🚕 Такси шақыру",
        "ru": "🚕 Вызвать такси",
    },
    "btn_my_routes": {
        "uz": "🛣 Mening yo'nalishlarim",
        "uz_cyr": "🛣 Менинг йўналишларим",
        "kk": "🛣 Менің бағыттарым",
        "ru": "🛣 Мои маршруты",
    },
    "btn_profile": {
        "uz": "👤 Profil",
        "uz_cyr": "👤 Профил",
        "kk": "👤 Профиль",
        "ru": "👤 Профиль",
    },
    "btn_help": {
        "uz": "ℹ️ Yordam",
        "uz_cyr": "ℹ️ Ёрдам",
        "kk": "ℹ️ Көмек",
        "ru": "ℹ️ Помощь",
    },
    "btn_reload": {
        "uz": "🔄 Qayta yuklash",
        "uz_cyr": "🔄 Қайта юклаш",
        "kk": "🔄 Жаңарту",
        "ru": "🔄 Обновить",
    },
    "btn_announce": {
        "uz": "🚐 Safar e'lon qilish",
        "uz_cyr": "🚐 Сафар эълон қилиш",
        "kk": "🚐 Сапар жариялау",
        "ru": "🚐 Объявить поездку",
    },
    "btn_active_trip": {
        "uz": "📋 Faol safar",
        "uz_cyr": "📋 Фаол сафар",
        "kk": "📋 Белсенді сапар",
        "ru": "📋 Активная поездка",
    },
    "btn_stats": {
        "uz": "📊 Statistika",
        "uz_cyr": "📊 Статистика",
        "kk": "📊 Статистика",
        "ru": "📊 Статистика",
    },
    "btn_back_client": {
        "uz": "◀️ Mijoz rejimiga qaytish",
        "uz_cyr": "◀️ Мижоз режимига қайтиш",
        "kk": "◀️ Жолаушы режиміне қайту",
        "ru": "◀️ Вернуться в режим клиента",
    },
    "btn_back": {
        "uz": "◀️ Orqaga",
        "uz_cyr": "◀️ Орқага",
        "kk": "◀️ Артқа",
        "ru": "◀️ Назад",
    },
    "btn_cancel": {
        "uz": "❌ Bekor qilish",
        "uz_cyr": "❌ Бекор қилиш",
        "kk": "❌ Бас тарту",
        "ru": "❌ Отмена",
    },

    # ── Taxi call ─────────────────────────────────────────────────────────
    "taxi_select_route": {
        "uz": "🚕 <b>Qaysi yo'nalishda ketasiz?</b>",
        "uz_cyr": "🚕 <b>Қайси йўналишда кетасиз?</b>",
        "kk": "🚕 <b>Қай бағытта кетесіз?</b>",
        "ru": "🚕 <b>По какому маршруту едете?</b>",
    },
    "taxi_select_dir": {
        "uz": "Qaysi yo'nalishda ketasiz?",
        "uz_cyr": "Қайси йўналишда кетасиз?",
        "kk": "Қай бағытта кетесіз?",
        "ru": "В каком направлении?",
    },
    "taxi_no_drivers": {
        "uz": "😔 Hozircha haydovchi kutmayapti.\n\n💡 <i>Yangilash tugmasini bosing.</i>",
        "uz_cyr": "😔 Ҳозирча ҳайдовчи кутмаяпти.\n\n💡 <i>Янгилаш тугмасини босинг.</i>",
        "kk": "😔 Қазір жүргізуші күтіп тұрған жоқ.\n\n💡 <i>Жаңарту батырмасын басыңыз.</i>",
        "ru": "😔 Пока нет водителей.\n\n💡 <i>Нажмите обновить.</i>",
    },
    "taxi_no_routes": {
        "uz": "🛣 <b>Yo'nalishlar yo'q</b>\n\nTaxi chaqirish uchun avval yo'nalish qo'shing.\n👉 \"🛣 Mening yo'nalishlarim\" tugmasini bosing.",
        "uz_cyr": "🛣 <b>Йўналишлар йўқ</b>\n\nТакси чақириш учун аввал йўналиш қўшинг.",
        "kk": "🛣 <b>Бағыттар жоқ</b>\n\nТакси шақыру үшін бағыт қосыңыз.",
        "ru": "🛣 <b>Маршрутов нет</b>\n\nДобавьте маршрут для вызова такси.",
    },
    "btn_refresh": {
        "uz": "🔄 Yangilash",
        "uz_cyr": "🔄 Янгилаш",
        "kk": "🔄 Жаңарту",
        "ru": "🔄 Обновить",
    },
    "btn_change_dir": {
        "uz": "↩️ Yo'nalish o'zgartirish",
        "uz_cyr": "↩️ Йўналиш ўзгартириш",
        "kk": "↩️ Бағытты өзгерту",
        "ru": "↩️ Сменить направление",
    },

    # ── Booking ───────────────────────────────────────────────────────────
    "book_comment_ask": {
        "uz": "💬 <b>Izoh qoldiring</b> (ixtiyoriy)\n\n<i>Masalan: \"2 ta sumka bor\"</i>\n\nIzoh kerak bo'lmasa — /skip",
        "uz_cyr": "💬 <b>Изоҳ қолдиринг</b> (ихтиёрий)\n\n<i>Масалан: \"2 та сумка бор\"</i>\n\nИзоҳ керак бўлмаса — /skip",
        "kk": "💬 <b>Ескертпе қалдырыңыз</b> (міндетті емес)\n\n<i>Мысалы: \"2 сөмке бар\"</i>\n\nҚажет болмаса — /skip",
        "ru": "💬 <b>Оставьте комментарий</b> (необязательно)\n\n<i>Например: \"2 сумки\"</i>\n\nНе нужен — /skip",
    },
    "book_success": {
        "uz": "✅ <b>Bron qilindi!</b>",
        "uz_cyr": "✅ <b>Брон қилинди!</b>",
        "kk": "✅ <b>Брондалды!</b>",
        "ru": "✅ <b>Забронировано!</b>",
    },
    "book_seats_full": {
        "uz": "🔥 <b>Joylar tugadi — tez yo'lga chiqadi!</b>",
        "uz_cyr": "🔥 <b>Жойлар тугади!</b>",
        "kk": "🔥 <b>Орындар бітті!</b>",
        "ru": "🔥 <b>Мест нет — скоро выезд!</b>",
    },
    "book_seats_left": {
        "uz": "⏳ Yana {n} joy qoldi",
        "uz_cyr": "⏳ Яна {n} жой қолди",
        "kk": "⏳ Тағы {n} орын қалды",
        "ru": "⏳ Осталось {n} мест",
    },
    "btn_edit_comment": {
        "uz": "✏️ Izoh",
        "uz_cyr": "✏️ Изоҳ",
        "kk": "✏️ Ескертпе",
        "ru": "✏️ Коммент.",
    },
    "btn_del_comment": {
        "uz": "🗑 Izohni o'chirish",
        "uz_cyr": "🗑 Изоҳни ўчириш",
        "kk": "🗑 Ескертпені жою",
        "ru": "🗑 Удалить коммент.",
    },
    "btn_cancel_booking": {
        "uz": "❌ Bronni bekor qilish",
        "uz_cyr": "❌ Бронни бекор қилиш",
        "kk": "❌ Брондау бас тарту",
        "ru": "❌ Отменить бронь",
    },
    "confirm_cancel": {
        "uz": "⚠️ <b>Rostdan bekor qilmoqchimisiz?</b>",
        "uz_cyr": "⚠️ <b>Ростдан бекор қилмоқчимисиз?</b>",
        "kk": "⚠️ <b>Шынымен бас тартқыңыз келе ме?</b>",
        "ru": "⚠️ <b>Вы уверены?</b>",
    },
    "btn_yes_cancel": {
        "uz": "✅ Ha, bekor qilish",
        "uz_cyr": "✅ Ҳа, бекор қилиш",
        "kk": "✅ Иә, бас тарту",
        "ru": "✅ Да, отменить",
    },
    "btn_no": {
        "uz": "❌ Yo'q",
        "uz_cyr": "❌ Йўқ",
        "kk": "❌ Жоқ",
        "ru": "❌ Нет",
    },
    "booking_cancelled": {
        "uz": "❌ <b>Bron bekor qilindi.</b>",
        "uz_cyr": "❌ <b>Брон бекор қилинди.</b>",
        "kk": "❌ <b>Брондау бас тартылды.</b>",
        "ru": "❌ <b>Бронь отменена.</b>",
    },
    "new_booking_driver": {
        "uz": "🆕 <b>Yangi bron!</b>",
        "uz_cyr": "🆕 <b>Янги брон!</b>",
        "kk": "🆕 <b>Жаңа брондау!</b>",
        "ru": "🆕 <b>Новая бронь!</b>",
    },

    # ── My Routes ─────────────────────────────────────────────────────────
    "my_routes_title": {
        "uz": "🛣 <b>Mening yo'nalishlarim</b>",
        "uz_cyr": "🛣 <b>Менинг йўналишларим</b>",
        "kk": "🛣 <b>Менің бағыттарым</b>",
        "ru": "🛣 <b>Мои маршруты</b>",
    },
    "no_fav_routes": {
        "uz": "Yo'nalishlar yo'q.",
        "uz_cyr": "Йўналишлар йўқ.",
        "kk": "Бағыттар жоқ.",
        "ru": "Маршрутов нет.",
    },
    "btn_add_route": {
        "uz": "➕ Yo'nalish qo'shish",
        "uz_cyr": "➕ Йўналиш қўшиш",
        "kk": "➕ Бағыт қосу",
        "ru": "➕ Добавить маршрут",
    },
    "route_added": {
        "uz": "✅ Qo'shildi!",
        "uz_cyr": "✅ Қўшилди!",
        "kk": "✅ Қосылды!",
        "ru": "✅ Добавлено!",
    },
    "route_removed": {
        "uz": "🗑 O'chirildi!",
        "uz_cyr": "🗑 Ўчирилди!",
        "kk": "🗑 Жойылды!",
        "ru": "🗑 Удалено!",
    },
    "route_exists": {
        "uz": "Bu yo'nalish allaqachon qo'shilgan!",
        "uz_cyr": "Бу йўналиш аллақачон қўшилган!",
        "kk": "Бұл бағыт қосылған!",
        "ru": "Этот маршрут уже добавлен!",
    },

    # ── Profile ───────────────────────────────────────────────────────────
    "profile_title": {
        "uz": "👤 <b>Profil</b>",
        "uz_cyr": "👤 <b>Профил</b>",
        "kk": "👤 <b>Профиль</b>",
        "ru": "👤 <b>Профиль</b>",
    },
    "btn_edit_name": {
        "uz": "✏️ Ism",
        "uz_cyr": "✏️ Исм",
        "kk": "✏️ Ат",
        "ru": "✏️ Имя",
    },
    "btn_edit_phone": {
        "uz": "📞 Telefon",
        "uz_cyr": "📞 Телефон",
        "kk": "📞 Телефон",
        "ru": "📞 Телефон",
    },
    "btn_edit_car": {
        "uz": "🚗 Mashina",
        "uz_cyr": "🚗 Машина",
        "kk": "🚗 Көлік",
        "ru": "🚗 Авто",
    },
    "btn_edit_color": {
        "uz": "🎨 Rang",
        "uz_cyr": "🎨 Ранг",
        "kk": "🎨 Түс",
        "ru": "🎨 Цвет",
    },
    "btn_edit_plate": {
        "uz": "🔢 Raqam",
        "uz_cyr": "🔢 Рақам",
        "kk": "🔢 Нөмір",
        "ru": "🔢 Номер",
    },
    "btn_change_lang": {
        "uz": "🌐 Til",
        "uz_cyr": "🌐 Тил",
        "kk": "🌐 Тіл",
        "ru": "🌐 Язык",
    },
    "name_changed": {
        "uz": "✅ Ism o'zgartirildi: <b>{name}</b>",
        "uz_cyr": "✅ Исм ўзгартирилди: <b>{name}</b>",
        "kk": "✅ Ат өзгертілді: <b>{name}</b>",
        "ru": "✅ Имя изменено: <b>{name}</b>",
    },
    "phone_changed": {
        "uz": "✅ Telefon o'zgartirildi: <b>{phone}</b>",
        "uz_cyr": "✅ Телефон ўзгартирилди: <b>{phone}</b>",
        "kk": "✅ Телефон өзгертілді: <b>{phone}</b>",
        "ru": "✅ Телефон изменён: <b>{phone}</b>",
    },
    "car_changed": {
        "uz": "✅ Mashina o'zgartirildi: <b>{val}</b>",
        "uz_cyr": "✅ Машина ўзгартирилди: <b>{val}</b>",
        "kk": "✅ Көлік өзгертілді: <b>{val}</b>",
        "ru": "✅ Авто изменено: <b>{val}</b>",
    },
    "edit_name_prompt": {
        "uz": "✏️ Hozirgi ism: <b>{val}</b>\n\nYangi ismingizni kiriting:",
        "uz_cyr": "✏️ Ҳозирги исм: <b>{val}</b>\n\nЯнги исмингизни киритинг:",
        "kk": "✏️ Қазіргі ат: <b>{val}</b>\n\nЖаңа атыңызды жазыңыз:",
        "ru": "✏️ Текущее имя: <b>{val}</b>\n\nВведите новое имя:",
    },
    "edit_phone_prompt": {
        "uz": "📞 Hozirgi telefon: <b>{val}</b>\n\nYangi raqamni yuboring:",
        "uz_cyr": "📞 Ҳозирги телефон: <b>{val}</b>\n\nЯнги рақамни юборинг:",
        "kk": "📞 Қазіргі телефон: <b>{val}</b>\n\nЖаңа нөмірді жіберіңіз:",
        "ru": "📞 Текущий телефон: <b>{val}</b>\n\nОтправьте новый номер:",
    },
    "edit_car_prompt": {
        "uz": "🚗 Hozirgi mashina: <b>{val}</b>\n\nYangi model kiriting:",
        "uz_cyr": "🚗 Ҳозирги машина: <b>{val}</b>\n\nЯнги модел киритинг:",
        "kk": "🚗 Қазіргі көлік: <b>{val}</b>\n\nЖаңа модель жазыңыз:",
        "ru": "🚗 Текущее авто: <b>{val}</b>\n\nВведите новую модель:",
    },
    "edit_color_prompt": {
        "uz": "🎨 Hozirgi rang: <b>{val}</b>\n\nYangi rang kiriting:",
        "uz_cyr": "🎨 Ҳозирги ранг: <b>{val}</b>\n\nЯнги ранг киритинг:",
        "kk": "🎨 Қазіргі түс: <b>{val}</b>\n\nЖаңа түс жазыңыз:",
        "ru": "🎨 Текущий цвет: <b>{val}</b>\n\nВведите новый цвет:",
    },
    "edit_plate_prompt": {
        "uz": "🔢 Hozirgi raqam: <b>{val}</b>\n\nYangi raqam kiriting:",
        "uz_cyr": "🔢 Ҳозирги рақам: <b>{val}</b>\n\nЯнги рақам киритинг:",
        "kk": "🔢 Қазіргі нөмір: <b>{val}</b>\n\nЖаңа нөмір жазыңыз:",
        "ru": "🔢 Текущий номер: <b>{val}</b>\n\nВведите новый номер:",
    },
    "role_passenger": {
        "uz": "👤 Yo'lovchi",
        "uz_cyr": "👤 Йўловчи",
        "kk": "👤 Жолаушы",
        "ru": "👤 Пассажир",
    },
    "role_driver_label": {
        "uz": "🚗 Haydovchi",
        "uz_cyr": "🚗 Ҳайдовчи",
        "kk": "🚗 Жүргізуші",
        "ru": "🚗 Водитель",
    },

    # ── Driver trip ───────────────────────────────────────────────────────
    "trip_select_route": {
        "uz": "🚐 <b>Qaysi yo'nalishda safar e'lon qilasiz?</b>",
        "uz_cyr": "🚐 <b>Қайси йўналишда сафар эълон қиласиз?</b>",
        "kk": "🚐 <b>Қай бағытта сапар жариялайсыз?</b>",
        "ru": "🚐 <b>По какому маршруту объявить поездку?</b>",
    },
    "trip_select_dir": {
        "uz": "Qaysi yo'nalishda ketasiz?",
        "uz_cyr": "Қайси йўналишда кетасиз?",
        "kk": "Қай бағытта кетесіз?",
        "ru": "В каком направлении?",
    },
    "trip_select_seats": {
        "uz": "👥 <b>Nechta joy bor?</b>\n\nJoy sonini tanlang:",
        "uz_cyr": "👥 <b>Нечта жой бор?</b>\n\nЖой сонини танланг:",
        "kk": "👥 <b>Неше орын бар?</b>\n\nОрын санын таңдаңыз:",
        "ru": "👥 <b>Сколько мест?</b>\n\nВыберите количество:",
    },
    "trip_announced": {
        "uz": "✅ <b>Safar e'lon qilindi!</b>\n\n🛣 {route}\n👥 {seats} ta joy\n💰 {price} so'm\n\n💡 Yo'lovchilar bron qilganda xabar olasiz.",
        "uz_cyr": "✅ <b>Сафар эълон қилинди!</b>\n\n🛣 {route}\n👥 {seats} та жой\n💰 {price} сўм",
        "kk": "✅ <b>Сапар жарияланды!</b>\n\n🛣 {route}\n👥 {seats} орын\n💰 {price} сум",
        "ru": "✅ <b>Поездка объявлена!</b>\n\n🛣 {route}\n👥 {seats} мест\n💰 {price} сум",
    },
    "trip_active": {
        "uz": "🚐 <b>Faol safar</b>",
        "uz_cyr": "🚐 <b>Фаол сафар</b>",
        "kk": "🚐 <b>Белсенді сапар</b>",
        "ru": "🚐 <b>Активная поездка</b>",
    },
    "trip_no_active": {
        "uz": "📋 <b>Faol safar yo'q</b>\n\n💡 \"🚐 Safar e'lon qilish\" tugmasini bosing.",
        "uz_cyr": "📋 <b>Фаол сафар йўқ</b>\n\n💡 \"🚐 Сафар эълон қилиш\" тугмасини босинг.",
        "kk": "📋 <b>Белсенді сапар жоқ</b>\n\n💡 \"🚐 Сапар жариялау\" батырмасын басыңыз.",
        "ru": "📋 <b>Активной поездки нет</b>\n\n💡 Нажмите \"🚐 Объявить поездку\".",
    },
    "trip_passengers_title": {
        "uz": "<b>Yo'ldan olinadigan yo'lovchilar:</b>",
        "uz_cyr": "<b>Йўлдан олинадиган йўловчилар:</b>",
        "kk": "<b>Жолдан алынатын жолаушылар:</b>",
        "ru": "<b>Пассажиры для подбора:</b>",
    },
    "trip_no_passengers": {
        "uz": "  — hali yo'q",
        "uz_cyr": "  — ҳали йўқ",
        "kk": "  — әлі жоқ",
        "ru": "  — пока нет",
    },
    "trip_seats_left": {
        "uz": "Yana {n} bo'sh",
        "uz_cyr": "Яна {n} бўш",
        "kk": "Тағы {n} бос",
        "ru": "Ещё {n} свободных",
    },
    "trip_seats_full": {
        "uz": "Joylar to'ldi!",
        "uz_cyr": "Жойлар тўлди!",
        "kk": "Орындар бітті!",
        "ru": "Мест нет!",
    },
    "btn_add_seat": {
        "uz": "➕ Joy",
        "uz_cyr": "➕ Жой",
        "kk": "➕ Орын",
        "ru": "➕ Место",
    },
    "btn_remove_seat": {
        "uz": "➖ Joy",
        "uz_cyr": "➖ Жой",
        "kk": "➖ Орын",
        "ru": "➖ Место",
    },
    "btn_depart": {
        "uz": "🚀 Yo'lga chiqish",
        "uz_cyr": "🚀 Йўлга чиқиш",
        "kk": "🚀 Жолға шығу",
        "ru": "🚀 Выехать",
    },
    "btn_trip_done": {
        "uz": "🏁 Safar tugadi",
        "uz_cyr": "🏁 Сафар тугади",
        "kk": "🏁 Сапар аяқталды",
        "ru": "🏁 Поездка завершена",
    },
    "btn_reannounce": {
        "uz": "🔄 Yana safar e'lon qilish",
        "uz_cyr": "🔄 Яна сафар эълон қилиш",
        "kk": "🔄 Қайта сапар жариялау",
        "ru": "🔄 Объявить снова",
    },
    "confirm_depart": {
        "uz": "⚠️ <b>Yo'lga chiqmoqchimisiz?</b>\n\nBarcha yo'lovchilarga xabar yuboriladi.",
        "uz_cyr": "⚠️ <b>Йўлга чиқмоқчимисиз?</b>",
        "kk": "⚠️ <b>Жолға шығасыз ба?</b>",
        "ru": "⚠️ <b>Выехать?</b>\n\nВсем пассажирам будет отправлено уведомление.",
    },
    "btn_yes_depart": {
        "uz": "🚀 Ha, yo'lga chiqish",
        "uz_cyr": "🚀 Ҳа, йўлга чиқиш",
        "kk": "🚀 Иә, жолға шығу",
        "ru": "🚀 Да, выехать",
    },
    "confirm_abort": {
        "uz": "⚠️ <b>Safarni bekor qilmoqchimisiz?</b>",
        "uz_cyr": "⚠️ <b>Сафарни бекор қилмоқчимисиз?</b>",
        "kk": "⚠️ <b>Сапарды бас тартасыз ба?</b>",
        "ru": "⚠️ <b>Отменить поездку?</b>",
    },
    "trip_departed": {
        "uz": "🚀 <b>Haydovchi yo'lga chiqdi!</b>\n\nTayyor bo'ling!",
        "uz_cyr": "🚀 <b>Ҳайдовчи йўлга чиқди!</b>\n\nТайёр бўлинг!",
        "kk": "🚀 <b>Жүргізуші жолға шықты!</b>\n\nДайын болыңыз!",
        "ru": "🚀 <b>Водитель выехал!</b>\n\nБудьте готовы!",
    },
    "trip_completed": {
        "uz": "🏁 <b>Safar yakunlandi!</b>",
        "uz_cyr": "🏁 <b>Сафар якунланди!</b>",
        "kk": "🏁 <b>Сапар аяқталды!</b>",
        "ru": "🏁 <b>Поездка завершена!</b>",
    },
    "trip_cancelled": {
        "uz": "❌ <b>Safar bekor qilindi.</b>",
        "uz_cyr": "❌ <b>Сафар бекор қилинди.</b>",
        "kk": "❌ <b>Сапар бас тартылды.</b>",
        "ru": "❌ <b>Поездка отменена.</b>",
    },

    # ── Driver registration ───────────────────────────────────────────────
    "enter_car_model": {
        "uz": "🚗 <b>Mashina ma'lumotlari</b>\n\nMashina modelini kiriting:\n<i>Masalan: Cobalt, Nexia, Spark</i>",
        "uz_cyr": "🚗 <b>Машина маълумотлари</b>\n\nМашина моделини киритинг:\n<i>Масалан: Cobalt, Nexia, Spark</i>",
        "kk": "🚗 <b>Көлік мәліметтері</b>\n\nКөлік моделін жазыңыз:\n<i>Мысалы: Cobalt, Nexia, Spark</i>",
        "ru": "🚗 <b>Данные машины</b>\n\nВведите модель:\n<i>Например: Cobalt, Nexia, Spark</i>",
    },
    "enter_car_color": {
        "uz": "🎨 Mashina rangini kiriting:\n<i>Masalan: Oq, Qora, Kumush</i>",
        "uz_cyr": "🎨 Машина рангини киритинг:\n<i>Масалан: Оқ, Қора, Кумуш</i>",
        "kk": "🎨 Көлік түсін жазыңыз:\n<i>Мысалы: Ақ, Қара, Күміс</i>",
        "ru": "🎨 Введите цвет:\n<i>Например: Белый, Чёрный, Серебро</i>",
    },
    "enter_license_plate": {
        "uz": "🔢 Davlat raqamini kiriting:\n<i>Masalan: 01A123BC</i>",
        "uz_cyr": "🔢 Давлат рақамини киритинг:\n<i>Масалан: 01A123BC</i>",
        "kk": "🔢 Мемлекеттік нөмірді жазыңыз:\n<i>Мысалы: 01A123BC</i>",
        "ru": "🔢 Введите гос. номер:\n<i>Например: 01A123BC</i>",
    },
    "driver_reg_success": {
        "uz": "✅ <b>Ro'yxatdan muvaffaqiyatli o'tdingiz!</b>\n\n🚗 {car} — {color}\n🔢 {plate}\n🛣 Yo'nalish: <b>{route}</b>",
        "uz_cyr": "✅ <b>Рўйхатдан муваффақиятли ўтдингиз!</b>\n\n🚗 {car} — {color}\n🔢 {plate}\n🛣 Йўналиш: <b>{route}</b>",
        "kk": "✅ <b>Тіркеу сәтті аяқталды!</b>\n\n🚗 {car} — {color}\n🔢 {plate}\n🛣 Бағыт: <b>{route}</b>",
        "ru": "✅ <b>Регистрация успешна!</b>\n\n🚗 {car} — {color}\n🔢 {plate}\n🛣 Маршрут: <b>{route}</b>",
    },
    "driver_not_verified": {
        "uz": "❌ <b>Siz hali tasdiqlanmagansiz.</b>",
        "uz_cyr": "❌ <b>Сиз ҳали тасдиқланмагансиз.</b>",
        "kk": "❌ <b>Сіз әлі расталмағансыз.</b>",
        "ru": "❌ <b>Вы ещё не подтверждены.</b>",
    },
    "driver_has_active": {
        "uz": "📋 Sizda allaqachon faol safar bor!\n\n💡 \"📋 Faol safar\" tugmasini bosing.",
        "uz_cyr": "📋 Сизда аллақачон фаол сафар бор!",
        "kk": "📋 Сізде белсенді сапар бар!",
        "ru": "📋 У вас уже есть активная поездка!",
    },
    "driver_no_routes": {
        "uz": "🛣 <b>Yo'nalishlar yo'q</b>\n\nSafar e'lon qilish uchun avval yo'nalish qo'shing.\n👉 \"🛣 Mening yo'nalishlarim\" tugmasini bosing.",
        "uz_cyr": "🛣 <b>Йўналишлар йўқ</b>",
        "kk": "🛣 <b>Бағыттар жоқ</b>",
        "ru": "🛣 <b>Маршрутов нет</b>\n\nДобавьте маршрут через \"Мои маршруты\".",
    },
    "driver_menu": {
        "uz": "🚗 Haydovchi menyu:",
        "uz_cyr": "🚗 Ҳайдовчи меню:",
        "kk": "🚗 Жүргізуші мәзірі:",
        "ru": "🚗 Меню водителя:",
    },

    # ── Help ──────────────────────────────────────────────────────────────
    "help_text": {
        "uz": "ℹ️ <b>TaxiBek — Yordam</b>\n\n🚕 <b>Taxi chaqirish:</b>\n  Yo'nalish tanlang → A→B yoki B→A\n\n🛣 <b>Yo'nalishlar:</b>\n  \"Mening yo'nalishlarim\" orqali boshqaring\n\n🚗 <b>Haydovchi bo'lish:</b>\n  /driver buyrug'ini yuboring\n\n📞 <b>Muammo bo'lsa:</b>\n  Admin bilan bog'laning",
        "uz_cyr": "ℹ️ <b>TaxiBek — Ёрдам</b>\n\n🚕 Такси чақириш\n🛣 Йўналишлар\n🚗 Ҳайдовчи бўлиш: /driver\n📞 Админ билан боғланинг",
        "kk": "ℹ️ <b>TaxiBek — Көмек</b>\n\n🚕 Такси шақыру\n🛣 Бағыттар\n🚗 Жүргізуші болу: /driver\n📞 Админге хабарласыңыз",
        "ru": "ℹ️ <b>TaxiBek — Помощь</b>\n\n🚕 Вызов такси\n🛣 Маршруты\n🚗 Стать водителем: /driver\n📞 Свяжитесь с админом",
    },
    "menu_refreshed": {
        "uz": "🔄 Menyu yangilandi!",
        "uz_cyr": "🔄 Меню янгиланди!",
        "kk": "🔄 Мәзір жаңартылды!",
        "ru": "🔄 Меню обновлено!",
    },
    "client_mode": {
        "uz": "👋 <b>{name}</b> — Yo'lovchi rejimi",
        "uz_cyr": "👋 <b>{name}</b> — Йўловчи режими",
        "kk": "👋 <b>{name}</b> — Жолаушы режимі",
        "ru": "👋 <b>{name}</b> — Режим пассажира",
    },
}


def t(key: str, lang: str = "uz", **kwargs) -> str:
    """Get translated string."""
    entry = _t.get(key, {})
    text = entry.get(lang) or entry.get("uz", f"[{key}]")
    if kwargs:
        text = text.format(**kwargs)
    return text
