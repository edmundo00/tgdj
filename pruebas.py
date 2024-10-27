import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TracklistEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        # Verifica que el cambio ocurrió en el archivo específico
        if event.src_path == os.path.abspath("D:\\Downloads\\test.txt"):
            print(f"El archivo {event.src_path} ha sido modificado.")

if __name__ == "__main__":
    # Define la ruta del archivo que quieres monitorear
    tracklist_path = "D:\\Downloads\\test.txt"

    # Crea el archivo si no existe
    if not os.path.exists(tracklist_path):
        with open(tracklist_path, 'w') as f:
            f.write("Línea inicial")

    # Configura el observador y el manejador de eventos
    event_handler = TracklistEventHandler()
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(os.path.abspath(tracklist_path)), recursive=False)
    observer.start()

    print(f"Monitoreando cambios en {tracklist_path}. Presiona Ctrl+C para detener.")

    try:
        while True:
            time.sleep(1)  # Mantiene el script corriendo
    except KeyboardInterrupt:
        observer.stop()
    observer.join()