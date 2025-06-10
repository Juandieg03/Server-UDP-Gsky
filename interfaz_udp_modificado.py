import sys
import threading
import socket
import datetime
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton,
    QLabel, QHBoxLayout, QTableWidget, QTableWidgetItem, QFileDialog
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QTextCursor
from io import StringIO
import contextlib
from servidor_udp_modular import shared_data



# Redirección de stdout para mostrar en interfaz
class EmittingStream:
    def __init__(self, text_edit):
        self.text_edit = text_edit

    def write(self, text):
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.text_edit.insertPlainText(text)

    def flush(self):
        pass


class UDPMonitorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UDP Monitor - Logs, Tramas, Tags")
        self.resize(1000, 700)

        layout = QVBoxLayout()

        # Log de consola
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(QLabel("📄 Consola (Logs en tiempo real):"))
        layout.addWidget(self.log_output)

        # Tramas procesadas
        self.tramas_output = QTextEdit()
        self.tramas_output.setReadOnly(True)
        layout.addWidget(QLabel("📦 Tramas procesadas (tramas_procesadas.txt):"))
        layout.addWidget(self.tramas_output)

        # Tabla de tags
        self.tag_table = QTableWidget()
        layout.addWidget(QLabel("🏷️ Tags parseados (tag_parce.txt):"))
        layout.addWidget(self.tag_table)

        # Botones de control
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Iniciar Servidor UDP")
        self.start_button.clicked.connect(self.start_server)
        button_layout.addWidget(self.start_button)

        self.refresh_button = QPushButton("🔄 Refrescar")
        self.refresh_button.clicked.connect(self.update_views)
        button_layout.addWidget(self.refresh_button)

        self.export_logs_btn = QPushButton("💾 Exportar Logs")
        self.export_logs_btn.clicked.connect(lambda: self.export_text(self.log_output.toPlainText(), "logs.txt"))
        button_layout.addWidget(self.export_logs_btn)

        self.export_tramas_btn = QPushButton("💾 Exportar Tramas")
        self.export_tramas_btn.clicked.connect(lambda: self.export_text(self.tramas_output.toPlainText(), "tramas_exportadas.txt"))
        button_layout.addWidget(self.export_tramas_btn)

        self.mapa_button = QPushButton("🗺️ Mostrar Mapa")
        self.mapa_button.clicked.connect(self.generar_mapa_desde_tags)
        button_layout.addWidget(self.mapa_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.cargar_archivo_btn = QPushButton("📂 Cargar Tramas desde Archivo")
        self.cargar_archivo_btn.clicked.connect(self.cargar_tramas_desde_archivo)
        button_layout.addWidget(self.cargar_archivo_btn)
        
        # Sección para enviar comandos
        layout.addWidget(QLabel("📤 Enviar comando (en HEX):"))
        self.hex_input = QTextEdit()
        self.hex_input.setPlaceholderText("Ejemplo: 0251a601200003383638383232303437343430323930...")
        self.hex_input.setMaximumHeight(60)
        layout.addWidget(self.hex_input)

        send_button = QPushButton("🚀 Enviar Comando")
        send_button.clicked.connect(self.enviar_comando_hex)
        layout.addWidget(send_button)

        # Timer para actualizar contenido automáticamente
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_views)
        self.timer.start(3000)  # Cada 3 segundos

        # Redirigir stdout
        sys.stdout = EmittingStream(self.log_output)

    def start_server(self):
        self.start_button.setEnabled(False)
        threading.Thread(target=external_udp_server_logic, daemon=True).start()

    def update_views(self):
        # Actualiza tramas
        if os.path.exists("tramas_procesadas.txt"):
            with open("tramas_procesadas.txt", "r") as f:
                self.tramas_output.setPlainText(f.read())

        # Actualiza tags
        if os.path.exists("tag_parce.txt"):
            try:
                with open("tag_parce.txt", "r") as f:
                    lines = f.readlines()
                    
                    # Verificar si hay líneas y si la primera línea tiene contenido
                    if lines and lines[0].strip():
                        headers = lines[0].strip().split("\t")
                        
                        # Primero, limpiar la tabla existente
                        self.tag_table.clear()
                        self.tag_table.setRowCount(0)
                        
                        # Configurar columnas
                        self.tag_table.setColumnCount(len(headers))
                        self.tag_table.setHorizontalHeaderLabels(headers)
                        
                        # Añadir filas una por una
                        for row_idx, line in enumerate(lines[1:]):
                            if line.strip():  # Verificar que la línea no esté vacía
                                cells = line.strip().split("\t")
                                self.tag_table.insertRow(row_idx)
                                
                                # Asegurarse de no intentar establecer más celdas que columnas
                                for col_idx, cell in enumerate(cells[:len(headers)]):
                                    self.tag_table.setItem(row_idx, col_idx, QTableWidgetItem(cell))
            except Exception as e:
                print(f"Error al actualizar tabla de tags: {e}")

    def export_text(self, content, filename):
        path, _ = QFileDialog.getSaveFileName(self, "Guardar como", filename)
        if path:
            with open(path, "w") as f:
                f.write(content)

    def decodificar_coordenadas(self, hex_string):
        try:
            raw_bytes = bytes.fromhex(hex_string)
            if len(raw_bytes) < 9:
                print("Trama muy corta para coordenadas:", hex_string)
                return None

            byte0 = raw_bytes[0]
            satelites = byte0 & 0x0F
            source = (byte0 >> 4) & 0x0F

            lat_bytes = raw_bytes[1:5][::-1]
            lon_bytes = raw_bytes[5:9][::-1]

            lat = int.from_bytes(lat_bytes, 'big', signed=True) / 1_000_000
            lon = int.from_bytes(lon_bytes, 'big', signed=True) / 1_000_000

            return {"sat": satelites, "source": source, "lat": lat, "lon": lon}

        except Exception as e:
            print(f"Error decodificando coordenadas ({hex_string}): {e}")
            return None

    def generar_mapa_desde_tags(self):
        import pandas as pd
        import folium
        import webbrowser

        def decodificar_coordenadas(hex_string):
            try:
                raw_bytes = bytes.fromhex(hex_string)
                if len(raw_bytes) < 9:
                    print("Trama muy corta para coordenadas:", hex_string)
                    return None

                byte0 = raw_bytes[0]
                satelites = byte0 & 0x0F
                source = (byte0 >> 4) & 0x0F

                lat_bytes = raw_bytes[1:5][::-1]
                lon_bytes = raw_bytes[5:9][::-1]

                lat = int.from_bytes(lat_bytes, 'big', signed=True) / 1_000_000
                lon = int.from_bytes(lon_bytes, 'big', signed=True) / 1_000_000

                datos = {"sat": satelites, "source": source, "lat": lat, "lon": lon}
                return datos

            except Exception as e:
                print(f"Error decodificando coordenadas ({hex_string}): {e}")
                return None

        if not os.path.exists("tag_parce.txt"):
            print("No se encontró 'tag_parce.txt'")
            return

        try:
            df = pd.read_csv("tag_parce.txt", sep="\t", encoding="latin1")
            if "coordenadas" not in df.columns:
                print("No se encontró la columna 'coordenadas'")
                return

            puntos = []
            for _, row in df.iterrows():
                hora = row["Hora"] if "Hora" in row else ""
                hex_consecutivo = str(row["Consecutivo"]) if "Consecutivo" in row else ""
                if pd.notna(hex_consecutivo) and len(hex_consecutivo) == 4:
                    hex_le = hex_consecutivo[2:4] + hex_consecutivo[0:2]
                    consecutivo = int(hex_le, 16)
                else:
                    consecutivo = -1

                coords = decodificar_coordenadas(str(row["coordenadas"]))
                if coords:
                    puntos.append({
                        "hora": hora,
                        "consecutivo": consecutivo,
                        **coords
                    })

            puntos = sorted(puntos, key=lambda x: x["consecutivo"])

            if not puntos:
                print("No se encontraron coordenadas válidas.")
                return

            mapa = folium.Map(location=[puntos[0]["lat"], puntos[0]["lon"]], zoom_start=12)
            coord_line = []

            for punto in puntos:
                color = "green" if punto["source"] in (0, 2) else "red"
                popup = f'Hora: {punto["hora"]}<br>Satélites: {punto["sat"]}<br>Fuente: {punto["source"]}'
                folium.CircleMarker(
                    location=[punto["lat"], punto["lon"]],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_opacity=0.8,
                    popup=folium.Popup(popup, max_width=250)
                ).add_to(mapa)
                coord_line.append((punto["lat"], punto["lon"]))

            folium.PolyLine(coord_line, color="blue", weight=2.5).add_to(mapa)
            mapa_path = os.path.abspath("mapa_coordenadas.html")
            mapa.save(mapa_path)
            webbrowser.open(f"file://{mapa_path}")
            print("✅ Mapa generado y abierto en el navegador.")

        except Exception as e:
            print(f"Error generando el mapa: {e}")
            
    def enviar_comando_hex(self):
        try:
            hex_str = self.hex_input.toPlainText().strip().replace(" ", "")
            if not hex_str:
                print("⚠️ Comando vacío. Escribe algo en HEX.")
                return

            if len(hex_str) % 2 != 0 or not all(c in "0123456789abcdefABCDEF" for c in hex_str):
                print("❌ El comando HEX es inválido.")
                return

            data = bytes.fromhex(hex_str)

            # Enviar al último cliente que se conectó
            if shared_data.last_client_address is None:
                print("⚠️ Aún no se ha recibido ninguna conexión del equipo.")
                return

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(data, shared_data.last_client_address)

        except Exception as e:
            print(f"❌ Error al enviar comando: {e}")
    
    def cargar_tramas_desde_archivo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo de tramas", "", "Archivos de texto (*.txt);;Todos los archivos (*)")
        if file_path:
            from servidor_udp_modular import save_frame
            try:
                with open(file_path, "r") as file:
                    for line in file:
                        trama = line.strip().replace(" ", "")
                        if all(c in "0123456789abcdefABCDEF" for c in trama):
                            raw_data = bytes.fromhex(trama)
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            save_frame(raw_data, "archivo", timestamp, "tramas_procesadas.txt")
                print("✅ Tramas cargadas desde archivo y procesadas.")
                self.update_views()
            except Exception as e:
                print(f"❌ Error al cargar archivo: {e}")

# Aquí iría tu lógica del servidor UDP
def external_udp_server_logic():
    from servidor_udp_modular import start_udp_server
    start_udp_server()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UDPMonitorApp()
    window.show()
    sys.exit(app.exec())