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

## Barcode / QR skaner (v3)

Winson WAI-5770D-USB kabi USB HID skanerlar klaviatura sifatida ishlaydi.

1. Mahsulotlar bo‘limida `Barcode / SKU` maydonini bosib, kodni skaner qiling. Bo‘sh qoldirilsa tizim `OMB-000001` ko‘rinishida avtomatik kod beradi.
2. Kirim yoki Chiqim sahifasida `Barcode / QR skaner` maydonida mahsulot kodini skaner qiling.
3. Skaner Enter yuborsa, mahsulot avtomatik tanlanadi va fokus `Miqdor` maydoniga o‘tadi.
4. Mahsulot nomi, barcode yoki kategoriya bo‘yicha qidirish mumkin.

Eslatma: bir xil barcode/SKU ikki mahsulotga biriktirilmaydi.

## v5 — Avtomatik QR va joylashuv

Bu versiyada mahsulot qo‘shishda quyidagilar kiritiladi:
- mahsulot nomi va kategoriya;
- birlik va og‘irlik (kg);
- ombor, qator va polka;
- yaroqlilik muddati;
- minimal qoldiq, kirim va sotuv narxi.

`Saqlash` bosilganda mahsulotga `OMB-000001` ko‘rinishida yagona kod yaratiladi (agar Barcode/SKU qo‘lda kiritilmagan bo‘lsa) va QR etiketka avtomatik tayyorlanadi.

### Skaner rejimi
`Skaner` menyusiga kiring va Bluetooth/USB skaner bilan QR yoki barcode ni o‘qing. Mahsulot kartasida:
- nomi;
- qoldiq;
- og‘irligi;
- qaysi ombor/qator/polkada turgani;
- yaroqlilik muddati va qancha kun qolgani;
- kirim/sotuv narxi ko‘rinadi.

### A4 printer
`Mahsulotlar → A4 QR etiketkalar` orqali oddiy printerdan QR etiketkalar chiqarish mumkin. Keyin termal printerga o‘tilganda mahsulot kodlarini o‘zgartirish shart emas.
