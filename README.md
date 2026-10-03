# Ombor360°

Ombor, kirim-chiqim, kassa, xodim avansi, oylik va sof foyda nazorati uchun Flask MVP.

## MVP ichida
- Mahsulotlar va minimal qoldiq
- Kirim / chiqim / qaytim
- Mashina, davlat raqami, haydovchi, kim berdi / kim oldi
- Kamera yozuviga URL bog‘lash
- Xodim pul so‘rovi → rahbar tasdig‘i → kassir berdi → xodim oldim
- Avansni oylikdan ayrish
- Oylikni oy bo‘yicha yopish
- Tushum / xarajat / sof foyda
- Audit tarixi
- Role: admin, manager, warehouse, cashier, accountant, employee
- Telegram bot uchun boshlang‘ich modul

## Lokal ishga tushirish (Windows)
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app app init-db
python app.py
```
Brauzer: http://127.0.0.1:5000

### Test loginlar
- Rahbar: `admin` / `admin123`
- Omborchi: `ombor` / `1234`
- Kassir: `kassir` / `1234`
- Buxgalter: `buxgalter` / `1234`

**Birinchi kirishda parollarni albatta almashtiring.**

## GitHub'ga yuklash
1. Yangi repository yarating, masalan `ombor360`.
2. Shu papkadagi barcha faylni repository'ga yuklang.
3. Render/Railway'da Python Web Service sifatida ulang.

### Render Start Command
```bash
gunicorn app:app
```

### Render Build Command
```bash
pip install -r requirements.txt
```

Deploydan keyin Shell orqali bir marta:
```bash
flask --app app init-db
```

## Muhim
SQLite MVP uchun. Real ishlab chiqarishda PostgreSQL ishlatish tavsiya qilinadi.
`DATABASE_URL` ga PostgreSQL manzilini berish mumkin.

## Kamera
Hozir harakat kartasiga `camera_url` qo‘yiladi. Real NVR/DVR integratsiyasi uchun kamera markasi va modeli kerak bo‘ladi (Hikvision/Dahua va h.k.).

## Telegram
`.env` faylga `TELEGRAM_BOT_TOKEN` va `PUBLIC_BASE_URL` kiriting, keyin:
```bash
python bot.py
```
Hozir bot web kabinetga kirish tugmasini beradi. Keyingi bosqichda pul so‘rovi/tasdiqlashni to‘liq bot ichiga ko‘chirish mumkin.
