# Ombor360° — Modern Dashboard v2

Ombor, kirim-chiqim, kassa, xodim avansi, oylik va sof foyda nazorati uchun Flask dasturi.

## v2 yangiliklari
- Yangi premium Ombor360° bosh sahifa dizayni
- 6 ta KPI: ombor qiymati, bugungi kirim, bugungi chiqim, sof foyda, kam qolgan mahsulot, faol xodimlar
- Oxirgi 6 oy kirim/chiqim grafigi
- Kam qolgan mahsulotlar paneli
- Oxirgi harakatlar
- Eng ko‘p kirgan mahsulotlar TOP-5
- Pul so‘rovlari preview
- Tezkor Kirim / Chiqim / Mahsulot / Hisobot tugmalari
- Mahsulot qidirish
- Hisobotlar va Sozlamalar sahifasi
- Telefon/planshet uchun moslashuvchan menyu
- Jinja format xatolari tuzatildi

## Asosiy funksiyalar
- Mahsulotlar va minimal qoldiq
- Kirim / chiqim / qaytim
- Mashina, davlat raqami, haydovchi, kim berdi / kim oldi
- Kamera yozuviga URL bog‘lash
- Xodim pul so‘rovi → rahbar tasdig‘i → kassir berdi → xodim oldim
- Avansni oylikdan ayrish
- Oylikni oy bo‘yicha yopish
- Tushum / xarajat / sof foyda
- Audit tarixi
- Rollar: admin, manager, warehouse, cashier, accountant, employee

## Test loginlar
- Rahbar: `admin` / `admin123`
- Omborchi: `ombor` / `1234`
- Kassir: `kassir` / `1234`
- Buxgalter: `buxgalter` / `1234`

Birinchi real foydalanishda parollarni almashtiring.

## Render
Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app
```

Render GitHub repositoryga ulangan bo‘lsa, GitHubdagi yangi commitdan keyin avtomatik qayta deploy qiladi.

## Muhim
SQLite sinov/MVP uchun. Doimiy real ishlatish uchun PostgreSQL tavsiya etiladi, chunki Render Free servisida lokal SQLite fayli doimiy saqlanishiga tayanib bo‘lmaydi.
