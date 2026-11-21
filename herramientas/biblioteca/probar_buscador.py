# -*- coding: utf-8 -*-
"""Prueba Buscador\\buscar.html sin abrir nada en pantalla (Edge sin ventana, como render.py de los reels).
   python probar_buscador.py [palabra ...]     (por defecto: tresillo)
   python probar_buscador.py --foto salida.png tresillo    además saca una foto de la página
   Debe decir TODO BIEN."""
import sys, json, time, asyncio, subprocess, tempfile, base64, urllib.request
from pathlib import Path
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PAGINA = Path(__file__).resolve().parents[4] / "Buscador" / "buscar.html"
PUERTO = 9334


async def probar(consultas, foto=None):
    perfil = tempfile.mkdtemp(prefix="edge_buscador_")
    edge = subprocess.Popen([EDGE, "--headless=new", "--mute-audio", f"--remote-debugging-port={PUERTO}", f"--user-data-dir={perfil}",
                             "--window-size=1100,1400", "--no-first-run", "--allow-file-access-from-files", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = True
    try:
        for _ in range(100):
            try:
                pags = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json"))
                ws_url = next(p["webSocketDebuggerUrl"] for p in pags if p.get("type") == "page")
                break
            except Exception:
                time.sleep(0.2)
        else:
            sys.exit("Edge no arranca")
        async with websockets.connect(ws_url, max_size=50_000_000) as ws:
            n = 0

            async def cdp(metodo, **params):
                nonlocal n
                n += 1
                await ws.send(json.dumps({"id": n, "method": metodo, "params": params}))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get("id") == n:
                        if "error" in r:
                            raise RuntimeError(f"{metodo}: {r['error']}")
                        return r.get("result", {})

            async def js(expr):
                r = await cdp("Runtime.evaluate", expression=expr, returnByValue=True)
                return r["result"].get("value")

            await cdp("Page.addScriptToEvaluateOnNewDocument",
                      source="window.__errores=[];addEventListener('error',e=>__errores.push(e.message));")
            await cdp("Page.navigate", url=PAGINA.as_uri())
            for _ in range(150):
                if await js("document.readyState==='complete' && !!window.BIBLIOTECA"):
                    break
                await asyncio.sleep(0.2)
            else:
                sys.exit("La página no carga")
            print(f"Cargada: {await js('BIBLIOTECA.docs.length')} documentos, índice del {await js('BIBLIOTECA.hecho')}")
            for q in consultas:
                t = time.time()
                await js(f"document.getElementById('q').value={json.dumps(q)}; buscar(); 1")
                info = await js("document.getElementById('info').textContent")
                docs = await js("[...document.querySelectorAll('#res h3 > a, #res .part > a')].map(a=>a.textContent)")
                marcas = await js("document.querySelectorAll('#res mark').length")
                print(f"«{q}» ({time.time()-t:.1f} s): {info}")
                for d in docs[:12]:
                    print("   ·", d)
                if not docs or not marcas and not all(".part" for _ in docs):
                    ok = False
            await js("t2.click(); 1")
            filas = await js("document.querySelectorAll('#cat tr').length")
            print(f"Pestaña «Qué hay»: {filas} filas")
            ok = ok and filas > 20
            err = await js("(window.__errores||[]).join(' | ')")
            if err:
                print("ERRORES en la página:", err); ok = False
            if foto:
                await js("t1.click(); window.scrollTo(0,0); 1")
                img = await cdp("Page.captureScreenshot", format="png")
                Path(foto).write_bytes(base64.b64decode(img["data"]))
                print("foto:", foto)
    finally:
        edge.kill()
    return ok


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args, foto = sys.argv[1:], None
    if args[:1] == ["--foto"]:
        foto, args = args[1], args[2:]
    ok = asyncio.run(probar(args or ["tresillo"], foto))
    print("TODO BIEN" if ok else "ALGO FALLA")
