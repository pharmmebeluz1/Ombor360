# Ombor360° v8 — Ko‘p abonentli tizim

Bu versiya bitta Ombor360° saytida bir nechta korxona/abonentni alohida kabinetlarda boshqaradi.

## Yangi imkoniyatlar

- Super Admin paneli
- Yangi korxona/abonent ochish
- Har korxona uchun alohida rahbar login/paroli
- Korxona ma’lumotlarini `company_id` bilan ajratish
- Har korxonaning mahsulotlari, kirim-chiqimi, moliyasi, xodimlari va hisobotlari bir-biriga aralashmaydi
- Abonent muddati va oylik tarif
- +30 kun yoki istalgan kun miqdorida uzaytirish
- Abonentni vaqtincha to‘xtatish/faollashtirish
- Super Admin korxona kabinetiga kirib tekshira oladi
- Korxona admin parolini Super Admin panelidan almashtirish
- Eski Ombor360 ma’lumotlari `Asosiy korxona`ga avtomatik biriktiriladi

## Boshlang‘ich loginlar

Eski korxona rahbari:
- Login: `admin`
- Parol: `admin123`

Super Admin:
- Login: `.env` dagi `SUPERADMIN_USERNAME`
- Parol: `.env` dagi `SUPERADMIN_PASSWORD`
- Agar Render Environment Variables qo‘yilmasa: `superadmin / admin360`

**Muhim:** Internetga chiqarishdan oldin `SUPERADMIN_PASSWORD`ni kuchli parolga almashtiring.

## Render

Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app
```

Render > Environment bo‘limida kamida quyidagilarni kiriting:

- `SECRET_KEY` — uzun tasodifiy qiymat
- `SUPERADMIN_USERNAME` — masalan `owner360`
- `SUPERADMIN_PASSWORD` — kuchli parol

## Baza

Sinov uchun SQLite ishlaydi. Ko‘p haqiqiy mijoz bilan ishlashda PostgreSQL tavsiya qilinadi. `DATABASE_URL` ga PostgreSQL manzilini kiritsangiz dastur `psycopg` orqali ulanadi.

## GitHub

ZIP ichidagi `Ombor360` papkasidagi fayllarni repositoryga yuklang. `.env` faylni GitHub’ga yuklamang.

## v9 — Abonent faolligi nazorati
Super Admin panelida har bir korxona bo‘yicha Ombor360 ichidagi faollik ko‘rinadi:
- Onlayn / Offline holati (2 daqiqalik faollik oynasi)
- Oxirgi kirish va oxirgi ko‘rilgan vaqt
- Foydalanuvchi ismi
- Qurilma turi (masalan Windows • Chrome yoki Android • Chrome)
- Oxirgi Ombor360 bo‘limi
- Bugungi kirim/chiqim operatsiyalari soni

Brauzer Ombor360 ochiq turganda har 60 soniyada yengil heartbeat yuboradi. Bu modul mijozning kompyuteri yoki boshqa dasturlarini kuzatmaydi; faqat Ombor360 ichidagi faoliyatni qayd etadi.

## v10 — Texnik yordam / Support markazi

Super Admin panelidagi har bir abonentda **Texnik yordam** tugmasi bor.

- Foydalanuvchilarning Ombor360° ichidagi onlayn/offline holati
- Oxirgi kirish, oxirgi faol sahifa va qurilma turi
- So‘nggi ombor harakatlari
- Audit: kim, qachon, nima o‘zgartirgani
- Server xatolarini avtomatik texnik jurnalga yozish
- Noto‘g‘ri login urinishlarini qayd etish
- **Support rejimi**: Super Admin mijoz kabinetiga texnik yordam sifatida kiradi
- Support rejimidagi o‘zgarishlar `[SUPPORT]` belgisi bilan Audit tarixida qoladi
- Mijozning boshqa dasturlari yoki shaxsiy fayllari kuzatilmaydi

PostgreSQL uchun `psycopg[binary]==3.3.2` ishlatiladi.

## v11 — Xodim mobil paneli

- Xodim va omborchi login qilganda mobil `Xodim paneli`ga kiradi.
- Bluetooth/USB skaner orqali QR/barcode kod urilganda mahsulot kartasi ochiladi.
- Mahsulot kartasida qoldiq, ombor, qator, polka, og‘irlik va yaroqlilik muddati ko‘rinadi.
- Xodim uchun soddalashtirilgan Kirim / Chiqim mavjud.
- Mahsulot joyini Ombor / Qator / Polka bo‘yicha o‘zgartirish mumkin.
- Inventarizatsiyada real qoldiq sanaladi va farq Audit jurnaliga yoziladi.
- Telefon brauzeri qo‘llasa, kamera orqali QR/barcode skanerlash ham mavjud.
- Xodim panelida narx va moliyaviy KPIlar ko‘rsatilmaydi.
