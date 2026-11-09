import psycopg2


def baglan():
    return psycopg2.connect(
        host="localhost",
        database="eticaret",
        user="admin",
        password="8888",
    )
