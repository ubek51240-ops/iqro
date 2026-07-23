# IQRO.UZ - Onlayn Kitob Do'koni va Admin Paneli (Python Flask Server)

Ushbu loyiha IQRO onlayn kitob do'koni uchun yaratilgan zamonaviy web-sayt, Admin Boshqaruv paneli va Python Flask serveridan iborat.

## 📁 Loyiha Tarkibi
- `app.py` - Flask backend server (REST API, Admin Panel API & Statik fayllarni uzatish)
- `index.html` - Kitobxonlar uchun interaktiv onlayn do'kon va savat
- `admin.html` - Kitoblar, narxlar va buyurtmalarni boshqarish paneli
- `requirements.txt` - Python kutubxonalari ro'yxati

## 🚀 Ishga Tushirish Yo'riqnomasi

### 1. Zarur Python kutubxonalarini o'rnatish:
```bash
python -m pip install -r requirements.txt
```

### 2. Python serverini ishga tushirish:
```bash
python app.py
```

### 3. Brauzerda ochish:
- 🛒 **Kitob Do'koni:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
- ⚙️ **Admin Panel:** [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin)

---

## 🛠️ Mavjud API Endpointlar (Backend)

- `GET /` - Asosiy veb-sahifani (`index.html`) qaytaradi.
- `GET /admin` - Admin Boshqaruv Panelini (`admin.html`) qaytaradi.
- `GET /api/books` - Kitoblar ro'yxatini qaytaradi.
- `POST /api/admin/books` - Yangi kitob va narx qo'shish.
- `PUT /api/admin/books/<id>` - Kitob ma'lumotlari hamda narxini o'zgartirish.
- `DELETE /api/admin/books/<id>` - Kitobni o'chirish.
- `GET /api/admin/orders` - Kelib tushgan buyurtmalar ro'yxatini olish.
- `POST /api/order` - Xarid savatidagi buyurtmani tasdiqlash.
