import pickle
import socket


def veri_al():
    sunucu = socket.socket()
    sunucu.bind(("0.0.0.0", 9000))
    sunucu.listen(1)
    baglanti, _ = sunucu.accept()
    gelen_bayt = baglanti.recv(4096)  # ağdan gelen güvenilmeyen veri
    return pickle.loads(gelen_bayt)


print(veri_al())
