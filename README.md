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
