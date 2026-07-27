import pymysql

conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='root',
    password='7233DB_Pass!2024',
    database='7tan_cn',
    charset='utf8mb4'
)

cursor = conn.cursor()
cursor.execute("SELECT ll_name, ll_pass FROM ll_useregs LIMIT 10")
rows = cursor.fetchall()

for row in rows:
    name = row[0]
    pwd = row[1]
    print(f"用户名: {name}")
    print(f"密码: {pwd}")
    print("-" * 40)

cursor.close()
conn.close()
