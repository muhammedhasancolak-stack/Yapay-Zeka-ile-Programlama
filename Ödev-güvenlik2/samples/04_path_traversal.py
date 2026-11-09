BASE_DIR = "/var/www/uploads/"


def dosya_oku(filename):
    # Kullanıcıdan gelen dosya adı doğrudan klasör yoluna ekleniyor
    with open(BASE_DIR + filename, "r", encoding="utf-8") as f:
        return f.read()


print(dosya_oku(input("Dosya adı: ")))
