import os


def sunucu_kontrol(hedef):
    # Kullanıcıdan gelen değer doğrudan kabuk komutuna ekleniyor
    os.system("ping -c 1 " + hedef)


sunucu_kontrol(input("Sunucu adresi: "))
