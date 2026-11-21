"""Pega un texto (con acentos y emojis) en el campo que tenga el foco en el móvil (21-11-2026).

`adb shell input text` NO admite acentos ni emojis (Android lo rechaza). Esto usa el servidor de scrcpy (el que ya
está en C:\\Users\\edmun\\herramientas\\scrcpy): le manda un SET_CLIPBOARD con paste=1, que pone el texto en el
portapapeles del móvil y lo pega en el campo activo. No abre ninguna ventana. Hecho para el texto del reel
«Bailar la frase». Si scrcpy cambia de versión, cambiar VERSION.

Uso (python del venv): pegar_en_movil.py <texto.txt>   (antes, tocar el campo en el móvil con adb input tap)"""
import socket, struct, subprocess, sys, time

ADB = r"C:\Users\edmun\herramientas\scrcpy\adb.exe"
SERVER = r"C:\Users\edmun\herramientas\scrcpy\scrcpy-server"
VERSION = "5.0.1"
SCID = 0x1D2C3B4A
PUERTO = 27199

texto = open(sys.argv[1], encoding="utf-8").read().strip()
subprocess.run([ADB, "push", SERVER, "/data/local/tmp/scrcpy-server.jar"], check=True, capture_output=True)
subprocess.run([ADB, "forward", f"tcp:{PUERTO}", f"localabstract:scrcpy_{SCID:08x}"], check=True)
srv = subprocess.Popen([ADB, "shell", "CLASSPATH=/data/local/tmp/scrcpy-server.jar", "app_process", "/",
                        "com.genymobile.scrcpy.Server", VERSION, f"scid={SCID:08x}", "log_level=debug",
                        "tunnel_forward=true", "video=false", "audio=false", "control=true",
                        "send_device_meta=false", "send_dummy_byte=true", "cleanup=false"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
s = None
for i in range(60):
    time.sleep(0.25)
    try:
        c = socket.create_connection(("127.0.0.1", PUERTO), timeout=3)
        if c.recv(1):            # el servidor manda un byte cuando de verdad está escuchando
            s = c
            break
        c.close()
    except OSError:
        pass
if s is None:
    srv.kill(); print(srv.stdout.read()); raise SystemExit("no conecta con el servidor de scrcpy")
time.sleep(0.8)
b = texto.encode("utf-8")
s.sendall(struct.pack(">BQBI", 9, 1, 1, len(b)) + b)    # SET_CLIPBOARD, secuencia 0, paste=1
time.sleep(2.0)
try:
    s.settimeout(2); print("respuesta:", s.recv(64))
except Exception as e:
    print("sin respuesta:", e)
s.close()
time.sleep(0.5)
srv.kill()
try:
    print((srv.stdout.read() or "")[-800:])
except Exception:
    pass
subprocess.run([ADB, "forward", "--remove", f"tcp:{PUERTO}"])
print("enviado:", len(texto), "caracteres")
