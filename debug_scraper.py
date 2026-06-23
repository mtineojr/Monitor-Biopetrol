import requests
import time
import random

URL      = "http://ec2-3-22-240-207.us-east-2.compute.amazonaws.com/guiasaldos/main/donde/134"
BASE_URL = "http://ec2-3-22-240-207.us-east-2.compute.amazonaws.com"

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language":           "es-BO,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding":           "gzip, deflate",
    "Connection":                "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})

try:
    session.get(BASE_URL, timeout=10)
    time.sleep(random.uniform(1.0, 2.5))
except Exception as e:
    print(f"[WARN] warm-up falló: {e}")

response = session.get(URL, timeout=15, headers={"Referer": BASE_URL + "/"})
print(f"HTTP Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
print(f"Longitud respuesta: {len(response.text)} chars")
print("─" * 60)
print("PRIMEROS 1000 CARACTERES:")
print(response.text[:1000])
print("─" * 60)
print("CONTIENE 'array(5)':", "array(5)" in response.text)
print("CONTIENE 'saldo':", "saldo" in response.text.lower())
print("CONTIENE 'var_dump':", "var_dump" in response.text.lower())

import re
# Buscar y mostrar el primer bloque array(5)
match = re.search(r'array\(5\)\s*\{.{0,800}', response.text, re.DOTALL)
if match:
    print("BLOQUE array(5) ENCONTRADO:")
    print(match.group(0))
else:
    # Si no, buscar contexto alrededor de "saldo"
    idx = response.text.lower().find("saldo")
    print("CONTEXTO ALREDEDOR DE 'saldo':")
    print(response.text[max(0, idx-200):idx+500])

import re

# Mostrar TODOS los bloques array(5) encontrados con su saldo
bloques = re.split(r'(?=array\(5\)\s*\{)', response.text)
count = 0
for b in bloques:
    if 'array(5)' not in b:
        continue
    count += 1
    saldo_int = re.search(r'"saldo"\]\s*=>\s*int\((\d+)\)', b)
    saldo_str = re.search(r'"saldo"\]\s*=>\s*string\(\d+\)\s*"([^"]+)"', b)
    un = re.search(r'"un"\]\s*=>\s*int\((\d+)\)', b)
    print(f"\n--- BLOQUE {count} | un={un.group(1) if un else '?'} | saldo_int={saldo_int.group(1) if saldo_int else 'N/A'} | saldo_str={saldo_str.group(1) if saldo_str else 'N/A'}")
    print(b[:600])
