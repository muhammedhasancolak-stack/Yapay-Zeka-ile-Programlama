import sqlite3


def urun_ara(urun_adi):
    conn = sqlite3.connect("magaza.db")
    cursor = conn.cursor()
    sorgu = "SELECT * FROM urunler WHERE urun_adi = '" + urun_adi + "'"
    cursor.execute(sorgu)
    return cursor.fetchall()


print(urun_ara(input("Ürün adı: ")))
