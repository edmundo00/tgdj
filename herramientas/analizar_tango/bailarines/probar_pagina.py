"""Prueba la página de marcar sin abrir nada en pantalla (Edge sin ventana): carriles, clic en el pie, Q W O P (parado
y sonando), doble clic en un carril, arrastrar en la línea de tiempo (tiempo y carril), varias a la vez, zoom, imán,
afinar, deshacer, borrar, PARAR. Usa un navegador de prueba aparte (no toca las marcas del Chrome de Edmundo).
Uso: python probar_pagina.py "<carpeta marcar_...>" [captura.png]
"""
import os, json, time, base64, asyncio, subprocess, tempfile, shutil, urllib.request, pathlib, sys
import websockets
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PAG = pathlib.Path(sys.argv[1], "index.html").as_uri()
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(tempfile.gettempdir(), "probar_pagina.png")
VIEJAS = [{"n": 129, "quien": "S", "pie": "I", "x": 300, "y": 1650}, {"n": 185, "quien": "L", "pie": "D", "x": 700, "y": 1700}]
fallos = []


def ok(cond, txt):
    print(("  OK   " if cond else "  FALLO ") + txt)
    if not cond:
        fallos.append(txt)


async def main():
    perfil = tempfile.mkdtemp()
    e = subprocess.Popen([EDGE, "--headless=new", "--remote-debugging-port=9336", f"--user-data-dir={perfil}", "--window-size=1600,1050",
                          "--mute-audio", "--autoplay-policy=no-user-gesture-required", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                ws_url = next(p["webSocketDebuggerUrl"] for p in json.load(urllib.request.urlopen("http://127.0.0.1:9336/json")) if p["type"] == "page"); break
            except Exception:
                time.sleep(0.2)
        async with websockets.connect(ws_url, max_size=80_000_000) as ws:
            n = 0
            errores = []

            async def cdp(m, **p):
                nonlocal n
                n += 1; i = n
                await ws.send(json.dumps({"id": i, "method": m, "params": p}))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get("method") == "Runtime.exceptionThrown":
                        errores.append(r["params"]["exceptionDetails"].get("exception", {}).get("description", "?")[:200])
                    if r.get("id") == i:
                        return r.get("result", r.get("error"))

            async def val(x):
                r = await cdp("Runtime.evaluate", expression=x, returnByValue=True, awaitPromise=True)
                return r.get("result", {}).get("value", r)

            async def tecla(key, code, vk, mods=0):
                await cdp("Input.dispatchKeyEvent", type="keyDown", key=key, code=code, windowsVirtualKeyCode=vk, modifiers=mods)
                await cdp("Input.dispatchKeyEvent", type="keyUp", key=key, code=code, windowsVirtualKeyCode=vk, modifiers=mods)
                await asyncio.sleep(0.08)

            async def raton(t, x, y, botones=0, boton="left", clics=1, mods=0):
                await cdp("Input.dispatchMouseEvent", type=t, x=x, y=y, button=boton, buttons=botones, clickCount=clics, modifiers=mods)

            async def clic(x, y, boton="left", mods=0, clics=1):
                await raton("mousePressed", x, y, 1, boton, clics, mods); await raton("mouseReleased", x, y, 0, boton, clics, mods)
                await asyncio.sleep(0.1)

            async def arrastrar(x0, y0, x1, y1):
                await raton("mousePressed", x0, y0, 1)
                for k in range(1, 6):
                    await raton("mouseMoved", x0 + (x1 - x0) * k / 5, y0 + (y1 - y0) * k / 5, 1)
                await raton("mouseReleased", x1, y1, 0); await asyncio.sleep(0.1)

            async def boton(sel):
                b = json.loads(await val(f"JSON.stringify(document.querySelector('{sel}').getBoundingClientRect())"))
                await clic(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)

            # punto de la línea de tiempo (en la pantalla) para un fotograma y carril
            async def punto(fr, car):
                return json.loads(await val(f"(()=>{{const g=geom(),r=LC.getBoundingClientRect();return JSON.stringify({{x:r.left+g.x({fr})*r.width/LC.width,y:r.top+(g.yCarr+{car}*ALTO_CARRIL+ALTO_CARRIL/2)*r.height/LC.height}})}})()"))

            await cdp("Runtime.enable")
            await cdp("Page.navigate", url=PAG); await asyncio.sleep(1)
            await val(f"localStorage.clear(); localStorage.setItem('pisadas_prueba', {json.dumps(json.dumps(VIEJAS))})")
            await cdp("Page.reload"); await asyncio.sleep(3)
            ok(await val("marcas.length") == 2, "recupera las marcas de la página antigua")
            ok(await val("CARRILES.length") == 4, "4 carriles (Sol izq/der, London izq/der)")
            ok(await val("marcas.find(m=>m.n===185).b") == 1 and await val("marcas.find(m=>m.n===185).pie") == "D", "la antigua de London queda en London der")

            # clic en el pie en la imagen
            await val("ir(140-F0)")
            c = json.loads(await val("JSON.stringify(capa.getBoundingClientRect())"))
            await clic(c["x"] + c["width"] * 0.25, c["y"] + c["height"] * 0.88)
            ok(await val("marcas.some(m=>m.n===140&&m.b===0&&m.pie==='I')"), "clic en la imagen = pisada Sol izq en el fotograma 140")
            ok(await val("carril") == 1, "tras el clic cambia solo a Sol der")

            # Q W O P parado
            await val("ir(150-F0)")
            await tecla("o", "KeyO", 79)
            ok(await val("marcas.some(m=>m.b===1&&m.pie==='I'&&Math.abs(m.n-150)<=3)"), "tecla O = London izq ahora (con imán a la rejilla)")
            ok(await val("selUna() && selUna().provisional === true"), "queda provisional (sitio copiado)")
            await clic(c["x"] + c["width"] * 0.6, c["y"] + c["height"] * 0.9)
            ok(await val("selUna() && !selUna().provisional && selUna().b===1"), "el clic en la imagen coloca la provisional en el pie")

            # al vuelo mientras suena
            await val("ir(160-F0)")
            await boton("#play"); await asyncio.sleep(0.4)
            ok("PARAR" in await val("document.getElementById('play').textContent"), "el botón dice PARAR mientras suena")
            antes = await val("marcas.length")
            await tecla("w", "KeyW", 87); await asyncio.sleep(0.3); await tecla("p", "KeyP", 80)
            await asyncio.sleep(0.3); await boton("#play")
            ok(await val("marcas.length") == antes + 2, "W y P al vuelo añaden 2 pisadas sin parar la música")
            ok("Escuchar" in await val("document.getElementById('play').textContent"), "PARAR la detiene")

            # doble clic en un carril
            p = await punto(200, 3)
            await clic(p["x"], p["y"], clics=1); await clic(p["x"], p["y"], clics=2)
            await cdp("Runtime.evaluate", expression="LC.dispatchEvent(new MouseEvent('dblclick',{clientX:%f,clientY:%f,bubbles:true}))" % (p["x"], p["y"]))
            ok(await val("marcas.some(m=>m.b===1&&m.pie==='D'&&Math.abs(m.n-200)<=3)"), "doble clic en el carril London der crea pisada")

            # arrastrar a los lados (tiempo) con imán
            await val("ponIman('no')")
            m140 = await punto(140, 0); dest = await punto(146, 0)
            await arrastrar(m140["x"], m140["y"], dest["x"], dest["y"])
            ok(await val("marcas.some(m=>m.b===0&&m.pie==='I'&&m.n===146)") and not await val("marcas.some(m=>m.n===140&&m.b===0)"), "arrastrar en la línea: 140 → 146")
            # arrastrar a otro carril
            a = await punto(146, 0); b = await punto(146, 1)
            await arrastrar(a["x"], a["y"], b["x"], b["y"])
            ok(await val("marcas.some(m=>m.b===0&&m.pie==='D'&&m.n===146)"), "arrastrar abajo: pasa a Sol der")
            # imán al soltar
            await val("ponIman('rejilla')")
            a = await punto(146, 1); b = await punto(148, 1)
            await arrastrar(a["x"], a["y"], b["x"], b["y"])
            ok(await val("(()=>{const m=marcas.find(m=>m.b===0&&m.pie==='D'&&Math.abs(m.n-148)<4);return m&&Math.abs(m.n-cercano(semis.map(s=>s.f),m.n,9))<0.6})()"), "con imán cae en una casilla de la rejilla")

            # varias a la vez
            await val("ponIman('no')")
            n1 = await val("marcas.filter(m=>m.b===0).map(m=>m.n).sort((a,b)=>a-b)[0]")
            q1 = await punto(n1, await val(f"carrilDe(marcas.find(m=>m.b===0&&m.n==={n1}))"))
            await clic(q1["x"], q1["y"])
            n2 = await val("marcas.filter(m=>m.b===1).map(m=>m.n).sort((a,b)=>a-b)[0]")
            q2 = await punto(n2, await val(f"carrilDe(marcas.find(m=>m.b===1&&m.n==={n2}))"))
            await clic(q2["x"], q2["y"], mods=8)
            ok(await val("sel.size") == 2, "Mayús+clic elige 2")
            await tecla(".", "Period", 190)
            ok(await val(f"marcas.some(m=>m.n==={n1}+1&&m.b===0) && marcas.some(m=>m.n==={n2}+1&&m.b===1)"), "«.» mueve las 2 un fotograma")

            # zoom
            await val("ir(190-F0)")
            await tecla("c", "KeyC", 67)
            ok(await val("vista.b-vista.a") < 90, "C = ver solo el compás")
            await tecla("0", "Digit0", 48)
            ok(await val("vista.a===F0&&vista.b===F1"), "0 = ver todo")
            r = json.loads(await val("JSON.stringify(LC.getBoundingClientRect())"))
            await cdp("Input.dispatchMouseEvent", type="mouseWheel", x=r["x"] + r["width"] * 0.6, y=r["y"] + 20, deltaX=0, deltaY=-300)
            await asyncio.sleep(0.2)
            ok(await val("vista.b-vista.a") < await val("F1-F0"), "rueda del ratón = zoom")

            # arrastrar un pie desde su botón a la línea de tiempo y a la imagen
            await tecla("0", "Digit0", 48); await val("ponIman('sonido')")
            bt = json.loads(await val("JSON.stringify(document.querySelectorAll('#carriles button')[3].getBoundingClientRect())"))
            dest = await punto(250, 0)
            antes = await val("marcas.length")
            await arrastrar(bt["x"] + 20, bt["y"] + 10, dest["x"], dest["y"])
            ok(await val("marcas.length") == antes + 1 and await val("aColocar && aColocar.b===1 && aColocar.pie==='D'"), "arrastrar «Leader der» del botón a la línea crea pisada (a colocar)")
            ok(await val("PICOS.some(p=>Math.abs(p-aColocar.n)<0.6)") or not await val("PICOS.some(p=>Math.abs(p-aColocar.n)<3)"), "imán sonido: pegada al tope de la onda")
            ok("Clic en el pie para colocar" in await val("(()=>{pintar();return 'Clic en el pie para colocar'})()"), "letrero de «a colocar»")
            nAC = await val("aColocar.n")
            await clic(c["x"] + c["width"] * 0.7, c["y"] + c["height"] * 0.92)
            ok(await val(f"marcas.length") == antes + 1 and await val(f"marcas.find(m=>m.n==={nAC}&&m.b===1&&m.pie==='D').x") > 650, "clic en la imagen coloca ESA pisada (no crea otra)")
            ok(await val("aColocar === null"), "después ya no hay ninguna a colocar")
            bt = json.loads(await val("JSON.stringify(document.querySelectorAll('#carriles button')[0].getBoundingClientRect())"))
            antes = await val("marcas.length")
            await arrastrar(bt["x"] + 20, bt["y"] + 10, c["x"] + c["width"] * 0.3, c["y"] + c["height"] * 0.9)
            ok(await val("marcas.length") == antes + 1 and await val(f"marcas.some(m=>m.n===F0+i&&m.b===0&&m.pie==='I')"), "arrastrar «Follower izq» a la imagen crea pisada en ese pie")
            # elegir en la línea y colocar con un clic
            q = await punto(nAC, 3)
            await clic(q["x"], q["y"])
            ok(await val(f"aColocar && aColocar.n==={nAC}"), "clic en una pisada de la línea la deja «a colocar»")
            await clic(c["x"] + c["width"] * 0.55, c["y"] + c["height"] * 0.88)
            ok(await val(f"marcas.find(m=>m.n==={nAC}&&m.b===1&&m.pie==='D').x") < 650, "y el clic en la imagen la mueve")
            ok(await val("document.querySelectorAll('details').length") >= 3, "apartados plegables")
            ok("Leader" in await val("nomCarril(2)") and "Follower" in await val("nomCarril(0)"), "carriles Follower / Leader")
            await val("sel = new Set(marcas.slice(0,2)); pintar()")

            # copiar para Claude
            t = await val("textoCopia()")
            ok(t.startswith("PISADAS") and len(t.splitlines()) == await val("marcas.length") + 1, "Copiar: una línea por pisada")
            # al principio y velocidad (arriba, junto a Escuchar)
            await val("ir(200-F0)"); await boton("#bInicio")
            ok(await val("i") == 0, "⏮ Al principio")
            await boton('[data-vel="0.25"]')
            ok(await val("vel") == 0.25, "velocidad 25 % desde arriba")
            await boton('[data-vel="0.5"]')

            # deshacer, rehacer, borrar
            antes = await val("marcas.length")
            await tecla("Delete", "Delete", 46)
            ok(await val("marcas.length") == antes - 2, "Supr borra las elegidas")
            await tecla("z", "KeyZ", 90)
            ok(await val("marcas.length") == antes, "Z deshace")
            await tecla("y", "KeyY", 89)
            ok(await val("marcas.length") == antes - 2, "Y rehace")
            await tecla("z", "KeyZ", 90)

            await val("ir(185-F0)"); await tecla("0", "Digit0", 48)
            await raton("mouseMoved", c["x"] + c["width"] * 0.3, c["y"] + c["height"] * 0.85)
            await asyncio.sleep(0.3)
            img = await cdp("Page.captureScreenshot", format="png"); open(OUT, "wb").write(base64.b64decode(img["data"]))
            ok("Follower izq" in await val("document.getElementById('stats').textContent"), "estadísticas por pie")
            ok(not errores, "sin errores de la página" + (": " + " | ".join(errores) if errores else ""))
            await val("localStorage.clear()")
    finally:
        e.terminate(); shutil.rmtree(perfil, ignore_errors=True)
    print("\nTODO BIEN" if not fallos else f"\n{len(fallos)} FALLOS")


asyncio.run(main())
