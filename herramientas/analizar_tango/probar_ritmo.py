r"""Prueba la página de ritmo con una canción sin abrir nada en pantalla (Edge sin ventana).

    python probar_ritmo.py "<carpeta de _ritmo\canción>"   (abre «Analisis tangos
itmo.html?c=<canción>»)

Comprueba: que no hay errores, que están los botones de velocidad y de clic de tresillo/corcheas,
y que al 60 % el audio avanza a 0,6 y los clics se van programando mientras suena. Debe decir TODO BIEN.
Con --foto salida.png <compás> [n compases] [casillas] guarda además una foto de la lupa.
Con --pagina salida.png [ancho] guarda una foto de la página entera (ancho 1300 = escritorio, 390 = móvil).
Si la canción tiene partitura (partitura_datos.js) prueba también el panel «Partitura»; con
--partitura salida.png [ancho] [compás] saca una foto de ese panel abierto en ese compás.
"""
import asyncio, json, os, subprocess, sys, tempfile, time, urllib.request, pathlib
import websockets

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas
EDGE = rutas.buscar_edge()
PUERTO = 9333


async def probar(url):
    perfil = tempfile.mkdtemp(prefix="edge_ritmo_")
    edge = subprocess.Popen([EDGE, "--headless=new", "--mute-audio", f"--remote-debugging-port={PUERTO}", f"--user-data-dir={perfil}",
                             "--autoplay-policy=no-user-gesture-required", "--allow-file-access-from-files", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    fallos = []
    try:
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json"))
                ws_url = [t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"]; break
            except Exception:
                time.sleep(0.3)
        else:
            sys.exit("Edge no arranca")
        async with websockets.connect(ws_url, max_size=None) as ws:
            n = 0
            async def cdp(m, **p):
                nonlocal n; n += 1; i = n
                await ws.send(json.dumps(dict(id=i, method=m, params=p)))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get("id") == i: return r.get("result", {})
            async def ev(x):
                r = await cdp("Runtime.evaluate", expression=x, returnByValue=True, awaitPromise=True)
                return r.get("result", {}).get("value")
            await cdp("Page.enable")
            await cdp("Page.addScriptToEvaluateOnNewDocument", source="window.__errores=[];addEventListener('error',e=>__errores.push(e.message));")
            await cdp("Page.navigate", url=url)
            for _ in range(100):
                if await ev("document.readyState==='complete' && !!document.getElementById('play')"): break
                await asyncio.sleep(0.2)
            await asyncio.sleep(1.5)
            global BPM
            BPM = await ev("M.bpm")
            bot = await ev("[document.querySelectorAll('[data-vel]').length, document.querySelectorAll('[data-rej]').length]")
            if bot != [5, 3]: fallos.append(f"faltan botones (velocidad, clics): {bot}")
            # al 60 % con clic de tresillo, desde el segundo 30
            await ev("document.querySelector('[data-vel=\"0.6\"]').click(); document.querySelector('[data-rej=\"_tres\"]').click(); 1")
            await ev("cursor=30; escuchar(30).then(()=>1)")
            await asyncio.sleep(0.4)
            a = await ev("[EL.mezcla.currentTime, ahora(), sonando.nodos.length, ctx.currentTime]")
            await asyncio.sleep(2.0)
            b = await ev("[EL.mezcla.currentTime, ahora(), sonando.nodos.length, ctx.currentTime]")
            if not a or not b:
                fallos.append("no suena")
            else:
                vel = (b[0] - a[0]) / (b[3] - a[3])
                # clics que tocaban entre las dos medidas: metrónomo apagado, solo tresillo = 2 por tiempo
                esperados = 2 * (b[0] - a[0]) / (60 / BPM)
                nuevos = b[2] - a[2]
                print(f"al 60 %: el audio avanza a {vel:.2f} · clics nuevos mientras sonaba {nuevos} (tocaban ~{esperados:.0f})")
                if abs(vel - 0.6) > 0.05: fallos.append(f"la velocidad no es 0,6 sino {vel:.2f}")
                if abs(nuevos - esperados) > 3: fallos.append(f"clics programados {nuevos}, tocaban {esperados:.0f}")
            # vuelta a 100 %
            await ev("parar(); document.querySelector('[data-vel=\"1\"]').click(); escuchar(30).then(()=>1)")
            await asyncio.sleep(1.0)
            c = await ev("[ahora(), sonando ? sonando.vel : null]")
            if not c or c[1] != 1: fallos.append(f"al 100 % no va: {c}")
            await ev("parar(); 1")
            await probar_reproductor(ev, fallos)
            await probar_menus(ev, fallos)
            await probar_trozo(ev, fallos)
            await probar_video(ev, cdp, fallos)
            await probar_estrellas(ev, fallos)
            # partitura (19-11-2026): solo si la canción tiene partitura_datos.js
            hay = await ev("!!window.PARTITURA")
            oculto = await ev("document.getElementById('panel_partitura').hidden")
            if not hay:
                if not oculto: fallos.append("sin partitura, pero el panel «Partitura» se ve")
            else:
                await probar_partitura(ev, fallos)
                await probar_vistas(ev, cdp, fallos)
            if PARTI:
                ancho = PARTI[1]; movil = ancho < 700
                await cdp("Emulation.setDeviceMetricsOverride", width=ancho, height=900, deviceScaleFactor=1 if not movil else 2, mobile=movil)
                await ev("window.dispatchEvent(new Event('resize')); 1")
                await ev("$('panel_partitura').open=true; 1")
                await asyncio.sleep(1.5)     # si cambia el ancho, la página la vuelve a dibujar sola
                if movil:   # como la ve Edmundo en el móvil la primera vez: solo bandoneones, piano y contrabajo
                    await ev("partesVer=['bandoneones','piano','contrabajo'].filter(g=>PT.partes.some(p=>p.grupo===g)); marcaPartes(); dibujaPartitura(); 1")
                seguidas = 0     # esperar a que esté dibujada y quieta (al cambiar el ancho se vuelve a dibujar sola)
                for _ in range(200):
                    seguidas = seguidas + 1 if await ev("window.__partituraLista===true && !enCurso") else 0
                    if seguidas >= 3: break
                    await asyncio.sleep(0.5)
                await ev(f"cursor=TP[{PARTI[2]}]+0.3; vIni=unos.filter(u=>u<=cursor).pop()||unos[0]; ponInfo(cursor); marcaPartitura(true); aLaVista({PARTI[2]}); pinta(); 1")
                await asyncio.sleep(1.2)
                # ventana tan alta como la página entera ANTES de la foto (la foto con captureBeyondViewport cambia el tamaño
                # de la ventana a mitad, la partitura se redibuja y sale «Dibujando…»)
                alto_pag = await ev("document.documentElement.scrollHeight")
                await cdp("Emulation.setDeviceMetricsOverride", width=ancho, height=alto_pag, deviceScaleFactor=1 if not movil else 2, mobile=movil)
                await asyncio.sleep(1.0)
                seguidas = 0
                for _ in range(200):
                    seguidas = seguidas + 1 if await ev("window.__partituraLista===true && !enCurso") else 0
                    if seguidas >= 3: break
                    await asyncio.sleep(0.5)
                await ev(f"$('panel_partitura').scrollIntoView({{block:'start'}}); aLaVista({PARTI[2]}); marcaPartitura(true); 1")
                await asyncio.sleep(0.8)
                r = await ev("(()=>{const b=$('panel_partitura').getBoundingClientRect();return [b.x,b.y+scrollY,b.width,b.height]})()")
                import base64
                # todo el ancho de la ventana: si la foto recorta a lo ancho, la ventana encoge y la partitura se redibuja
                img = await cdp("Page.captureScreenshot", format="png", clip=dict(x=0, y=r[1], width=ancho, height=r[3], scale=1))
                open(PARTI[0], "wb").write(base64.b64decode(img["data"])); print("foto de la partitura:", PARTI[0])
            if FOTO:
                # foto de la lupa en un compás (para mirarla sin abrir nada)
                await cdp("Emulation.setDeviceMetricsOverride", width=1300, height=1000, deviceScaleFactor=1, mobile=False)
                await ev(f"NCOMP={FOTO[2]}; SUB={FOTO[3]}; vIni=(P.find(p=>p.compas=={FOTO[1]}&&p.tiempo===1)||P[0]).seg; pinta(); 1")
                await asyncio.sleep(1.5)
                await ev("$('lupa').scrollIntoView({block:'center'}); 1")
                await asyncio.sleep(0.8)
                r = await ev("(()=>{const b=$('lupa').getBoundingClientRect();return [b.x,b.y+scrollY,b.width,b.height]})()")
                import base64
                img = await cdp("Page.captureScreenshot", format="png", clip=dict(x=r[0], y=r[1], width=r[2], height=r[3], scale=1), captureBeyondViewport=True)
                open(FOTO[0], "wb").write(base64.b64decode(img["data"])); print("foto:", FOTO[0])
            if PAGINA:
                ancho = PAGINA[1]; movil = ancho < 700
                await cdp("Emulation.setDeviceMetricsOverride", width=ancho, height=900, deviceScaleFactor=1 if not movil else 2, mobile=movil)
                if FOTO is None:
                    await ev("vIni=(P.find(p=>p.compas==66&&p.tiempo===1)||P[0]).seg; pinta(); 1")
                await ev("window.dispatchEvent(new Event('resize')); scrollTo(0,0); 1")
                await asyncio.sleep(1.5)
                alto = await ev("document.documentElement.scrollHeight")
                import base64
                img = await cdp("Page.captureScreenshot", format="png", clip=dict(x=0, y=0, width=ancho, height=alto, scale=1), captureBeyondViewport=True)
                open(PAGINA[0], "wb").write(base64.b64decode(img["data"])); print("foto de la página:", PAGINA[0])
            await probar_extras(ev, cdp, url, fallos)
            if SUBIR:
                await probar_subir(ev, cdp, url, fallos)
            err = await ev("(window.__errores||[]).join(' | ')")
            if err: fallos.append("errores en la página: " + err)
    finally:
        edge.kill()
    print("TODO BIEN" if not fallos else "FALLOS:\n  " + "\n  ".join(fallos))
    return not fallos


async def probar_reproductor(ev, fallos):
    """La barra de arriba (19-11-2026): ir a un compás, ⏮ ⏭ (parado y sonando), teclas ← → R, repetir de N a M,
    que el bucle vuelva al principio del trozo y que ir fuera del trozo deje de repetir."""
    nc = await ev("NC")
    if not nc or nc < 12: fallos.append(f"reproductor: pocos compases ({nc})"); return
    # sin vídeo: con el vídeo a la vista las flechas son de fotograma (moviola, se prueba en probar_video)
    await ev("typeof ponVideo==='function' && hayV() && ponVideo(false); 1")
    def mal(txt): fallos.append("reproductor: " + txt)
    tecla = lambda code, shift=False: ev(f"document.dispatchEvent(new KeyboardEvent('keydown',{{code:'{code}',shiftKey:{str(shift).lower()},bubbles:true}})); 1")
    # ir a un compás escribiéndolo
    await ev("$('ir_compas').value=10; $('ir_compas').onchange(); 1"); await asyncio.sleep(0.2)
    r = await ev("[compasDe(cursor), Math.abs(cursor-inicioCompas(10)), (()=>{const [a,b]=ventana(); return cursor>=a&&cursor<b})()]")
    if r[0] != 10 or r[1] > 0.01: mal(f"ir al compás 10 deja en {r}")
    if not r[2]: mal("ir al compás 10: la lupa no lo enseña")
    # ⏭ ⏮ parado
    await ev("$('compas_mas').click(); 1"); a = await ev("compasDe(cursor)")
    await ev("$('compas_menos').click(); 1"); b = await ev("compasDe(cursor)")
    await tecla("ArrowRight"); c = await ev("compasDe(cursor)")
    await tecla("ArrowLeft"); d = await ev("compasDe(cursor)")
    print(f"reproductor: compás 10 → ⏭ {a} → ⏮ {b} → tecla → {c} → tecla ← {d}")
    if [a, b, c, d] != [11, 10, 11, 10]: mal(f"⏭ ⏮ parado: {[a, b, c, d]} (tocaban 11, 10, 11, 10)")
    v0 = await ev("vIni"); await tecla("ArrowRight", True); v1 = await ev("vIni"); e = await ev("compasDe(cursor)")
    if not v1 > v0 or e != 10: mal("Mayús + → debería mover la lupa y no lo que suena")
    # ⏭ sonando: sigue sonando, un compás más allá
    await ev("escuchar(inicioCompas(10)).then(()=>1)"); await asyncio.sleep(0.5)
    await ev("$('compas_mas').click(); 1"); await asyncio.sleep(0.6)
    r = await ev("[!!sonando, compasDe(ahora())]")
    print(f"reproductor: sonando en el 10, ⏭ → suena el {r[1]}")
    if r != [True, 11]: mal(f"⏭ sonando: {r} (tocaba seguir sonando en el 11)")
    await asyncio.sleep(0.5)   # ya a la mitad del 11 (más de ~0,9 s dentro): ⏮ vuelve a su principio, no al 10
    await ev("$('compas_menos').click(); 1"); await asyncio.sleep(0.3)
    r = await ev("[!!sonando, compasDe(ahora())]")
    if r != [True, 11]: mal(f"⏮ sonando a mitad de compás: {r} (tocaba volver al principio del 11)")
    # repetir del 5 al 6: el bucle vuelve al 5
    await ev("$('rep_de').value=5; $('rep_a').value=6; $('rep_de').onchange(); 1"); await asyncio.sleep(0.3)
    r = await ev("[$('bucle').checked, Math.abs(sel.a-inicioCompas(5)), Math.abs(sel.b-inicioCompas(7)), compasDe(ahora())]")
    if not r[0] or r[1] > 0.01 or r[2] > 0.01 or r[3] not in (5, 6): mal(f"repetir de 5 a 6: {r}")
    await ev("escuchar(inicioCompas(7)-0.3).then(()=>1)"); await asyncio.sleep(0.9)
    r = await ev("[!!sonando, compasDe(ahora())]")
    print(f"reproductor: repetir de 5 a 6, al pasar el final del 6 suena el {r[1]}")
    if r != [True, 5]: mal(f"el bucle no vuelve al compás 5: {r}")
    await tecla("KeyR"); r1 = await ev("$('bucle').checked"); await tecla("KeyR"); r2 = await ev("$('bucle').checked")
    if r1 or not r2: mal(f"la tecla R no enciende/apaga repetir: {r1}, {r2}")
    # ir fuera del trozo = dejar de repetir
    await ev("$('ir_compas').value=20; $('ir_compas').onchange(); 1"); await asyncio.sleep(0.4)
    r = await ev("[$('bucle').checked, compasDe(ahora()), !!sonando]")
    if r != [False, 20, True]: mal(f"ir al 20 fuera del trozo: {r} (tocaba repetir apagado, sonando en el 20)")
    # elegir el trozo arrastrando (sel) → las casillas «de … a …» lo dicen
    await ev("parar(); sel={a:inicioCompas(12)+0.1, b:inicioCompas(14)-0.1}; pinta(); 1"); await asyncio.sleep(0.3)
    r = await ev("[+$('rep_de').value, +$('rep_a').value]")
    if r != [12, 13]: mal(f"trozo del 12 al 13 elegido arrastrando, las casillas dicen {r}")
    await ev("sel=null; $('bucle').checked=false; cursor=0; ponInfo(0); pinta(); 1")


async def probar_trozo(ev, fallos):
    """«🔁 el trozo» en el menú de compases (23-11-2026): la lupa enseña justo los compases de «repetir de … a …»;
    1/2/4/8 o ◀ ▶ vuelven a lo de siempre."""
    def mal(txt): fallos.append("trozo: " + txt)
    espera = "new Promise(r=>setTimeout(r,80))"
    n = await ev("NC")
    if n < 12: print("trozo: canción corta, no se prueba"); return
    await ev(f"$('rep_de').value=5; $('rep_a').value=10; $('rep_a').onchange(); {espera}.then(()=>1)")
    await ev(f"$('ncomp_rep').click(); {espera}.then(()=>1)")
    r = await ev("(()=>{ const [a,b]=ventana(); return [compasDe(a+0.01), compasDe(b-0.01), $('ncomp_btn').textContent, $('donde').textContent, $('ncomp_rep').classList.contains('on')]; })()")
    print(f"trozo: repetir 5–10 → la lupa enseña {r}")
    if r[:2] != [5, 10] or "5–10" not in r[2] or not r[4]: mal(f"no enseña los compases 5–10: {r}")
    for k in sorted({7, n // 2, n - 38, n - 10}):   # varios sitios de la canción (con «El buey solo» 66–71 empezaba mal)
        if k < 2 or k + 5 > n: continue
        await ev(f"$('rep_de').value={k}; $('rep_a').value={k + 5}; $('rep_a').onchange(); {espera}.then(()=>1)")
        r = await ev("(()=>{ const [a,b]=ventana(); return [compasDe(a+0.01), compasDe(b-0.01)]; })()")
        if r != [k, k + 5]: mal(f"repetir {k}–{k + 5}: la lupa enseña {r}")
    await ev(f"$('rep_de').value=7; $('rep_a').value=12; $('rep_a').onchange(); {espera}.then(()=>1)")
    r = await ev("(()=>{ const [a,b]=ventana(); return [compasDe(a+0.01), compasDe(b-0.01)]; })()")
    if r != [7, 12]: mal(f"al cambiar a 7–12 la lupa no lo sigue: {r}")
    # sonando con «repetir»: al dar la vuelta la lupa sigue en el trozo (fallaba: se iba a 8 compases)
    await ev(f"$('rep_de').value=5; $('rep_a').value=5; $('rep_a').onchange(); {espera}.then(()=>1)")
    await ev("escuchar(sel.a).then(()=>1)")
    vistas = set()
    for _ in range(int((await ev("sel.b - sel.a")) * 2 + 2) * 4):
        await asyncio.sleep(0.25)
        vistas.add(tuple(await ev("(()=>{ const [a,b]=ventana(); return [VREP, compasDe(a+0.01), compasDe(b-0.01)]; })()")))
    await ev("parar(); 1")
    print(f"trozo: sonando y repitiendo el 5, la lupa enseña {sorted(vistas)}")
    if vistas != {(True, 5, 5)}: mal(f"al repetir, la lupa se va del trozo: {sorted(vistas)}")
    await ev(f"$('rep_de').value=7; $('rep_a').value=12; $('rep_a').onchange(); {espera}.then(()=>1)")
    await ev(f"document.querySelector('[data-ncomp=\"2\"]').click(); {espera}.then(()=>1)")
    r = await ev("(()=>{ const [a,b]=ventana(); return [VREP, compasDe(a+0.01), compasDe(b-0.01), $('ncomp_btn').textContent]; })()")
    if r[0] or r[2] - r[1] != 1 or "2 compases" not in r[3]: mal(f"«2» no vuelve a 2 compases: {r}")
    await ev(f"$('ncomp_rep').click(); $('adelante').click(); {espera}.then(()=>1)")
    r = await ev("(()=>{ const [a,b]=ventana(); return [VREP, compasDe(a+0.01)]; })()")
    if r != [False, 8]: mal(f"▶ desde el trozo no sigue desde su principio: {r}")
    await ev("sel=null; $('bucle').checked=false; VREP=false; pinta(); 1")


async def probar_menus(ev, fallos):
    """Encima de la lupa (19-11-2026): «🔔 Comprobar» y «⚙ Ver» se abren y se cierran; clic en el nombre de una fila
    = su menú (🎧 oírla sola, 🔔 clic, ocultar); lo encendido sale en chips que lo apagan."""
    def mal(txt): fallos.append("menús: " + txt)
    alto = await ev("$('cab_lupa').getBoundingClientRect().height")
    print(f"menús: la línea de encima de la lupa mide {alto:.0f} px")
    if alto > 60 and (await ev("innerWidth")) > 1000: mal(f"la cabecera de la lupa mide {alto:.0f} px (más de una línea)")
    r = await ev("""(()=>{ const b=$('m_comprobar').querySelector('.abre'); b.click(); const a=$('m_comprobar').classList.contains('abierto');
      document.body.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true})); return [a, $('m_comprobar').classList.contains('abierto')]; })()""")
    if r != [True, False]: mal(f"«Comprobar» no se abre y cierra: {r}")
    # clic en el nombre de la primera fila con pista
    js_fila = """(f=>{ const k=FV().indexOf(f), m=medidas(), r=cl.getBoundingClientRect();
      const y=r.top+m.ys[k]+m.altos[k]/2;
      cl.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:r.left+20,clientY:y,pointerId:1}));
      return !$('menu_fila').hidden ? [...$('menu_fila').querySelectorAll('button')].map(b=>b.textContent) : null; })"""
    f = await ev("FV().find(f=>PISTA_DE(f) && !SOLO_ONDA.includes(f)) || FV()[0]")
    bot = await ev(f"{js_fila}({f!r})")
    print(f"menús: clic en el nombre «{f}» → {bot}")
    if not bot: mal(f"clic en el nombre de la fila {f} no abre su menú"); return
    if await ev(f"!!PISTA_DE({f!r})"):
        await ev("[...$('menu_fila').querySelectorAll('button')].find(b=>b.textContent.startsWith('🎧')).click(); 1")
        r = await ev(f"[solo, vol.mezcla, vol[PISTA_DE({f!r})], $('activos').textContent, $('menu_fila').hidden]")
        if r[0] != f or r[1] != 0 or r[2] != 1 or "solo" not in r[3] or not r[4]: mal(f"🎧 oír solo {f}: {r}")
        await ev("$('activos').querySelector('button').click(); 1")
        r = await ev("[solo, vol.mezcla]")
        if r != [None, 1]: mal(f"el chip no quita el solo: {r}")
    await ev(f"{js_fila}({f!r})")
    await ev("[...$('menu_fila').querySelectorAll('button')].find(b=>b.textContent.startsWith('🔔')).click(); 1")
    r = await ev(f"[clic[{f!r}], $('activos').textContent]")
    if not r[0] or f not in r[1]: mal(f"🔔 clic en {f}: {r}")
    await ev("$('activos').querySelector('button').click(); 1")
    if await ev(f"clic[{f!r}]"): mal("el chip no quita el clic")
    n0 = await ev("FV().length")
    await ev(f"{js_fila}({f!r})")
    await ev("[...$('menu_fila').querySelectorAll('button')].find(b=>b.textContent.startsWith('ocultar')).click(); 1")
    n1 = await ev("FV().length")
    await ev(f"document.querySelector('[data-fila=\"{f}\"]').click(); 1")
    n2 = await ev("FV().length")
    if [n1, n2] != [n0 - 1, n0]: mal(f"ocultar la fila y volver a enseñarla en ⚙ Ver: {n0} → {n1} → {n2}")


async def probar_video(ev, cdp, fallos):
    """Vídeo de bailarines (19-11-2026, video.py): que cargue, que quepa a la derecha sin montarse con la lupa, que vaya
    con la música parado, al 100 % y al 60 % (±80 ms), el aviso fuera del vídeo, el cuadrador ⚓ y las filas «👣»."""
    if not await ev("hayV()"):
        if not await ev("$('panel_video').hidden"):
            fallos.append("sin vídeo, pero se ve el botón o el panel del vídeo")
        return
    def mal(t): fallos.append("vídeo: " + t)
    await cdp("Emulation.setDeviceMetricsOverride", width=1900, height=950, deviceScaleFactor=1, mobile=False)
    await ev("ponVideo(true); 1"); await asyncio.sleep(1.0)
    for _ in range(60):
        if await ev("$('video').readyState>=2"): break
        await asyncio.sleep(0.25)
    else:
        mal("no carga: " + str(await ev("[$('video').src, $('video').error && $('video').error.code]"))); return
    geo = await ev("(()=>{const v=$('video').getBoundingClientRect(), l=$('lupa').getBoundingClientRect(); return [Math.round(v.left), Math.round(v.width), Math.round(v.height), Math.round(v.bottom), Math.round(l.right), innerHeight]})()")
    print("vídeo [izq, ancho, alto, abajo, fin de la lupa, alto pantalla]:", geo)
    if geo[1] < 200 or geo[3] > geo[5] + 2: mal(f"tamaño raro o no cabe en la pantalla: {geo}")
    if geo[4] > geo[0]: mal(f"la lupa se monta con el vídeo: {geo}")
    await ev("ir(vidIni()+5); 1"); await asyncio.sleep(1.0)
    r = await ev("[$('video').currentTime, (ahora()-vidIni())/VV().velocidad]")
    if abs(r[0] - r[1]) > 0.05: mal(f"parado no va a su fotograma: {r}")
    for vel in (1, 0.6):
        await ev(f"document.querySelector('[data-vel=\"{vel}\"]').click(); ir(vidIni()+2); escuchar(vidIni()+2).then(()=>1)")
        await asyncio.sleep(1.5)
        ds = []
        for _ in range(8):
            r = await ev("[$('video').currentTime, (ahora()-vidIni())/VV().velocidad, $('video').paused]")
            if r[2]: ds.append(9.0)
            else: ds.append(r[0] - r[1])
            await asyncio.sleep(0.3)
        await ev("parar(); 1")
        peor = max(abs(d) for d in ds)
        print(f"vídeo al {vel:.0%}: se separa de la música como mucho {peor * 1000:.0f} ms")
        if peor > 0.08: mal(f"al {vel:.0%} se separa {peor * 1000:.0f} ms de la música ({[round(d, 3) for d in ds]})")
    await ev("document.querySelector('[data-vel=\"1\"]').click(); 1")
    await ev("ir(Math.max(0, vidIni()-8)); 1"); await asyncio.sleep(0.3)
    if vidini := await ev("vidIni()"):
        if vidini > 8.5 and not await ev("$('video_fuera').textContent.includes('empieza')"): mal("antes del vídeo no avisa de dónde empieza")
    a = await ev("vidIni()")
    await ev("document.querySelector('[data-vmueve=\"0.05\"]').click(); document.querySelector('[data-vmueve=\"1f\"]').click(); 1")
    b = await ev("[vidIni(), $('video_txt').textContent, 1/VV().fps*VV().velocidad]")
    if abs(b[0] - a - 0.05 - b[2]) > 0.002 or "VIDEO" not in b[1]: mal(f"⚓ +50 ms +1 fot. no va: {a} → {b}")
    await ev("$('video_maquina').click(); 1")
    if abs(await ev("vidIni()") - a) > 0.001: mal("↺ no vuelve al cuadre de la máquina")
    n = await ev("Object.keys(PIS_F).filter(f=>FUENTES.includes(f)).length")
    if n != await ev("VV().bailarines.length"): mal(f"faltan filas de pisadas: {n}")
    # marcar pisadas en la página, deshacer, fotograma a fotograma, sonido del vídeo (19-11-2026)
    r = await ev("""(async()=>{ ponMarcar(true); ir(vidIni()+3); await new Promise(r=>setTimeout(r,300));
      const n0=VV().pisadas.length, t0=ahora();
      document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyQ',bubbles:true})); const n1=VV().pisadas.length;
      const txt=textoPisadas();
      document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyZ',bubbles:true})); const n2=VV().pisadas.length;
      document.dispatchEvent(new KeyboardEvent('keydown',{code:'Period',bubbles:true})); const paso=ahora()-t0;
      $('sonido_video').click(); const mudo=$('video').muted; $('sonido_video').click();
      ponMarcar(false); localStorage.removeItem(CLAVE_PIS(VV().id));
      return [n0, n1, n2, txt.startsWith('PISADAS') && txt.split('\\n').length===n1+1, +(paso*VV().fps/VV().velocidad).toFixed(2), mudo, $('video').muted]; })()""")
    print("marcar pisadas [antes, con Q, tras Z, texto, fotogramas con «.», mudo con 🔊, mudo sin 🔊]:", r)
    # marcando (20-11-2026): botones a la IZQUIERDA del vídeo, vídeo casi al alto de la pantalla, Tab y E
    g = await ev("""(async()=>{ ponMarcar(true); ir(vidIni()+3); await new Promise(r=>setTimeout(r,400));
      const v=$('video').getBoundingClientRect(), c=$('caja_marcar').getBoundingClientRect(), l=$('lupa').getBoundingClientRect();
      const V=VV(), q=V.pisadas.find(p=>p[4]||p[5]), guarda=q&&[q[4],q[5]]; if(q){q[4]=0;q[5]=0;}
      soltarPis(); ir(Math.max(0,(q?q[0]:0)+(vDes[V.id]||0)-1));
      document.dispatchEvent(new KeyboardEvent('keydown',{code:'Tab',bubbles:true})); const tab=!q||selPis===q;
      if(q){q[4]=guarda[0];q[5]=guarda[1];} soltarPis();
      const e0=$('ver_estrellas').checked; document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyE',bubbles:true}));
      const e1=$('ver_estrellas').checked; document.dispatchEvent(new KeyboardEvent('keydown',{code:'KeyE',bubbles:true}));
      return [Math.round(c.right)<=Math.round(v.left)+1, Math.round(v.height), innerHeight, Math.round(l.right)<=Math.round(c.left)+1, tab, e0!==e1, $('ver_estrellas').checked===e0]; })()""")
    print("marcando [botones a la izquierda, alto del vídeo, alto pantalla, lupa no se monta, Tab elige la sin sitio, E apaga, E enciende]:", g)
    if not (g[0] and g[3] and g[4] and g[5] and g[6]) or g[1] < 0.72 * g[2]: mal(f"marcando: {g}")
    # marcando, en el vídeo solo la elegida y la anterior de su mismo pie (20-11-2026); «ver todas las marcas» = todas
    g = await ev("""(()=>{ const V=VV(), q=V.pisadas.filter(p=>p[4]||p[5])[5]; if(!q) return 'pocas';
      eligePis(q); const a=arosVisibles(V); a.forEach(p=>delete p.tenue);
      $('ver_todos_aros').checked=true; const n=arosVisibles(V).length; $('ver_todos_aros').checked=false; soltarPis();
      return [a.length<=2 && a.includes(q), a.every(p=>p[1]===q[1] && p[2]===q[2]), n===V.pisadas.length]; })()""")
    print("marcando, marcas en el vídeo [solo la elegida (+ anterior), mismo bailarín y pie, «ver todas» = todas]:", g)
    if g != "pocas" and g != [True, True, True]: mal(f"marcas al marcar: {g}")
    if FOTO_MARCAR:
        await ev("(()=>{ const V=VV(), q=V.pisadas.find(p=>p[4]||p[5]); if(q) eligePis(q); const r=$('video').getBoundingClientRect();"
                 " if(q){ ratonV=[q[4]*r.width/V.ancho+6, q[5]*r.height/V.alto-4]; } estrellasVideo(); return 1; })()")
        await asyncio.sleep(0.6)
        import base64
        img = await cdp("Page.captureScreenshot", format="png")
        open(FOTO_MARCAR, "wb").write(base64.b64decode(img["data"])); print("foto marcando:", FOTO_MARCAR)
        await ev("ratonV=null; soltarPis(); 1")
    await ev("ponMarcar(false); 1")
    if FOTO_ONDAS:   # foto del vídeo justo después de una pisada (las ondas en los pies al sonar)
        await ev("(()=>{ const V=VV(), q=V.pisadas.filter(p=>p[4]||p[5])[4]; ir(q[0]+(vDes[V.id]||0)+0.08); return 1; })()")
        await asyncio.sleep(0.8); await ev("estrellasVideo(); 1")
        import base64
        img = await cdp("Page.captureScreenshot", format="png")
        open(FOTO_ONDAS, "wb").write(base64.b64decode(img["data"])); print("foto ondas:", FOTO_ONDAS)
    # moviola (20-11-2026): con vídeo, ← → = 1 fotograma, Mayús = ¼ de tiempo, Ctrl = compás; espacio sigue donde paró
    g = await ev("""(()=>{ const V=VV(), k=(code,o)=>document.dispatchEvent(new KeyboardEvent('keydown',Object.assign({code,bubbles:true},o||{})));
      soltarPis(); const i=P.findIndex(p=>p.seg>vidIni()+4); ir(P[i].seg+0.01); const t0=ahora();
      k('ArrowRight'); const fot=Math.round((ahora()-t0)*V.fps/V.velocidad);
      ir(P[i].seg+0.01); k('ArrowRight',{shiftKey:true}); const cuarto=+((ahora()-P[i].seg)/(P[i+1].seg-P[i].seg)).toFixed(2);
      k('ArrowRight',{ctrlKey:true}); const compas=unos.some(u=>Math.abs(u-ahora())<0.002);
      sel={a:P[i].seg, b:P[i+8].seg}; cursor=P[i+3].seg+0.02; const sigue=Math.abs(desdeDonde()-cursor)<1e-6;
      cursor=P[i+9].seg; const fuera=desdeDonde()===sel.a; sel=null;
      return [fot, cuarto, compas, sigue, fuera]; })()""")
    g2 = await ev("""(async()=>{ ponMarcar(true); ratonV=[50,50]; await new Promise(r=>setTimeout(r,200)); lupaPie(); const antes=($('lupa_pie').offsetWidth>0);
      await escuchar(vidIni()+3); await new Promise(r=>setTimeout(r,400)); const sonandoSeVe=($('lupa_pie').offsetWidth>0); parar(); ratonV=null; lupaPie(); ponMarcar(false);
      ponMarcar(true); ratonV=[50,50]; lupaPie(); const puesta=($('lupa_pie').offsetWidth>0);
      const lc=$('lupa_pie'), Lw=lc.offsetWidth, tapa=lc.offsetLeft<50 && lc.offsetTop<50; window.__lupa=[Lw, tapa, zoomLupa];
      $('video').dispatchEvent(new WheelEvent('wheel',{deltaY:-100,cancelable:true})); window.__lupa.push(+zoomLupa.toFixed(2));
      $('video').dispatchEvent(new WheelEvent('wheel',{deltaY:100,cancelable:true}));
      document.body.dispatchEvent(new PointerEvent('pointermove',{bubbles:true})); const fuera=($('lupa_pie').offsetWidth>0); ponMarcar(false);
      return [antes, sonandoSeVe, puesta, fuera]; })()""")
    print("lupa del pie [se ve parado, se ve sonando, puesta otra vez, con el ratón fuera]:", g2)
    if g2 != [True, False, True, False]: mal(f"la lupa del pie se queda al escuchar: {g2}")
    lu = await ev("window.__lupa")
    print("lupa grande [ancho px, tapa el ratón, aumento, con la rueda]:", lu)
    if lu[0] < 200 or lu[1] or lu[3] <= lu[2]: mal(f"lupa del pie pequeña o encima del ratón: {lu}")
    print("moviola [→ fotogramas, Mayús+→ parte del tiempo, Ctrl+→ al 1, espacio sigue donde paró, fuera del trozo vuelve]:", g)
    if g != [1, 0.25, True, True, True]: mal(f"moviola: {g}")
    if r[1] != r[0] + 1 or r[2] != r[0] or not r[3]: mal(f"marcar pisadas con Q / deshacer con Z: {r}")
    if abs(r[4] - 1) > 0.05: mal(f"«.» no avanza un fotograma: {r[4]}")
    if r[5] or not r[6]: mal(f"🔊 sonido del vídeo no va: {r}")
    # elegir una pisada tocándola, moverla un fotograma, imantarla al tiempo, borrarla y deshacer (19-11-2026)
    r = await ev("""(async()=>{ const V=VV(); if(!V.pisadas.length) return 'sin pisadas';
      const q=V.pisadas[Math.min(3,V.pisadas.length-1)], dd=vDes[V.id]||0, t0=q[0];
      vIni=unos.filter(u=>u<=q[0]+dd+0.01).pop(); pinta(); await new Promise(r=>setTimeout(r,300));
      const m=medidas(), r=cl.getBoundingClientRect(), [a,b]=ventana(), f=FV().indexOf(FUENTES.find(x=>PIS_F[x]===V.bailarines[q[1]].nombre));
      const X0=m.izq+m.pad, X1=r.width-m.der, x=r.left+X0+(q[0]+dd-a)/(b-a)*(X1-X0), y=r.top+m.ys[f]+m.altos[f]*(q[2]==='I'?0.3:0.7);
      cl.dispatchEvent(new PointerEvent('pointerdown',{bubbles:true,clientX:x,clientY:y,pointerId:7}));
      cl.dispatchEvent(new PointerEvent('pointerup',{bubbles:true,clientX:x,clientY:y,pointerId:7}));
      const elegida=selPis===q, barra=!$('pis_sel').hidden, n=V.pisadas.length;
      document.querySelector('[data-pmueve="1"]').click();
      const paso=Math.round((q[0]-t0)*V.fps/V.velocidad);
      document.querySelector('[data-piman="1"]').click(); const enTiempo=P.some(p=>Math.abs(p.seg-(q[0]+dd))<0.002);
      document.dispatchEvent(new KeyboardEvent('keydown',{code:'Delete',bubbles:true})); const borrada=!V.pisadas.includes(q);
      deshazPis(); deshazPis(); deshazPis(); const vuelta=V.pisadas.includes(q) && Math.abs(q[0]-t0)<0.001 && V.pisadas.length===n;
      soltarPis(); localStorage.removeItem(CLAVE_PIS(V.id));
      return [elegida, barra, paso, enTiempo, borrada, vuelta]; })()""")
    print("pisada elegida [tocada, barrita, ▶ 1 fot., 🧲 al tiempo, Supr borra, Z ×3 la devuelve]:", r)
    if r != 'sin pisadas' and r != [True, True, 1, True, True, True]: mal(f"retocar una pisada: {r}")   # sin pisadas: no se prueba
    # marcar como Edmundo (23-11-2026): fotograma con → , pie, clic en el vídeo; → otra vez y otro pie. Antes: la nueva
    # no quedaba elegida (el clic movía la anterior), → movía la pisada elegida, el imán la corría y sonando no se veían
    r = await ev("""(async()=>{ const V=VV(), dd=vDes[V.id]||0, guarda=V.pisadas.map(q=>q.slice()), fot=V.velocidad/V.fps;
      const k=code=>document.dispatchEvent(new KeyboardEvent('keydown',{code,bubbles:true})), espera=ms=>new Promise(r=>setTimeout(r,ms));
      const clic=(fx,fy)=>{ const r=$('video').getBoundingClientRect(); $('video').dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:r.left+r.width*fx,clientY:r.top+r.height*fy})); };
      ponMarcar(true); soltarPis(); const i=P.findIndex(p=>p.seg>vidIni()+5); ir(P[i].seg+0.09); await espera(300);
      k('KeyQ'); const p1=selPis, t1=ahora(); const nueva=!!p1 && !guarda.some(q=>q[0]===p1[0]&&q[1]===p1[1]&&q[2]===p1[2]);
      const sinIman=p1 ? Math.abs(p1[0]+dd-t1)<fot : false;
      clic(0.25,0.75); const sitio1=p1 && Math.abs(p1[4]-V.ancho*0.25)<V.ancho*0.01;
      for(let j=0;j<5;j++) k('ArrowRight'); await espera(100);
      const vidSeMueve=Math.round((ahora()-t1)/fot), p1quieta=p1 && Math.abs(p1[0]+dd-t1)<fot, suelta=selPis===null;
      k('KeyO'); const p2=selPis; clic(0.6,0.4);
      const sitio2=p2 && p2!==p1 && Math.abs(p2[4]-V.ancho*0.6)<V.ancho*0.01, p1igual=p1 && Math.abs(p1[4]-V.ancho*0.25)<V.ancho*0.01;
      // sonando, también marcando, se dibujan todas las marcas
      const o=ondaPie; let n=0; ondaPie=(...a)=>{ n++; return o(...a); };
      soltarPis(); await escuchar(p1[0]+dd-0.05); await espera(150); estrellasVideo(); parar(); ondaPie=o;
      V.pisadas=guarda; localStorage.removeItem(CLAVE_PIS(V.id)); soltarPis(); ponMarcar(false);
      return [nueva, sinIman, sitio1, vidSeMueve, p1quieta, suelta, sitio2, p1igual, n>0]; })()""")
    print("marcar como Edmundo [la nueva elegida, sin imán parado, clic = su sitio, → mueve el vídeo, la pisada quieta, se suelta, la 2.ª su sitio, la 1.ª igual, sonando se ven]:", r)
    if r != [True, True, True, 5, True, True, True, True, True]: mal(f"marcar como Edmundo: {r}")
    # con una pisada elegida, el clic en el vídeo le pone el sitio a ELLA, aunque otra esté más cerca (20-11-2026)
    r = await ev("""(()=>{ const V=VV(); if(V.pisadas.length<2) return 'pocas pisadas';
      const q=V.pisadas.find(p=>p[1]===1)||V.pisadas[1], otra=V.pisadas.find(p=>p!==q), dd=vDes[V.id]||0;
      const guarda=[q[4],q[5],otra[4],otra[5]], u=ultimaPis; ultimaPis=otra; eligePis(q);
      vIni=q[0]+dd; pinta();   // en el fotograma de la elegida (irse a más de 2 fotogramas la suelta, a propósito)
      const r=$('video').getBoundingClientRect();
      $('video').dispatchEvent(new MouseEvent('click',{bubbles:true,clientX:r.left+r.width*0.25,clientY:r.top+r.height*0.75}));
      const tol=Math.max(3, 1.5*V.ancho/r.width);   // un píxel de pantalla = varios del vídeo (4K: 5)
      const ok=[Math.abs(q[4]-V.ancho*0.25)<tol && Math.abs(q[5]-V.alto*0.75)<tol, otra[4]===guarda[2] && otra[5]===guarda[3]];
      q[4]=guarda[0]; q[5]=guarda[1]; ultimaPis=u; soltarPis(); localStorage.removeItem(CLAVE_PIS(V.id)); return ok; })()""")
    print("clic en el vídeo con una pisada elegida [se mueve la elegida, la otra quieta]:", r)
    if r != "pocas pisadas" and r != [True, True]: mal(f"el clic en el vídeo no va a la pisada elegida: {r}")
    await ev("$('video_cerrar').click(); 1")
    if not await ev("$('panel_video').hidden"): mal("✕ no lo oculta")
    await ev("$('ver_video').click(); 1")
    if await ev("$('panel_video').hidden"): mal("«🎬 Vídeo» no lo enseña")
    await cdp("Emulation.clearDeviceMetricsOverride")
    await ev("window.dispatchEvent(new Event('resize')); 1"); await asyncio.sleep(0.5)


async def probar_extras(ev, cdp, url, fallos):
    """Marcas con texto, cuenta de entrada y recordar dónde se quedó (también con ?compas=N) (19-11-2026)."""
    def mal(t): fallos.append(t)
    r = await ev("""(()=>{ ponMarca(30, 'prueba'); const a=[MARCAS.length, $('marcas_txt').textContent]; MARCAS.length=0; guardaMarcas(); return [...a, MARCAS.length]; })()""")
    if r[0] != 1 or "30.000=prueba" not in r[1] or r[2] != 0: mal(f"marcas: {r}")
    await ev("$('cuenta').checked=true; escucharConCuenta(20); 1")
    await asyncio.sleep(0.3)
    a = await ev("[$('play').textContent, !!sonando]")
    await asyncio.sleep(60 / BPM * 4 + 0.8)
    b = await ev("[!!sonando, ahora()]")
    await ev("parar(); $('cuenta').checked=false; 1")
    print(f"cuenta de entrada: {a} → {b}")
    if "1" not in a[0] or a[1] or not b[0] or b[1] < 20: mal(f"cuenta de entrada: {a} → {b}")
    # comparar con otra grabación: fila cuadrada compás a compás, oírla, quitarla
    r = await ev("""(async()=>{ const otra=(RITMO_LISTA.find(x=>x.c!==CANCION)||{}).c; await ponComparar(otra);
      if (!CMP) return null; const t=inicioCompas(5)+0.1, tB=aComparada(t);
      const r=[FUENTES.includes(CMP.f), tB, CMP.ix['5|1']!==undefined ? CMP.PB[CMP.ix['5|1']].seg : null];
      await oirComparada(); r.push(!!CMP.src); parar(); r.push(!!CMP.src); quitaComparar(); r.push(!!CMP); return r; })()""")
    print("comparar [fila, compás 5 allí, su 1 del compás 5, suena, para, quitada]:", r)
    if not r or not r[0] or r[1] is None or abs(r[1] - r[2]) > 0.6 or not r[3] or r[4] or r[5]: mal(f"comparar: {r}")
    await ev("ir(40); 1"); await asyncio.sleep(0.8)
    for u, esperado in ((url, "40"), (url + "&compas=10", "inicioCompas(10)")):
        await cdp("Page.navigate", url=u)
        for _ in range(100):
            if await ev("document.readyState==='complete' && !!document.getElementById('play')"): break
            await asyncio.sleep(0.2)
        await asyncio.sleep(1.2)
        r = await ev(f"[cursor, {esperado}]")
        if not r or abs(r[0] - r[1]) > 0.1: mal(f"al volver a la página no recuerda dónde iba ({u[-12:]}): {r}")



async def probar_estrellas(ev, fallos):
    """23-11-2026 (Edmundo: «las dos últimas pisadas de Amelia no se ven en el vídeo»): cada pisada con sitio tiene que
    dar un destello en el lienzo del vídeo, PARADO justo después de ella y SONANDO al 50 %. Si el vídeo no tiene pisadas
    con sitio, se ponen 6 seguidas (cada 0,25 s) en el centro para probar. Mide píxeles pintados alrededor del pie."""
    if not await ev("(typeof VV==='function') && !!VV() && !!document.getElementById('estrellas')"):
        return
    def mal(t): fallos.append("estrellas: " + t)
    await ev("""(()=>{ if($('panel_video').hidden && $('boton_video')) $('boton_video').click(); window.__pisGuarda=VV().pisadas.map(q=>q.slice());
      const V=VV(); if(!V.pisadas.some(q=>q[4]||q[5])){ const t0=(V.inicio||0)+V.dur*0.5*V.velocidad;
        for(let i=0;i<6;i++) V.pisadas.push([t0+0.25*i, i%2, i%2?'D':'I', 'p', V.ancho*(0.4+0.04*i), V.alto*0.85]); }
      return 1; })()""")
    # parado, justo después de cada pisada
    r = await ev("""(()=>{ const V=VV(), dd=vDes[V.id]||0, c=$('estrellas'), v=$('video');
      const out=[]; const qs=V.pisadas.filter(q=>q[4]||q[5]);
      for(const q of qs){ ir(q[0]+dd+0.05); estrellasVideo();
        const k=c.width/v.clientWidth, x=Math.round(q[4]*v.clientWidth/V.ancho*k), y=Math.round(q[5]*v.clientHeight/V.alto*k);
        const r=Math.round(10*k), d=c.getContext('2d').getImageData(Math.max(0,x-r),Math.max(0,y-r),2*r,2*r).data;
        let n=0; for(let i=3;i<d.length;i+=4) if(d[i]>40) n++; out.push(n); }
      return out; })()""")
    if not r:
        mal("no hay pisadas con sitio")
    elif min(r) == 0:
        mal(f"parado, hay pisadas sin destello (píxeles por pisada): {r}")
    print(f"estrellas: parado, píxeles pintados en cada pisada ({len(r)}): mín {min(r) if r else 0} · máx {max(r) if r else 0}")
    # sonando al 50 %: las 3 últimas pisadas con sitio
    r2 = await ev("""(async()=>{ const V=VV(), dd=vDes[V.id]||0, c=$('estrellas'), v=$('video');
      const qs=V.pisadas.filter(q=>q[4]||q[5]).sort((a,b)=>a[0]-b[0]).slice(-3); if(!qs.length) return [];
      const vista=qs.map(()=>0); ponVel(0.5); await escuchar(qs[0][0]+dd-0.4);
      const fin=performance.now()+((qs[qs.length-1][0]-qs[0][0])+1.2)/0.5*1000;
      while(performance.now()<fin){ await new Promise(r=>requestAnimationFrame(r));
        const k=c.width/v.clientWidth, g=c.getContext('2d');
        qs.forEach((q,i)=>{ const x=Math.round(q[4]*v.clientWidth/V.ancho*k), y=Math.round(q[5]*v.clientHeight/V.alto*k);
          const a=g.getImageData(x,y,1,1).data[3]; if(a>vista[i]) vista[i]=a; }); }
      parar(); ponVel(1); return vista; })()""")
    if r2 and min(r2) < 100:
        mal(f"sonando al 50 %, alguna de las últimas pisadas no se ve (opacidad máxima en el pie, 0–255): {r2}")
    print(f"estrellas: sonando al 50 %, opacidad máxima en el pie de las 3 últimas: {r2}")
    await ev("VV().pisadas=window.__pisGuarda; estrellasVideo(); 1")

async def probar_subir(ev, cdp, url, fallos):
    """Subir un vídeo desde la página (19-11-2026): que lo cuadre solo, que se guarde al recargar y que se pueda quitar."""
    def mal(t): fallos.append("subir vídeo: " + t)
    src = pathlib.Path(SUBIR[0]).as_uri()
    t0 = time.time()
    r = await ev(f"""(async()=>{{ window.__sinPreguntar=true; const b=await (await fetch({json.dumps(src)})).blob();
        const r=await anadeVideo(new File([b], 'prueba.mp4', {{type:'video/mp4'}})); return [r, VD.length, !!(VV()&&VV().subido), verVideo]; }})()""")
    print(f"subir vídeo: {r} ({time.time() - t0:.1f} s)")
    if not r or not r[0]: mal(f"no lo pone: {r}"); return
    if SUBIR[1] is not None and abs(r[0]["inicio"] - SUBIR[1]) > 0.04: mal(f"lo cuadra en {r[0]['inicio']} s y tocaba {SUBIR[1]}")
    if not (r[2] and r[3]): mal(f"no se ve después de subirlo: {r}")
    await cdp("Page.navigate", url=url)
    for _ in range(100):
        if await ev("document.readyState==='complete' && !!document.getElementById('play')"): break
        await asyncio.sleep(0.2)
    await asyncio.sleep(2.0)
    n = await ev("VD.filter(v=>v.subido).length")
    if n != 1: mal(f"al recargar no está guardado (subidos: {n})"); return
    await ev("VI=VD.findIndex(v=>v.subido); window.confirm=()=>true; quitaVideo().then(()=>1)")
    await asyncio.sleep(0.5)
    n2 = await ev("(async()=>{const r=await bdVideos('leer'); return [VD.filter(v=>v.subido).length, r.length]})()")
    if n2 != [0, 0]: mal(f"🗑 no lo quita: {n2}")


async def probar_vistas(ev, cdp, fallos):
    """«Ver: Lupa / Partitura / Las dos» (19-11-2026): qué se esconde y que con «Las dos» quepa en la pantalla
    (en una pantalla como la de Edmundo, 1900 × 950)."""
    await cdp("Emulation.setDeviceMetricsOverride", width=1900, height=950, deviceScaleFactor=1, mobile=False)
    await ev("window.dispatchEvent(new Event('resize')); 1"); await asyncio.sleep(0.8)
    r = {}
    for v in ("lupa", "partitura", "dos"):
        await ev(f"ponVista('{v}'); 1"); await asyncio.sleep(0.6)
        r[v] = await ev("""[$('panel_lupa').hidden, $('panel_partitura').hidden, $('panel_partitura').open,
          Math.round($('partitura').getBoundingClientRect().bottom), innerHeight]""")
    print(f"vistas: {r}")
    if r["lupa"][:2] != [False, True]: fallos.append(f"vista «Lupa»: {r['lupa']}")
    if r["partitura"][:3] != [True, False, True]: fallos.append(f"vista «Partitura»: {r['partitura']}")
    if r["dos"][:3] != [False, False, True]: fallos.append(f"vista «Las dos»: {r['dos']}")
    elif r["dos"][3] > r["dos"][4] + 2: fallos.append(f"«Las dos» no cabe en la pantalla: la partitura acaba en {r['dos'][3]} y la pantalla mide {r['dos'][4]}")
    await cdp("Emulation.clearDeviceMetricsOverride")
    await ev("window.dispatchEvent(new Event('resize')); 1"); await asyncio.sleep(0.5)


async def probar_golpes_partitura(ev, fallos):
    """Filas «♪ …» de la lupa (golpes de la partitura, 23-11-2026): cada golpe cae dentro de su compás cuadrado,
    tantos golpes como notas no ligadas (los acordes, uno), van con las anclas y suenan con 🔔."""
    r = await ev("""(()=>{ const out=[]; for (const f of PT_FILAS) { const gs=golpesP(f,-1,1e9);
        const malos=gs.filter(q=>!(q[0]>=TP[q[5]]-0.002 && q[0]<TP[q[5]+1]+0.002)).length;
        const onsets=new Set(PTF[f].notas.map(n=>n[0]+':'+n[1].toFixed(4))).size;
        out.push([f, gs.length, onsets, malos, PTF[f].notas.length]); } return out; })()""")
    if not r: fallos.append("hay partitura pero ninguna fila «♪» de golpes en la lupa"); return
    for f, n, ons, malos, notas in r:
        print(f"golpes de la partitura: fila «{f}» · {n} golpes ({notas} notas sin contar ligadas) · fuera de su compás: {malos}")
        if n == 0: fallos.append(f"«{f}»: sin golpes")
        if malos: fallos.append(f"«{f}»: {malos} golpes fuera de su compás")
        if n > ons: fallos.append(f"«{f}»: {n} golpes y solo {ons} sitios distintos")
    f = r[0][0]
    # mover un ancla mueve los golpes de ese compás lo mismo (y se deja como estaba)
    d = await ev(f"""(()=>{{ const f={json.dumps(f)}, gs=golpesP(f,-1,1e9), q=gs.find(x=>x[5]>0) || gs[0], k=q[5];
        const antes=JSON.stringify(anclas), t0=q[0]; anclas={{}}; anclas[k]=TP[k]+0.25; rehazTiempos();
        const t1=golpesP(f,-1,1e9).find(x=>x[5]===k && Math.abs(x[6]-q[6])<1e-6)[0];
        anclas=JSON.parse(antes); rehazTiempos(); return t1-t0; }})()""")
    print(f"golpes de la partitura: un ancla +0,25 s mueve los golpes de su compás {d:+.3f} s")
    if d is None or abs(d - 0.25) > 0.01: fallos.append(f"los golpes no siguen a las anclas: {d}")
    # 🔔 clic en lo escrito: un clic por golpe en el trozo que suena
    c = await ev(f"""(async()=>{{ const f={json.dumps(f)}; for (const k in clic) clic[k]=false; clic[f]=true; parar(); const a=TP[0], b=TP[TP.length-1];
        sel={{a,b}}; $('bucle').checked=true; await escuchar(a);
        const n=sonando.cl.length, esp=golpesP(f,a,b).filter(q=>q[0]>=a && q[0]<b).length;
        parar(); clic[f]=false; sel=null; $('bucle').checked=false; cambiaClics(); return [n, esp]; }})()""")
    print(f"golpes de la partitura: 🔔 {c[0]} clics programados, {c[1]} golpes en el trozo")
    if not c or c[0] != c[1]: fallos.append(f"clic en lo escrito: {c}")


async def probar_partitura(ev, fallos):
    """El panel «Partitura»: se dibuja, marca el compás que suena (a 100 % y a 60 %), clic en un compás, bucle,
    elegir partes, anclas y ← →."""
    await probar_golpes_partitura(ev, fallos)
    # la página la prepara sola de antemano (sin sonar): esperar a que esté y medir lo que tarda en ABRIRSE el panel
    for _ in range(300):
        if await ev("window.__partituraLista===true"): break
        await asyncio.sleep(0.2)
    abrir = await ev("new Promise(r=>{const t=performance.now(); $('panel_partitura').open=true; requestAnimationFrame(()=>requestAnimationFrame(()=>r(performance.now()-t)))})")
    for _ in range(300):
        if await ev("window.__partituraLista===true"): break
        await asyncio.sleep(0.2)
    else:
        fallos.append("la partitura no se dibuja: " + str(await ev("$('partitura').innerText.slice(0,200)"))); return
    piezas = await ev("document.querySelectorAll('#partitura *').length")
    print(f"partitura: abrir el panel {abrir / 1000:.1f} s · {piezas} piezas de SVG en la página")
    if abrir > 5000: fallos.append(f"abrir el panel de la partitura tarda {abrir / 1000:.1f} s")
    n = await ev("[svgMedidas.length, PARTITURA.compases.length]")
    ms = await ev("window.__partituraMs")
    print(f"partitura: {n[0]} compases dibujados · {n[1]} en el cuadre · leer {ms[0] / 1000:.1f} s, dibujar {ms[1] / 1000:.1f} s")
    if n[0] != n[1]: fallos.append(f"compases dibujados {n[0]} ≠ cuadre {n[1]}")
    # ¿los compases dibujados van en el mismo orden que el archivo? (notas por compás; 19-11-2026: Verovio desordenaba
    # «El Huracán» por unas casillas de repetición mal cerradas)
    orden = await ev("""(()=>{ const doc=new DOMParser().parseFromString(xmlConPartes(),'application/xml');
      const ps=[...doc.querySelectorAll('part')], r=[];
      for (let i=0;i<nMedidas;i++){ let x=0; ps.forEach(p=>{const m=p.querySelectorAll(':scope > measure')[i];
        if(m) x+=[...m.querySelectorAll('note')].filter(q=>!q.querySelector('rest')).length;});
        const g=medida(i); r.push([x, g ? g.querySelectorAll('g.note').length : 0]); }
      return r; })()""")
    malos = [i + 1 for i, (x, s) in enumerate(orden or []) if abs(x - s) > max(3, 0.25 * x)]
    print(f"partitura: compases dibujados en otro orden que el archivo: {len(malos)}" + (f" (p. ej. {malos[:8]})" if malos else ""))
    if len(malos) > 0.1 * len(orden or [1]): fallos.append(f"Verovio desordena los compases: {malos[:10]}")
    k = min(20, n[1] - 3)

    async def marcado_en():
        return await ev("(()=>{const r=document.querySelector('#partitura rect.marca');return [compasPartitura(ahora()), r?svgMedidas.indexOf(r.parentNode):-1]})()")
    for vel in ("1", "0.6"):
        await ev(f"document.querySelector('[data-vel=\"{vel}\"]').click(); escuchar(TP[{k}]+0.15).then(()=>1)")
        await asyncio.sleep(1.5)
        a = await marcado_en()
        await ev("parar(); 1")
        if a[0] < k or a[0] > k + 2 or a[0] != a[1]:
            fallos.append(f"al {float(vel):.0%} el compás que suena es {a[0]} y se marca {a[1]} (empezó en {k})")
        else:
            print(f"al {float(vel):.0%}: suena y se marca el compás {a[0]} de la partitura")
    await ev("document.querySelector('[data-vel=\"1\"]').click(); 1")
    # clic en un compás
    j = min(40, n[1] - 2)
    c = await ev(f"medida({j}).dispatchEvent(new MouseEvent('click',{{bubbles:true}})); [cursor, TP[{j}], marcado]")
    if abs(c[0] - c[1]) > 0.01 or c[2] != j: fallos.append(f"clic en el compás {j}: el audio va a {c[0]:.2f} (tocaba {c[1]:.2f})")
    # repetir el trozo de un compás
    await ev(f"sel={{a:TP[{j}], b:TP[{j}+1]}}; $('bucle').checked=true; escuchar(TP[{j}]).then(()=>1)")
    dur = await ev(f"TP[{j}+1]-TP[{j}]")
    await asyncio.sleep(dur + 0.7)
    t = await ev(f"[ahora(), TP[{j}], TP[{j}+1], !!sonando]")
    await ev("parar(); $('bucle').checked=false; sel=null; 1")
    if not (t[3] and t[1] - 0.05 <= t[0] <= t[2] + 0.05): fallos.append(f"«repetir el trozo» con la partitura no vuelve: {t}")
    # ← →: la lupa se marca en la partitura
    await ev("$('adelante').click(); 1"); await asyncio.sleep(0.4)
    if not await ev("document.querySelectorAll('#partitura rect.marca_lupa').length>0"): fallos.append("lo que se ve en la lupa no se marca en la partitura")
    # anclas: mover un compás medio segundo
    an = await ev("const k=Math.min(10,TP.length-2), v=TP[k]; ponAncla(k, v+0.5); [TP[k]-v, $('anclas_txt').textContent]")
    if abs(an[0] - 0.5) > 0.01 or "ANCLAS" not in an[1]: fallos.append(f"las anclas no van: {an}")
    await ev("$('borra_anclas').click(); 1")
    # elegir partes: solo piano → menos pentagramas
    p0 = await ev("medida(5).querySelectorAll('g.staff').length")
    if await ev("!!document.querySelector('[data-parte=\"piano\"]')"):
        await ev("document.querySelector('[data-parte=\"piano\"]').click(); 1")
        await asyncio.sleep(0.5)
        for _ in range(300):
            if await ev("window.__partituraLista===true"): break
            await asyncio.sleep(0.2)
        p1 = await ev("[medida(5).querySelectorAll('g.staff').length, svgMedidas.length]")
        print(f"partes: todas = {p0} pentagramas · solo piano = {p1[0]}")
        if not (0 < p1[0] < p0) or p1[1] != n[1]: fallos.append(f"«solo piano» no quita partes: {p0} → {p1}")
        await ev("document.querySelector('[data-parte=\"todas\"]').click(); 1")
        for _ in range(300):
            if await ev("window.__partituraLista===true"): break
            await asyncio.sleep(0.2)


FOTO = None
PAGINA = None
PARTI = None
SUBIR = None
FOTO_MARCAR = None
FOTO_ONDAS = None
if __name__ == "__main__":
    if "--foto-ondas" in sys.argv:
        i = sys.argv.index("--foto-ondas"); FOTO_ONDAS = str(pathlib.Path(sys.argv[i + 1]).resolve()); del sys.argv[i:i + 2]
    # opcional: --foto-marcar x.png  (foto de la página con «👣 marcar» encendido y la lupa del pie)
    if "--foto-marcar" in sys.argv:
        i = sys.argv.index("--foto-marcar"); FOTO_MARCAR = str(pathlib.Path(sys.argv[i + 1]).resolve()); del sys.argv[i:i + 2]
    # opcional: --subir video.mp4 [segundo esperado]  (subir un vídeo desde la página y que lo cuadre solo)
    if "--subir" in sys.argv:
        i = sys.argv.index("--subir"); a = sys.argv[i + 1:i + 3]
        con_t = len(a) > 1 and a[1].replace(".", "", 1).isdigit()
        del sys.argv[i:i + (3 if con_t else 2)]
        SUBIR = (str(pathlib.Path(a[0]).resolve()), float(a[1]) if con_t else None)
    # opcional: --partitura salida.png [ancho] [compás]  (foto del panel de la partitura abierto)
    if "--partitura" in sys.argv:
        i = sys.argv.index("--partitura"); a = sys.argv[i + 1:i + 4]
        nums = [x for x in a[1:] if x.isdigit()]
        del sys.argv[i:i + 2 + len(nums)]
        PARTI = (a[0], int(nums[0]) if nums else 1300, int(nums[1]) if len(nums) > 1 else 20)
    # opcional: --pagina salida.png [ancho]
    if "--pagina" in sys.argv:
        i = sys.argv.index("--pagina"); a = sys.argv[i + 1:i + 3]
        con_ancho = len(a) > 1 and a[1].isdigit()
        del sys.argv[i:i + (3 if con_ancho else 2)]
        PAGINA = (a[0], int(a[1]) if con_ancho else 1300)

    # opcional: --foto salida.png <compás> [compases a la vista] [casillas 2|3|4]
    if "--foto" in sys.argv:
        i = sys.argv.index("--foto"); a = sys.argv[i + 1:]; del sys.argv[i:]
        FOTO = (a[0], int(a[1]), a[2] if len(a) > 2 else "4", a[3] if len(a) > 3 else "4")
    import urllib.parse
    c = pathlib.Path(sys.argv[1].rstrip("\\/")).resolve()           # carpeta de _ritmo\<canción>
    url = (c.parent.parent / "ritmo.html").as_uri() + "?c=" + urllib.parse.quote(c.name)
    ok = asyncio.run(probar(url))
    sys.exit(0 if ok else 1)
