import sys
import os
import math
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QSlider, 
                             QColorDialog, QPushButton, QComboBox, QFontDialog,
                             QGroupBox, QSpinBox, QDoubleSpinBox, QScrollArea, 
                             QCheckBox, QFileDialog, QMessageBox, QTabWidget, QLineEdit, QSplitter, QDialog)
from PyQt6.QtGui import (QPainter, QColor, QPen, QPolygonF, QFont, QBrush, 
                          QPainterPath, QImage, QLinearGradient, QRadialGradient, QPixmap)
from PyQt6.QtCore import Qt, QPointF, QRectF, QSize, QTimer, QThread, pyqtSignal
import socket
import struct
from PyQt6.QtSvg import QSvgGenerator
import ezdxf
from svgelements import SVG, Path, Matrix, Color
import io

class TelemetryThread(QThread):
    telemetry_updated = pyqtSignal(dict)

    def __init__(self, ip='192.168.1.50', port=9999, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port = port
        self.running = False
        self.sock = None

    def run(self):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)
        try:
            self.sock.bind((self.ip, self.port))
        except Exception as e:
            print(f"Failed to bind UDP: {e}")
            self.running = False
            return

        while self.running:
            try:
                data, addr = self.sock.recvfrom(256)
                if len(data) >= 96:
                    outsim_pack = struct.unpack('I4sH2c7f2I3f16s16si', data[:96])
                    rpm = int(outsim_pack[6])
                    spd = float(outsim_pack[5]) # m/s
                    ctemp = int(outsim_pack[8]) # celsius
                    fuellvl = float(outsim_pack[9]) # 0 to 1
                    turbopressure = float(outsim_pack[7]) # bar
                    kmh = spd * 3.6
                    self.telemetry_updated.emit({
                        'RPM': rpm,
                        'Speed KM/H': kmh,
                        'Temp C': ctemp,
                        'Fuel Lvl': fuellvl,
                        'Turbo Bar': turbopressure
                    })
            except socket.timeout:
                continue
            except Exception as e:
                print(f"UDP Error: {e}")
                
        if self.sock:
            self.sock.close()

    def stop(self):
        self.running = False
        self.wait()

class HelpWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Help / Aiuto")
        self.setMinimumSize(600, 700)
        self.setStyleSheet("""
            QDialog { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #cccccc; line-height: 1.5; font-size: 14px; }
            QScrollArea { border: 1px solid #333333; border-radius: 6px; background: #1a1a1a; }
            QScrollBar:vertical { border: none; background: #121212; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #333333; min-height: 20px; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        layout = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_w = QWidget()
        self.content_l = QVBoxLayout(self.content_w)
        
        self.help_text = QLabel()
        self.help_text.setWordWrap(True)
        self.content_l.addWidget(self.help_text)
        self.scroll.setWidget(self.content_w)
        
        layout.addWidget(self.scroll)
        self.retranslate()

    def get_help_content(self, lang):
        if lang == "it":
            return """
<h2>Benvenuto in Gauge Designer Studio!</h2>
<p>Questa guida ti aiuterà a comprendere le funzioni principali del programma.</p>

<h3 style='color: #ffffff;'>1. Progetto (Project)</h3>
<ul>
    <li><b>Salva/Carica:</b> Gestisci i file .gaugedesign.</li>
    <li><b>Esportazione:</b> Salva come PNG (Alta Res) o SVG (Vettoriale).</li>
    <li><b>Unità di Misura:</b> Passa da Pixel (px) a Centimetri (cm) per precisione millimetrica.</li>
</ul>

<h3 style='color: #ffffff;'>2. Sfondo (Wallpaper)</h3>
<ul>
    <li><b>Stile Sfondo:</b> Scegli tra gradienti, fibra di carbonio o pattern a griglia.</li>
    <li><b>Ghiera Esterna (Rim):</b> Abilita il bordo metallico esterno.</li>
    <li><b>Angoli Scala:</b> Definisci l'inizio e la fine della rotazione della scala.</li>
</ul>

<h3 style='color: #ffffff;'>3. Lancetta (Indicator)</h3>
<ul>
    <li><b>Personalizzazione:</b> Modifica punta, corpo e mozzo della lancetta.</li>
    <li><b>Smoothing Inerzia:</b> Più alto è il valore, più fluida sarà la lancetta.</li>
    <li><b>Binding Dati:</b> Collega la lancetta a dati reali o simulati via OutSim (UDP).</li>
</ul>

<h3 style='color: #ffffff;'>4. Tipografia (Typography)</h3>
<ul>
    <li><b>Numeri Scala:</b> Cambia font, distanza e orientamento dei numeri.</li>
    <li><b>Box Valore:</b> Personalizza il display digitale centrale.</li>
    <li><b>Stringa Unità:</b> Scegli il testo da mostrare (es. RPM, KM/H).</li>
</ul>

<h3 style='color: #ffffff;'>5. Tacche (Ticks)</h3>
<ul>
    <li>Gestisci tre livelli di tacche (Principali, Medie, Piccole). Ad ogni livello puoi assegnare forme diverse (linee, quadrati, cerchi).</li>
</ul>

<h3 style='color: #ffffff;'>6. Archi & Sezioni (Arcs & Sections)</h3>
<ul>
    <li><b>Archi:</b> Crea aree colorate lungo la scala per indicare zone di pericolo (es. linea rossa).</li>
    <li><b>Sezioni:</b> Modifica dinamicamente lo stile di numeri o tacche in base al valore (es. tacche gialle tra 5000 e 7000 RPM).</li>
</ul>

<h3 style='color: #ffffff;'>7. Simulazione OutSim (UDP)</h3>
<ul>
    <li>Il programma può ricevere dati in tempo reale da simulatori (come Assetto Corsa o Live for Speed) via protocollo UDP. Inserisci IP e Porta per vedere la lancetta muoversi!</li>
</ul>
            """
        else:
            return """
<h2>Welcome to Gauge Designer Studio!</h2>
<p>This guide explains the main features of the designer.</p>

<h3 style='color: #ffffff;'>1. Project</h3>
<ul>
    <li><b>Save/Load:</b> Manage your .gaugedesign files.</li>
    <li><b>Export:</b> Save as PNG (High Res) or SVG (Vector).</li>
    <li><b>Measurement Units:</b> Switch between Pixels (px) and Centimeters (cm) for real-world precision.</li>
</ul>

<h3 style='color: #ffffff;'>2. Wallpaper & Geometry</h3>
<ul>
    <li><b>BG Style:</b> Choose between gradients, carbon fiber, or grid patterns.</li>
    <li><b>Bezel Outer Rim:</b> Enable the outer metallic ring.</li>
    <li><b>Scale Angles:</b> Define where the gauge starts and ends.</li>
</ul>

<h3 style='color: #ffffff;'>3. Indicator/Needle</h3>
<ul>
    <li><b>Customization:</b> Edit the point, tail, and hub decor.</li>
    <li><b>Inertia Smoothing:</b> Higher values make the needle response smoother.</li>
    <li><b>Data Binding:</b> Connect the needle to manual input or live UDP simulation.</li>
</ul>

<h3 style='color: #ffffff;'>4. Typography & Data</h3>
<ul>
    <li><b>Scale Numbers:</b> Change font, distance, and orientation.</li>
    <li><b>Value Box:</b> Customize the central digital display.</li>
    <li><b>Unit Label:</b> Set custom text like RPM, KM/H, or PSI.</li>
</ul>

<h3 style='color: #ffffff;'>5. Ticks</h3>
<ul>
    <li>Manage three levels of ticks (Major, Medium, Small). Each can have different shapes: lines, dots, or rectangles.</li>
</ul>

<h3 style='color: #ffffff;'>6. Arcs & Sections</h3>
<ul>
    <li><b>Arcs:</b> Add colored regions along the scale (e.g., Redline).</li>
    <li><b>Sections:</b> Dynamically change tick or number styles based on current values.</li>
</ul>

<h3 style='color: #ffffff;'>7. OutSim Simulation (UDP)</h3>
<ul>
    <li>Receive realtime data from simulators (Assetto Corsa, Live for Speed) via UDP. Enter IP/Port and start telemetry to see the needle move!</li>
</ul>
            """

    def retranslate(self):
        parent = self.parent()
        lang = getattr(parent, "lang", "en")
        self.setWindowTitle("Help" if lang == "en" else "Guida")
        self.help_text.setText(self.get_help_content(lang))

class AnalogTachometer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gauge_w = 600
        self.gauge_h = 600
        self.setFixedSize(self.gauge_w, self.gauge_h)
        
        self.telemetry_data = {}
        self.needle_bind_target = "Current Value"
        self.show_needle = True
        
        # 1. Scale & Physics Logic
        self.start_angle, self.end_angle = 135, 405
        self.value = 0.0
        self.target_value = 0.0
        self.plotter_mode = False
        self.min_value = 0.0
        self.max_value = 8000.0
        self.scale_multiplier = 0.001
        self.anim_inertia = 0.15 

        # 2. Wallpaper & Rim (Black-Anthracite Aesthetic)
        self.bg_color_1 = QColor("#050505")
        self.bg_color_2 = QColor("#1f1f1f")
        self.bg_mode = "Solid" 
        self.rim = {'en': True, 't': 8, 'col': QColor("#555555"), 'style': 'Metallic'}

        # 3. Ticks Data (Clean, sharp lines)
        self.ticks = {
            'big':   {'en': True, 'sh': 'Line', 'r': 280, 'l': 20, 't': 4, 'col': QColor("#e0e0e0"), 'cnt': 8},
            'med':   {'en': True, 'sh': 'Line', 'r': 280, 'l': 12, 't': 2, 'col': QColor("#888888"), 'cnt': 1},
            'small': {'en': True, 'sh': 'Line', 'r': 280, 'l': 6,  't': 2, 'col': QColor("#444444"), 'cnt': 4}
        }
        
        # 4. Digital Value Box
        self.val_box = {
            'en': True, 'dec': 0, 'w': 140, 'h': 45, 'y': 150, 'rad': 6, 't': 2,
            'bg': QColor("#111111"), 'border': QColor("#333333"), 'text_col': QColor("#e0e0e0"),
            'font': QFont(), 'prefix': '', 'suffix': ' RPM'
        }
        self.val_box['font'].fromString("Segoe UI,20,-1,5,700,0,0,0,0,0,0,0,0,0,0,1")
        
        # 5. Indicators (COMPLEX MULTI-PART NEEDLE)
        self.indicator_mode = "Needle" 
        self.center_dot_col = QColor("#ffffff")
        self.needle_ind = {'sh': 'Tapered', 'l': 255, 't': 11, 'col': QColor("#d92b2b")}
        self.needle_pin = {'sh': 'Circle', 'r': 20, 'col': QColor("#050505")}
        self.needle_decor = {'en': False, 'r': 10, 't': 3, 'col': QColor("#d92b2b")}
        self.needle_tail = {'sh': 'Inv-Trapezoid', 'l': 50, 't': 8, 'col': QColor("#444444")}
        
        self.prog_bar = { 'r': 250, 'thick': 20, 'col': QColor("#444444"), 'segments': 40, 'gap': 1.5, 'rounded': True }
        
        # 6. Typography
        self.unit_label = {'text': 'RPM', 'x': 0, 'y': -80, 'fs': 16, 'col': QColor("#888888"), 'font': QFont()}
        self.unit_label['font'].fromString("Segoe UI,16,-1,5,500,0,0,0,0,0,0,0,0,0,0,1")
        self.text = {'fs': 20, 'alt_fs': 12, 'mode': 'All Regular', 'align': 'Center', 'align_offset': 0, 'dist': 219, 'rot': False, 'col': QColor("#e0e0e0"), 'font': QFont()}
        self.text['font'].fromString("Segoe UI,18,-1,5,700,0,0,0,0,0,0,0,0,0,0,1")
        
        self.tick_sets = [
            {'name': 'Major', 'type': 'Major', 'en': True, 'cnt': 8, 'sh': 'Rounded Rectangle', 'r': 265, 'l': 20, 't': 8, 'col': QColor("#ffffff"), 'layer': 'Bottom'},
            {'name': 'Medium', 'type': 'Minor', 'en': True, 'cnt': 1, 'sh': 'Rounded Rectangle', 'r': 260, 'l': 12, 't': 4, 'col': QColor("#ffffff"), 'layer': 'Bottom'},
            {'name': 'Small', 'type': 'Sub-Minor', 'en': True, 'cnt': 4, 'sh': 'Rounded Rectangle', 'r': 260, 'l': 8, 't': 2, 'col': QColor("#ffffff"), 'layer': 'Bottom'}
        ]
        
        self.sections =[] 
        self.arcs = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)

    def update_telemetry(self, data):
        self.telemetry_data = data
        if str(self.needle_bind_target).startswith('Sim: '):
            self.update_val(self.get_bound_value(self.needle_bind_target, self.value))
        else:
            self.update()

    def update_val(self, target):
        self.target_value = target

    def _update_animation(self):
        diff = self.target_value - self.value
        if abs(diff) > 0.01:
            self.value += diff * self.anim_inertia
            self.update()

    def get_val_angle(self, val, span):
        total_range = self.max_value - self.min_value
        if total_range <= 0: return self.start_angle
        return self.start_angle + ((val - self.min_value) / total_range) * span

    def get_bound_value(self, bind_str, fallback):
        if bind_str == 'Current Value' or bind_str is True: return self.value
        elif bind_str == 'Min Value': return self.min_value
        elif bind_str == 'Max Value': return self.max_value
        elif isinstance(bind_str, str) and bind_str.startswith('Sim: '):
            return self.telemetry_data.get(bind_str.replace('Sim: ', ''), fallback)
        return fallback

    def safe_set_font(self, painter, font_obj, size_val, scale):
        try:
            f = QFont(font_obj)
            base_size = float(size_val)
            if base_size <= 0: base_size = float(f.pointSizeF())
            if base_size <= 0: base_size = float(f.pixelSize())
            if base_size <= 0: base_size = 12.0
            f.setPointSizeF(max(1.0, base_size * scale))
            painter.setFont(f)
        except Exception as e:
            print(f"Font Safety Net Triggered: {e}")

    def paint_gauge(self, painter, w, h, exp_needle=True, exp_val=True):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(w, h)
        center = QPointF(w / 2, h / 2)
        scale = size / 600.0  # Virtual base size for scaling analog elements
        
        # Background Wallpaper
        if getattr(self, 'plotter_mode', False):
            painter.setBrush(QBrush(Qt.GlobalColor.black))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, size/2, size/2)
        else:
            self.draw_wallpaper(painter, QRectF(0, 0, w, h), True)

        # Bezel (With polished Metallic option)
        if self.rim['en']:
            painter.save()
            if getattr(self, 'plotter_mode', False):
                painter.setPen(QPen(Qt.GlobalColor.black, self.rim['t'] * scale))
            else:
                pen_col = self.rim['col']
                if self.rim['style'] == 'Metallic':
                    grad = QLinearGradient(0, 0, size, size)
                    grad.setColorAt(0, pen_col.lighter(150)); grad.setColorAt(0.2, pen_col); 
                    grad.setColorAt(0.5, pen_col.darker(150)); grad.setColorAt(0.8, pen_col); grad.setColorAt(1, pen_col.lighter(150))
                    # FIX: Explicitly wrap the gradient in a QBrush to prevent PyQt6 TypeError crash
                    painter.setPen(QPen(QBrush(grad), self.rim['t'] * scale))
                else:
                    painter.setPen(QPen(QBrush(pen_col), self.rim['t'] * scale))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, (size/2) - (self.rim['t']*scale/2), (size/2) - (self.rim['t']*scale/2))
            painter.restore()

        span = self.end_angle - self.start_angle
        self.render_arcs(painter, center, scale, span, layer='Bottom')

        # Rendering Ticks In Layers
        for layer in ['Bottom', 'Top']:
            for ts in self.tick_sets:
                if not ts.get('en', True) or ts.get('layer', 'Bottom') != layer: continue
                # Calculate Frequency
                total_steps = self.calculate_tick_count(ts)
                if total_steps <= 0: continue
                # Unique Frequency Logic: Skip ticks that coincide with higher-order scales
                skip_mod = (ts['cnt'] + 1) if ts['type'] in ['Minor', 'Sub-Minor'] else 0
                
                for i in range(total_steps + 1):
                    # Check if this tick set should render at this I index
                    if skip_mod > 0 and i % skip_mod == 0: continue
                    
                    angle = self.start_angle + (i * span / total_steps)
                    val = self.min_value + (i / total_steps) * (self.max_value - self.min_value)
                    
                    t_props = ts.copy()
                    for sec in self.sections:
                        if sec.get('en', True) and sec['min'] <= val <= sec['max'] and sec['target'] == ts['type']:
                            t_props.update(sec)
                    
                    if t_props.get('en', True): 
                        if getattr(self, 'plotter_mode', False): t_props['col'] = Qt.GlobalColor.white
                        self.render_tick_shape(painter, angle, t_props, center, scale)

            # Special Step: Render Labels after Bottom ticks
            if layer == 'Bottom':
                self.render_labels(painter, center, scale, span)

        # Unit Label
        if getattr(self, 'plotter_mode', False):
            painter.setPen(Qt.GlobalColor.white)
        else:
            painter.setPen(self.unit_label['col'])
        self.safe_set_font(painter, self.unit_label['font'], self.unit_label['fs'], scale)
        if getattr(self, 'plotter_mode', False):
            path = QPainterPath()
            text = self.unit_label.get('text', '')
            fm = painter.fontMetrics()
            br = fm.boundingRect(QRectF(self.unit_label.get('x', 0)*scale, center.y() + self.unit_label['y']*scale, size, 60*scale).toRect(), Qt.AlignmentFlag.AlignCenter, text)
            path.addText(br.left(), br.bottom() - fm.descent(), painter.font(), text)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(Qt.GlobalColor.white, 1*scale))
            painter.drawPath(path)
        else:
            painter.drawText(QRectF(self.unit_label.get('x', 0)*scale, center.y() + self.unit_label['y']*scale, size, 60*scale), Qt.AlignmentFlag.AlignCenter, self.unit_label['text'])

        self.render_arcs(painter, center, scale, span, layer='Top')

        # Center Dot (visible even when needle is hidden)
        if not getattr(self, 'plotter_mode', False):
            painter.save()
            painter.setBrush(QBrush(self.center_dot_col))
            painter.setPen(Qt.PenStyle.NoPen)
            r_dot = 4 * scale
            painter.drawEllipse(center, r_dot, r_dot)
            painter.restore()

        # User choice: Export with or without dynamic elements
        if exp_val and self.val_box['en']: 
            self.render_value_box(painter, center, scale)
        if exp_needle: 
            self.render_needle(painter, center, scale, span)

    def render_arcs(self, painter, center, scale, span, layer):
        rng = self.max_value - self.min_value
        if rng <= 0: return
        for arc in self.arcs:
            if not arc.get('en', True): continue
            if arc.get('layer', 'Bottom') != layer: continue
            arc_min = max(self.min_value, arc['min'])
            arc_max = min(self.max_value, arc['max'])
            if arc_min >= arc_max: continue
            r = arc['r'] * scale
            t = arc['t'] * scale
            rect = QRectF(center.x() - r, center.y() - r, r * 2, r * 2)
            start_p = (arc_min - self.min_value) / rng
            span_p = (arc_max - arc_min) / rng
            painter.save()
            painter.setPen(QPen(QBrush(arc['col']), t, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
            painter.drawArc(rect, int(-(self.start_angle + start_p * span) * 16), int(-span_p * span * 16))
            painter.restore()

    def render_needle(self, painter, center, scale, span):
        if self.indicator_mode != "Needle":
            self.render_progress_bar(painter, center, scale, span)
            return

        angle = self.get_val_angle(self.value, span)
        painter.save(); painter.translate(center); painter.rotate(angle)

        def draw_needle_geometry(p, is_shadow=False):
            # Tail
            tl, tt = self.needle_tail['l'] * scale, self.needle_tail['t'] * scale
            st = self.needle_tail['sh']
            if not is_shadow: p.setBrush(QBrush(self.needle_tail['col']))
            if st == "Trapezoid": p.drawPolygon(QPolygonF([QPointF(0, -tt/2), QPointF(-tl, -tt/4), QPointF(-tl, tt/4), QPointF(0, tt/2)]))
            elif st == "Inv-Trapezoid": p.drawPolygon(QPolygonF([QPointF(0, -tt/4), QPointF(-tl, -tt/2), QPointF(-tl, tt/2), QPointF(0, tt/4)]))
            elif st == "Inv-Triangle": p.drawPolygon(QPolygonF([QPointF(0, 0), QPointF(-tl, -tt/2), QPointF(-tl, tt/2)]))
            elif st == "Rounded": p.drawRoundedRect(QRectF(-tl, -tt/2, tl, tt), tt/2, tt/2)
            elif st == "Rect": p.drawRect(QRectF(-tl, -tt/2, tl, tt))

            # Main Indicator
            il, it = self.needle_ind['l'] * scale, self.needle_ind['t'] * scale
            si = self.needle_ind['sh']
            if not is_shadow: p.setBrush(QBrush(self.needle_ind['col']))
            if si == "Trapezoid": p.drawPolygon(QPolygonF([QPointF(0, -it/2), QPointF(il, -it/4), QPointF(il, it/4), QPointF(0, it/2)]))
            elif si == "Tapered": p.drawPolygon(QPolygonF([QPointF(0, -it/2), QPointF(il, -it/6), QPointF(il, it/6), QPointF(0, it/2)]))
            elif si == "Triangle": p.drawPolygon(QPolygonF([QPointF(0, -it/2), QPointF(il, 0), QPointF(0, it/2)]))
            elif si == "Line": 
                if is_shadow: p.setPen(QPen(QBrush(QColor(0,0,0,100)), it, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                else: p.setPen(QPen(QBrush(self.needle_ind['col']), it, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawLine(0, 0, int(il), 0)
                p.setPen(Qt.PenStyle.NoPen)

            # Pin Hub
            pr = self.needle_pin['r'] * scale
            if not is_shadow: p.setBrush(QBrush(self.needle_pin['col']))
            if self.needle_pin['sh'] == 'Hex':
                poly = QPolygonF();[poly.append(QPointF(pr*math.cos(math.radians(j*60)), pr*math.sin(math.radians(j*60)))) for j in range(6)]; p.drawPolygon(poly)
            else: p.drawEllipse(QPointF(0,0), pr, pr)
            
            # Decor Ring
            if self.needle_decor['en'] and not is_shadow:
                dr, dt = self.needle_decor['r'] * scale, self.needle_decor['t'] * scale
                p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QBrush(self.needle_decor['col']), dt)); p.drawEllipse(QPointF(0,0), dr, dr)
                p.setPen(Qt.PenStyle.NoPen)

        # 1. Draw 3D Drop Shadow
        if not getattr(self, 'plotter_mode', False):
            painter.save()
            painter.translate(4 * scale, 4 * scale)
            painter.setBrush(QColor(0, 0, 0, 120))
            painter.setPen(Qt.PenStyle.NoPen)
            draw_needle_geometry(painter, is_shadow=True)
            painter.restore()

        # 2. Draw Actual Needle
        if getattr(self, 'plotter_mode', False):
            painter.setBrush(Qt.GlobalColor.white)
            painter.setPen(QPen(Qt.GlobalColor.white, 1*scale))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        draw_needle_geometry(painter, is_shadow=False)

        painter.restore()

    def render_tick_shape(self, painter, angle, data, center, scale):
        r_out, t, l = data['r']*scale, data['t']*scale, data['l']*scale
        r_in = r_out - l
        painter.save(); painter.translate(center); painter.rotate(angle)
        if data['sh'] == 'Dot':
            painter.setBrush(QBrush(data['col'])); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(QPointF(r_out, 0), t/2, t/2)
        elif data['sh'] == 'Rectangle':
            painter.setBrush(QBrush(data['col'])); painter.setPen(Qt.PenStyle.NoPen); painter.drawRect(QRectF(r_in, -t/2, l, t))
        elif data['sh'] == 'Rounded Rectangle':
            painter.setBrush(QBrush(data['col'])); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(QRectF(r_in, -t/2, l, t), t/2, t/2)
        elif data['sh'] == 'Line':
            painter.setPen(QPen(QBrush(data['col']), t, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); painter.drawLine(int(r_in), 0, int(r_out), 0)
        elif data['sh'] == 'Triangle':
            painter.setBrush(QBrush(data['col'])); painter.setPen(Qt.PenStyle.NoPen)
            poly = QPolygonF([QPointF(r_in, -t), QPointF(r_out, 0), QPointF(r_in, t)])
            painter.drawPolygon(poly)
        painter.restore()


    def calculate_tick_count(self, ts):
        # Nested Frequency Logic: always follow the first ENABLED Major/Minor
        major_set = next((s for s in self.tick_sets if s['type'] == 'Major' and s.get('en', True)), None)
        major_cnt = major_set['cnt'] if major_set else 1
        if ts['type'] == 'Major': return ts['cnt']
        
        # Minor depends on enabled Major
        if ts['type'] == 'Minor': return major_cnt * (ts['cnt'] + 1)
        
        # Sub-Minor depends on enabled Major and enabled Minor
        if ts['type'] == 'Sub-Minor':
            minor_set = next((s for s in self.tick_sets if s['type'] == 'Minor' and s.get('en', True)), None)
            minor_sub = minor_set['cnt'] if minor_set else 0
            return major_cnt * (minor_sub + 1) * (ts['cnt'] + 1)
        return ts.get('cnt', 10)

    def render_labels(self, painter, center, scale, span):
        primary_set = next((s for s in self.tick_sets if s['type'] == 'Major'), None)
        if not primary_set: return
        
        total_steps = primary_set['cnt']
        for i in range(total_steps + 1):
            angle = self.start_angle + (i * span / total_steps)
            val = self.min_value + (i / total_steps) * (self.max_value - self.min_value)
            
            txt_props = self.text.copy()
            for sec in self.sections:
                if sec.get('en', True) and sec['min'] <= val <= sec['max'] and sec['target'] == 'text':
                    txt_props.update(sec)
            
            big_idx = i
            mode = txt_props.get('mode', 'All Regular')
            draw_num, use_alt = True, False
            if mode == 'Even Only' and big_idx % 2 != 0: draw_num = False
            elif mode == 'Odd Only' and big_idx % 2 == 0: draw_num = False
            elif mode == 'Odd Alt Size' and big_idx % 2 != 0: use_alt = True
            elif mode == 'Even Alt Size' and big_idx % 2 == 0: use_alt = True
            
            if draw_num:
                rad = math.radians(angle)
                tx, ty = center.x() + (txt_props['dist'] * scale) * math.cos(rad), center.y() + (txt_props['dist'] * scale) * math.sin(rad)
                painter.save(); painter.translate(tx, ty)
                if txt_props['rot']: painter.rotate(angle + 90)
                if getattr(self, 'plotter_mode', False): painter.setPen(Qt.GlobalColor.white)
                else: painter.setPen(txt_props['col'])
                fs = txt_props.get('alt_fs', 12) if use_alt else txt_props['fs']
                self.safe_set_font(painter, txt_props['font'], fs, scale)
                val_txt = f"{((val) * getattr(self, 'scale_multiplier', 0.001)):g}"
                rect = painter.fontMetrics().boundingRect(val_txt)
                al = txt_props.get('align', 'Center')
                off_val = txt_props.get('align_offset', 0) * scale
                off_x = -rect.width()/2
                if al == 'Left': off_x = 0
                elif al == 'Right': off_x = -rect.width()
                
                if getattr(self, 'plotter_mode', False):
                    path = QPainterPath()
                    path.addText(float(off_x + off_val), float(rect.height()/4), painter.font(), val_txt)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    if getattr(self, 'plotter_mode', False):
                        painter.setPen(QPen(Qt.GlobalColor.white, 1*scale))
                    else:
                        painter.setPen(QPen(txt_props['col'], 1*scale))
                    painter.drawPath(path)
                else:
                    painter.drawText(int(off_x + off_val), int(rect.height()/4), val_txt)
                painter.restore()

    def render_value_box(self, painter, center, scale):
        vb = self.val_box; w, h, y, r = vb['w']*scale, vb['h']*scale, vb['y']*scale, vb['rad']*scale
        rect = QRectF(center.x() - w/2, center.y() + y - h/2, w, h)
        
        # Background Shadow Drop
        if not getattr(self, 'plotter_mode', False):
            painter.setBrush(QColor(0, 0, 0, 150)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect.translated(0, int(3*scale)), r, r)

        if getattr(self, 'plotter_mode', False):
            painter.setBrush(Qt.GlobalColor.black)
            painter.setPen(QPen(Qt.GlobalColor.white, vb['t']*scale))
        else:
            painter.setBrush(QBrush(vb['bg'])); painter.setPen(QPen(QBrush(vb['border']), vb['t']*scale))
            
        painter.drawRoundedRect(rect, r, r)
        
        if not getattr(self, 'plotter_mode', False):
            painter.setPen(vb['text_col'])
        
        self.safe_set_font(painter, vb['font'], 0, scale) 
        
        val_str = f"{self.value:.{vb['dec']}f}{vb['suffix']}"
        if getattr(self, 'plotter_mode', False):
            path = QPainterPath()
            fm = painter.fontMetrics()
            br = fm.boundingRect(rect.toRect(), Qt.AlignmentFlag.AlignCenter, val_str)
            path.addText(br.left(), br.bottom() - fm.descent(), painter.font(), val_str)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(Qt.GlobalColor.white, 1*scale))
            painter.drawPath(path)
        else:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, val_str)

    def render_progress_bar(self, painter, center, scale, span):
        pb = self.prog_bar; r, t = pb['r']*scale, pb['thick']*scale
        rect = QRectF(center.x()-r, center.y()-r, r*2, r*2)
        rng = self.max_value - self.min_value
        curr_p = max(0, min((self.value - self.min_value) / rng, 1.0)) if rng > 0 else 0
        painter.setPen(QPen(QBrush(pb['col']), t, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap if pb['rounded'] else Qt.PenCapStyle.FlatCap))
        if pb['segments'] <= 1: painter.drawArc(rect, int(-self.start_angle*16), int(-span*curr_p*16))
        else:
            seg_c, gap = pb['segments'], pb['gap']
            seg_w = (span - (gap * (seg_c - 1))) / seg_c
            for i in range(seg_c):
                if self.min_value + (i / seg_c) * rng > self.value: break
                painter.drawArc(rect, int(-(self.start_angle + i*(seg_w+gap))*16), int(-seg_w*16))


    def draw_wallpaper(self, painter, rect_f, is_radial):
        size = rect_f.width()
        center = rect_f.center()
        c1, c2 = self.bg_color_1, self.bg_color_2
        
        painter.setPen(Qt.PenStyle.NoPen)
        if self.bg_mode == "Solid":
            painter.setBrush(QBrush(c2))
        elif self.bg_mode == "Radial Gradient":
            grad = QRadialGradient(center, size/2); grad.setColorAt(0, c2); grad.setColorAt(1, c1)
            painter.setBrush(QBrush(grad))
        elif self.bg_mode == "Vertical Gradient":
            grad = QLinearGradient(rect_f.topLeft(), rect_f.bottomLeft()); grad.setColorAt(0, c2); grad.setColorAt(1, c1)
            painter.setBrush(QBrush(grad))
        elif self.bg_mode == "Horizontal Gradient":
            grad = QLinearGradient(rect_f.topLeft(), rect_f.topRight()); grad.setColorAt(0, c2); grad.setColorAt(1, c1)
            painter.setBrush(QBrush(grad))
        elif self.bg_mode == "Cross Weave":
            painter.setBrush(QBrush(c1))
            if is_radial: painter.drawEllipse(center, size/2, size/2)
            else: painter.drawRect(rect_f)
            painter.setBrush(QBrush(c2, Qt.BrushStyle.DiagCrossPattern))
        elif self.bg_mode == "Carbon Fibre":
            # REALISTIC CARBON FIBRE (8x8 Twill Weave)
            tile_size = 8
            pixmap = QPixmap(tile_size, tile_size)
            pixmap.fill(c1)
            tp = QPainter(pixmap)
            # Create a 2x2 twill weave pattern using c2 and c1
            # We use a slightly darker/lighter shade for the 'fibers'
            c_light = c2.lighter(110); c_dark = c2.darker(110)
            
            tp.setPen(Qt.PenStyle.NoPen)
            # Twill pattern: 4x4 blocks in 8x8 tile
            tp.setBrush(QBrush(c_light)); tp.drawRect(0, 0, 4, 4)
            tp.setBrush(QBrush(c_dark)); tp.drawRect(4, 4, 4, 4)
            
            # Add some 'fiber' lines for realism
            tp.setPen(QPen(c1.lighter(105), 1))
            for i in range(0, 8, 2):
                tp.drawLine(i, 0, i, 8)
            tp.end()
            
            painter.setBrush(QBrush(pixmap))
            if is_radial: painter.drawEllipse(center, size/2, size/2)
            else: painter.drawRect(rect_f)
        elif self.bg_mode == "Grid Pattern":
            painter.setBrush(QBrush(c1))
            if is_radial: painter.drawEllipse(center, size/2, size/2)
            else: painter.drawRect(rect_f)
            painter.setBrush(QBrush(c2, Qt.BrushStyle.CrossPattern))
        elif self.bg_mode == "Dense Dot Pattern":
            painter.setBrush(QBrush(c1))
            if is_radial: painter.drawEllipse(center, size/2, size/2)
            else: painter.drawRect(rect_f)
            painter.setBrush(QBrush(c2, Qt.BrushStyle.Dense4Pattern))
        else:
            painter.setBrush(QBrush(c1))
            
        if is_radial: painter.drawEllipse(center, size/2, size/2)
        else: painter.drawRect(rect_f)

    # FIX: Added `painter.end()` to prevent garbage collection segfaults!
    def paintEvent(self, event):
        painter = QPainter(self)
        self.paint_gauge(painter, self.width(), self.height(), exp_needle=self.show_needle, exp_val=True)
        painter.end()


class DesignerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gauge Designer Studio")
        self.gauge = AnalogTachometer()
        self._is_syncing = False
        self._is_undoing = False
        self.arc_widgets = []
        self.sec_widgets = []
        self.tick_widgets = []
        
        self.history = []
        self.history_index = -1
        self.unit_mode = "px"  # "px" or "cm"
        self.px_per_cm = 37.8
        self.lang = "en"
        self.is_dirty = False
        self.help_window = None
        self.sim_window = None
        self.telemetry_thread = None
        self.ui_reg = {}
        self.translations = {
            "Gauge Designer Studio": {"it": "Studio Design Tachimetri"},
            "Project Files": {"it": "File del Progetto"},
            "Save Project (.gaugedesign)": {"it": "Salva Progetto (.gaugedesign)"},
            "Load Project (.gaugedesign)": {"it": "Carica Progetto (.gaugedesign)"},
            "Undo": {"it": "Annulla"},
            "Redo": {"it": "Ripristina"},
            "Export Settings": {"it": "Impostazioni Esportazione"},
            "Include Value Box in Export": {"it": "Includi Box Valore nell'Esportazione"},
            "Include Needle in Export": {"it": "Includi Lancetta nell'Esportazione"},
            "Export Width (PX)": {"it": "Larghezza Esportazione (PX)"},
            "Export PNG High-Res": {"it": "Esporta PNG Alta Risoluzione"},
            "Export SVG Vector": {"it": "Esporta SVG Vettoriale"},
            "Export Plotter Cut-Lines (DXF)": {"it": "Esporta Plotter Cut-Lines (DXF)"},
            "Language / Lingua": {"it": "Lingua / Language"},
            "Measurement Units": {"it": "Unità di Misura"},
            "Current Unit": {"it": "Unità Corrente"},
            "Pixels per CM": {"it": "Pixel per CM"},
            "Enable Bezel Outer Rim": {"it": "Abilita Ghiera Esterna"},
            "BG Style": {"it": "Stile Sfondo"},
            "Edge Color": {"it": "Colore Bordo"},
            "Center Color": {"it": "Colore Centrale"},
            "UI Pixels": {"it": "Pixel UI"},
            "Minimum Value": {"it": "Valore Minimo"},
            "Maximum Value": {"it": "Valore Massimo"},
            "Start Angle": {"it": "Angolo Inizio"},
            "End Angle": {"it": "Angolo Fine"},
            "Indicator Point": {"it": "Punto Indicatore"},
            "Length": {"it": "Lunghezza"},
            "Thickness": {"it": "Spessore"},
            "Shape": {"it": "Forma"},
            "Pick Color": {"it": "Scegli Colore"},
            "Counter-Weight Tail": {"it": "Contrappeso Lancetta"},
            "Hub & Decor Ring": {"it": "Mozzo e Anello Decorato"},
            "Pin Rad": {"it": "Raggio Perno"},
            "Pin Color": {"it": "Colore Perno"},
            "Enable Decor Ring": {"it": "Abilita Anello Decorativo"},
            "Ring Rad": {"it": "Raggio Anello"},
            "Ring Thick": {"it": "Spessore Anello"},
            "Ring Color": {"it": "Colore Anello"},
            "Center Dot Color": {"it": "Colore Punto Centrale"},
            "Inertia Smoothing %": {"it": "Smoothing Inerzia %"},
            "Data Simulation Binding": {"it": "Simulazione Binding Dati"},
            "Scale Numbers": {"it": "Numeri della Scala"},
            "Rotate Scale Numbers": {"it": "Ruota Numeri Scala"},
            "Font Size": {"it": "Dimensione Font"},
            "Distance From Center": {"it": "Distanza dal Centro"},
            "Number Pattern": {"it": "Pattern Numeri"},
            "Alt Size": {"it": "Dimensione Alt."},
            "Value Multiplier": {"it": "Moltiplicatore Valore"},
            "Digital Value Box": {"it": "Box Valore Digitale"},
            "Enable Value Box": {"it": "Abilita Box Valore"},
            "Box Width": {"it": "Larghezza Box"},
            "Box Height": {"it": "Altezza Box"},
            "Custom Typography": {"it": "Tipografia Personalizzata"},
            "Pick Scale Numbers Font": {"it": "Scegli Font Numeri Scala"},
            "Pick Digital Box Font": {"it": "Scegli Font Box Digitale"},
            "Pick Unit Label Font": {"it": "Scegli Font Etichetta Unità"},
            "Unit String Configuration": {"it": "Configurazione Stringa Unità"},
            "Unit Text Label": {"it": "Etichetta Testo Unità"},
            "X Offset (px)": {"it": "Offset X (px)"},
            "Y Offset (px)": {"it": "Offset Y (px)"},
            "Add New Arc": {"it": "Aggiungi Nuovo Arco"},
            "Add New Section": {"it": "Aggiungi Nuova Sezione"},
            "Live Studio Simulator": {"it": "Simulatore di Studio"},
            "Manual Testing Value": {"it": "Valore di Test Manuale"},
            "Show Needle While Editing": {"it": "Mostra Lancetta in Editing"},
            "OutSim IP": {"it": "IP OutSim"},
            "OutSim Port": {"it": "Porta OutSim"},
            "Start UDP Telemetry (OutSim)": {"it": "Avvia Telemetria UDP"},
            "Lock Dashboard Resize": {"it": "Blocca Ridimensionamento"},
            "Unlock Dashboard Resize": {"it": "Sblocca Ridimensionamento"},
            "Arc": {"it": "Arco"},
            "Section": {"it": "Sezione"},
            "Enabled": {"it": "Abilitato"},
            "Color": {"it": "Colore"},
            "Delete": {"it": "Elimina"},
            "Name": {"it": "Nome"},
            "Target": {"it": "Target"},
            "Radius": {"it": "Raggio"},
            "Layer": {"it": "Livello"},
            "Text Font Size": {"it": "Dim. Font Testo"},
            "Pin Shape": {"it": "Forma Perno"}
        }
        self.size_controls = []  # List of (sld, spn, label, min_px, max_px) for scaling
        self.undo_timer = QTimer(self)
        self.undo_timer.setSingleShot(True)
        self.undo_timer.setInterval(400)
        self.undo_timer.timeout.connect(self.push_state)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.scroll_preview = QScrollArea()
        self.scroll_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_preview.setWidget(self.gauge)
        self.scroll_preview.setStyleSheet("QScrollArea { background-color: #050505; border: none; }")
        self.splitter.addWidget(self.scroll_preview)

        self.ctrl_scroll = QScrollArea()
        self.ctrl_panel = QWidget()
        self.controls_layout = QVBoxLayout(self.ctrl_panel)
        self.controls_layout.setContentsMargins(20, 20, 20, 20)
        self.controls_layout.setSpacing(15)

        # Deep Modern Studio Theme (Black-Anthracite Inspired)
        self.ctrl_panel.setStyleSheet("""
            QWidget { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 13px; } 
            QGroupBox { border: 1px solid #333333; border-radius: 6px; margin-top: 15px; color: #e0e0e0; font-weight: bold; padding-top: 10px; } 
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 10px; background-color: #121212; top: 0px; }
            QPushButton { background: #222222; border: 1px solid #333333; border-radius: 4px; padding: 6px 12px; font-weight: bold; } 
            QPushButton:hover { background: #333333; border: 1px solid #555555; }
            QPushButton:pressed { background: #444444; }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit { background: #1a1a1a; border: 1px solid #333333; border-radius: 4px; padding: 4px; }
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border: 1px solid #555555; }
            QTabWidget::pane { border: 1px solid #333333; border-radius: 6px; background: #121212; top: -1px; }
            QTabBar::tab { background: #1a1a1a; color: #999999; padding: 10px 15px; border: 1px solid #333333; border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; } 
            QTabBar::tab:selected { background: #222222; color: #ffffff; font-weight: bold; border-bottom: 2px solid #aaaaaa;}
            QTabBar::tab:hover { background: #2a2a2a; }
            QSlider::groove:horizontal { border: 1px solid #333333; height: 6px; background: #1a1a1a; border-radius: 3px; }
            QSlider::handle:horizontal { background: #777777; border: 1px solid #999999; width: 14px; margin: -4px 0; border-radius: 7px; }
            QSlider::handle:horizontal:hover { background: #aaaaaa; }
            QCheckBox { spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; border: 1px solid #333333; background: #1a1a1a; }
            QCheckBox::indicator:checked { background: #555555; border: 1px solid #777777; }
            QScrollArea { border: none; }
        """)
        
        self.setup_ui()
        self.ctrl_scroll.setWidget(self.ctrl_panel)
        self.ctrl_scroll.setWidgetResizable(True)
        self.splitter.addWidget(self.ctrl_scroll)
        self.splitter.setStretchFactor(0, 1) # Prefer scaling the preview
        self.splitter.setStretchFactor(1, 0) # Keep control panel as specified initially
        self.splitter.setSizes([1000, 560]) # Initial ratio
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.sync_all()

    def setup_ui(self):
        h_header = QHBoxLayout()
        self.header = QLabel("Gauge Designer Studio")
        self.header.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff; margin-bottom: 5px;")
        self.ui_reg['title'] = self.header; self.header._base_txt = "Gauge Designer Studio"
        
        self.btn_help = QPushButton("Help"); self.ui_reg['btn_help'] = self.btn_help; self.btn_help._base_txt = "Help"
        self.btn_help.setFixedWidth(80)
        self.btn_help.setStyleSheet("QPushButton { background: #002244; color: #66ccff; border: 1px solid #004488; } QPushButton:hover { background: #003366; color: #ffffff; }")
        self.btn_help.clicked.connect(self.show_help)
        
        h_header.addWidget(self.header); h_header.addStretch(); h_header.addWidget(self.btn_help)
        self.controls_layout.addLayout(h_header)
        
        self.tabs = QTabWidget()
        tabs = self.tabs
        
        # 1. Project
        t_proj = QWidget(); pl = QVBoxLayout(t_proj)
        pl.setContentsMargins(15, 15, 15, 15); pl.setSpacing(15)

        self.g_file = QGroupBox("Project Files"); self.ui_reg['g_file'] = self.g_file; self.g_file._base_txt = "Project Files"
        gl_file = QVBoxLayout(self.g_file); gl_file.setContentsMargins(15, 20, 15, 15)
        self.btn_save = QPushButton("Save Project (.gaugedesign)"); self.ui_reg['btn_save'] = self.btn_save; self.btn_save._base_txt = "Save Project (.gaugedesign)"; self.btn_save.clicked.connect(self.save_project)
        self.btn_load = QPushButton("Load Project (.gaugedesign)"); self.ui_reg['btn_load'] = self.btn_load; self.btn_load._base_txt = "Load Project (.gaugedesign)"; self.btn_load.clicked.connect(self.load_project)
        h_undo = QHBoxLayout()
        self.btn_undo = QPushButton("Undo"); self.ui_reg['btn_undo'] = self.btn_undo; self.btn_undo._base_txt = "Undo"; self.btn_undo.clicked.connect(self.undo)
        self.btn_redo = QPushButton("Redo"); self.ui_reg['btn_redo'] = self.btn_redo; self.btn_redo._base_txt = "Redo"; self.btn_redo.clicked.connect(self.redo)
        h_undo.addWidget(self.btn_undo); h_undo.addWidget(self.btn_redo)
        gl_file.addWidget(self.btn_save); gl_file.addWidget(self.btn_load); gl_file.addLayout(h_undo)

        self.g_exp = QGroupBox("Export Settings"); self.ui_reg['g_exp'] = self.g_exp; self.g_exp._base_txt = "Export Settings"
        gl_exp = QVBoxLayout(self.g_exp); gl_exp.setContentsMargins(15, 20, 15, 15); gl_exp.setSpacing(10)
        self.chk_exp_val = QCheckBox("Include Value Box in Export"); self.ui_reg['chk_exp_val'] = self.chk_exp_val; self.chk_exp_val._base_txt = "Include Value Box in Export"
        self.chk_exp_val.setChecked(True)
        self.chk_exp_needle = QCheckBox("Include Needle in Export"); self.ui_reg['chk_exp_needle'] = self.chk_exp_needle; self.chk_exp_needle._base_txt = "Include Needle in Export"
        self.chk_exp_needle.setChecked(True)
        self.exp_res = QSpinBox(); self.exp_res.setRange(200, 12000); self.exp_res.setValue(2000)
        
        h_res = QHBoxLayout(); self.lbl_res = QLabel("Export Width (PX):"); self.ui_reg['lbl_res'] = self.lbl_res; self.lbl_res._base_txt = "Export Width (PX)"; h_res.addWidget(self.lbl_res); h_res.addWidget(self.exp_res)
        self.btn_png = QPushButton("Export PNG High-Res"); self.ui_reg['btn_png'] = self.btn_png; self.btn_png._base_txt = "Export PNG High-Res"; self.btn_png.clicked.connect(self.export_png)
        self.btn_svg = QPushButton("Export SVG Vector"); self.ui_reg['btn_svg'] = self.btn_svg; self.btn_svg._base_txt = "Export SVG Vector"; self.btn_svg.clicked.connect(self.export_svg)
        self.btn_plotter = QPushButton("Export Plotter Cut-Lines (DXF)"); self.ui_reg['btn_plotter'] = self.btn_plotter; self.btn_plotter._base_txt = "Export Plotter Cut-Lines (DXF)"; self.btn_plotter.clicked.connect(self.export_plotter)
        self.btn_plotter.setStyleSheet("QPushButton { background: #3a2210; color: #ffb86c; border: 1px solid #663300; } QPushButton:hover { background: #4a2d15; }")
        gl_exp.addWidget(self.chk_exp_val); gl_exp.addWidget(self.chk_exp_needle); gl_exp.addLayout(h_res); gl_exp.addWidget(self.btn_png); gl_exp.addWidget(self.btn_svg); gl_exp.addWidget(self.btn_plotter)

        pl.addWidget(self.g_file)
        
        self.g_lang = QGroupBox("Language / Lingua"); self.ui_reg['g_lang'] = self.g_lang; self.g_lang._base_txt = "Language / Lingua"
        gl_lang = QVBoxLayout(self.g_lang); self.c_lang = QComboBox()
        self.c_lang.addItems(["English", "Italiano"])
        self.c_lang.currentTextChanged.connect(self.on_language_changed)
        gl_lang.addWidget(self.c_lang); pl.addWidget(self.g_lang)

        self.g_unit_cfg = QGroupBox("Measurement Units"); self.ui_reg['g_unit_cfg'] = self.g_unit_cfg; self.g_unit_cfg._base_txt = "Measurement Units"
        ul = QGridLayout(self.g_unit_cfg); ul.setContentsMargins(15, 20, 15, 15)
        self.c_unit_mode = QComboBox(); self.c_unit_mode.addItems(["Pixels (px)", "Centimeters (cm)"])
        self.c_unit_mode.currentTextChanged.connect(self.on_unit_mode_changed)
        self.c_px_cm = QDoubleSpinBox(); self.c_px_cm.setRange(1.0, 500.0); self.c_px_cm.setValue(37.8)
        self.c_px_cm.setSuffix(" px/cm"); self.c_px_cm.valueChanged.connect(self.on_px_cm_changed)
        self.lbl_unit1 = QLabel("Current Unit:"); self.ui_reg['lbl_unit1'] = self.lbl_unit1; self.lbl_unit1._base_txt = "Current Unit"
        self.lbl_unit2 = QLabel("Pixels per CM:"); self.ui_reg['lbl_unit2'] = self.lbl_unit2; self.lbl_unit2._base_txt = "Pixels per CM"
        ul.addWidget(self.lbl_unit1, 0, 0); ul.addWidget(self.c_unit_mode, 0, 1)
        ul.addWidget(self.lbl_unit2, 1, 0); ul.addWidget(self.c_px_cm, 1, 1)
        pl.addWidget(self.g_unit_cfg)

        pl.addWidget(self.g_exp); pl.addStretch()
        self.idx_proj = tabs.addTab(t_proj, "Project")

        # 2. Wallpaper & Geometry
        t_geo = QWidget(); gl = QGridLayout(t_geo)
        gl.setContentsMargins(15, 15, 15, 15); gl.setSpacing(15)
        self.chk_rim = QCheckBox("Enable Bezel Outer Rim"); self.ui_reg['chk_rim'] = self.chk_rim; self.chk_rim._base_txt = "Enable Bezel Outer Rim"; self.chk_rim.setChecked(True); self.chk_rim.toggled.connect(self.sync_all)
        self.bg_mode = QComboBox(); self.bg_mode.addItems(["Solid", "Radial Gradient", "Vertical Gradient", "Horizontal Gradient", "Carbon Fibre", "Cross Weave", "Grid Pattern", "Dense Dot Pattern"]); self.bg_mode.currentTextChanged.connect(self.sync_all)
        self.bg_mode.setCurrentText("Solid")
        self.btn_bg1 = QPushButton("Edge Color"); self.ui_reg['btn_bg1'] = self.btn_bg1; self.btn_bg1._base_txt = "Edge Color"; self.btn_bg1.clicked.connect(lambda: self.pick_color('bg1'))
        self.btn_bg2 = QPushButton("Center Color"); self.ui_reg['btn_bg2'] = self.btn_bg2; self.btn_bg2._base_txt = "Center Color"; self.btn_bg2.clicked.connect(lambda: self.pick_color('bg2'))
        self.c_size = self.create_linked_control(gl, "UI Pixels:", 200, 2000, 600, 3, is_size=True, key='lbl_pixels')
        self.c_min = self.create_double_spin(gl, "Minimum Value:", -10000, 0, 0, 4, key='lbl_min')
        self.c_max = self.create_double_spin(gl, "Maximum Value:", 1, 100000, 8000, 5, key='lbl_max')
        self.c_start_ang = self.create_linked_control(gl, "Start Angle:", -720, 720, 135, 6, is_size=False, key='lbl_start_a')
        self.c_end_ang = self.create_linked_control(gl, "End Angle:", -720, 720, 405, 7, is_size=False, key='lbl_end_a')
        gl.addWidget(self.chk_rim, 0, 0, 1, 3); self.lbl_bg = QLabel("BG Style:"); self.ui_reg['lbl_bg'] = self.lbl_bg; self.lbl_bg._base_txt = "BG Style"; gl.addWidget(self.lbl_bg, 1, 0); gl.addWidget(self.bg_mode, 1, 1, 1, 2)
        gl.addWidget(self.btn_bg1, 2, 0, 1, 1); gl.addWidget(self.btn_bg2, 2, 1, 1, 2)
        gl.setRowStretch(8, 1)
        tabs.addTab(t_geo, "Wallpaper"); self.ui_reg['tab_1'] = tabs.tabBar()
        # Note: tabs.setTabText directly instead of reg tab bar

        # 3. Needle Engineering
        t_ind = QScrollArea(); t_ind_w = QWidget(); il = QVBoxLayout(t_ind_w)
        il.setContentsMargins(15, 15, 15, 15); il.setSpacing(15)
        self.g_ind = QGroupBox("Indicator Point"); self.ui_reg['g_ind'] = self.g_ind; self.g_ind._base_txt = "Indicator Point"; il2 = QGridLayout(self.g_ind); self.ind_sh = QComboBox(); self.ind_sh.addItems(["Trapezoid", "Tapered", "Triangle", "Line"]); self.ind_sh.setCurrentText("Tapered"); self.c_ind_l = self.create_linked_control(il2, "Length:", 10, 500, 255, 1, is_size=True, key='lbl_len'); self.c_ind_t = self.create_linked_control(il2, "Thickness:", 1, 100, 11, 2, is_size=True, key='lbl_thick'); self.btn_c_ind = QPushButton("Pick Color"); self.ui_reg['btn_c_ind'] = self.btn_c_ind; self.btn_c_ind._base_txt = "Pick Color"; self.btn_c_ind.clicked.connect(lambda: self.pick_color('ind_p'))
        self.lbl_sh1 = QLabel("Shape:"); self.ui_reg['lbl_sh1'] = self.lbl_sh1; il2.addWidget(self.lbl_sh1, 0, 0); il2.addWidget(self.ind_sh, 0, 1, 1, 2); il2.addWidget(self.btn_c_ind, 3, 0, 1, 3); il.addWidget(self.g_ind)
        self.g_tail = QGroupBox("Counter-Weight Tail"); self.ui_reg['g_tail'] = self.g_tail; il3 = QGridLayout(self.g_tail); self.tail_sh = QComboBox(); self.tail_sh.addItems(["Trapezoid", "Inv-Trapezoid", "Inv-Triangle", "Rounded", "Rect"]); self.tail_sh.setCurrentText("Inv-Trapezoid"); self.c_tail_l = self.create_linked_control(il3, "Length:", 0, 500, 50, 1, is_size=True, key='lbl_len2'); self.c_tail_t = self.create_linked_control(il3, "Thickness:", 1, 100, 8, 2, is_size=True, key='lbl_thick2'); self.btn_c_tail = QPushButton("Pick Color"); self.ui_reg['btn_c_tail'] = self.btn_c_tail; self.btn_c_tail.clicked.connect(lambda: self.pick_color('ind_t'))
        self.lbl_sh2 = QLabel("Shape:"); self.ui_reg['lbl_sh2'] = self.lbl_sh2; il3.addWidget(self.lbl_sh2, 0, 0); il3.addWidget(self.tail_sh, 0, 1, 1, 2); il3.addWidget(self.btn_c_tail, 3, 0, 1, 3); il.addWidget(self.g_tail)
        self.g_hub = QGroupBox("Hub & Decor Ring"); self.ui_reg['g_hub'] = self.g_hub; il4 = QGridLayout(self.g_hub); self.pin_sh = QComboBox(); self.pin_sh.addItems(["Circle", "Hex"]); self.pin_sh.setCurrentText("Circle"); self.c_pin_r = self.create_linked_control(il4, "Pin Rad:", 0, 100, 20, 1, is_size=True, key='lbl_pin_r'); self.btn_c_pin = QPushButton("Pin Color"); self.ui_reg['btn_c_pin'] = self.btn_c_pin; self.btn_c_pin.clicked.connect(lambda: self.pick_color('ind_h')); self.decor_en = QCheckBox("Enable Decor Ring"); self.ui_reg['decor_en'] = self.decor_en; self.decor_en.setChecked(False); self.c_decor_r = self.create_linked_control(il4, "Ring Rad:", 0, 100, 10, 3, is_size=True, key='lbl_ring_r'); self.c_decor_t = self.create_linked_control(il4, "Ring Thick:", 1, 50, 3, 4, is_size=True, key='lbl_ring_t'); self.btn_c_decor = QPushButton("Ring Color"); self.ui_reg['btn_c_decor'] = self.btn_c_decor; self.btn_c_decor.clicked.connect(lambda: self.pick_color('ind_d')); self.btn_c_dot = QPushButton("Center Dot Color"); self.ui_reg['btn_c_dot'] = self.btn_c_dot; self.btn_c_dot.clicked.connect(lambda: self.pick_color('ind_dot'))
        self.lbl_sh3 = QLabel("Pin Shape:"); self.ui_reg['lbl_sh3'] = self.lbl_sh3; il4.addWidget(self.lbl_sh3, 0, 0); il4.addWidget(self.pin_sh, 0, 1, 1, 2); il4.addWidget(self.btn_c_pin, 2, 0, 1, 3); il4.addWidget(self.decor_en, 5, 0, 1, 3); il4.addWidget(self.btn_c_decor, 6, 0, 1, 3); il4.addWidget(self.btn_c_dot, 7, 0, 1, 3); il.addWidget(self.g_hub)
        self.c_inertia = self.create_linked_control(il, "Inertia Smoothing %:", 1, 100, 15, is_size=False, key='lbl_inertia')
        self.c_needle_bind = QComboBox()
        self.c_needle_bind.addItems(['Current Value', 'Sim: RPM', 'Sim: Speed KM/H', 'Sim: Temp C', 'Sim: Fuel Lvl', 'Sim: Turbo Bar'])
        self.c_needle_bind.currentTextChanged.connect(self.sync_all)
        self.g_bind = QGroupBox("Data Simulation Binding"); self.ui_reg['g_bind'] = self.g_bind; il5 = QVBoxLayout(self.g_bind); il5.addWidget(self.c_needle_bind); il.addWidget(self.g_bind)
        t_ind.setWidget(t_ind_w); t_ind.setWidgetResizable(True); tabs.addTab(t_ind, "Indicator")

        # 4. Typography & Data
        t_typo = QScrollArea(); t_typo_w = QWidget(); tl = QVBoxLayout(t_typo_w)
        tl.setContentsMargins(15, 15, 15, 15); tl.setSpacing(15)

        self.g_scale = QGroupBox("Scale Numbers"); self.ui_reg['g_scale'] = self.g_scale; gl_scale = QGridLayout(self.g_scale); gl_scale.setContentsMargins(15, 20, 15, 15)
        self.chk_rot = QCheckBox("Rotate Scale Numbers"); self.ui_reg['chk_rot'] = self.chk_rot; self.chk_rot.toggled.connect(self.sync_all)
        self.c_num_size = self.create_linked_control(gl_scale, "Font Size:", 5, 150, 20, 1, is_size=True, key='lbl_fs')
        self.c_num_dist = self.create_linked_control(gl_scale, "Distance From Center:", 10, 500, 219, 2, is_size=True, key='lbl_dist')
        
        self.num_mode = QComboBox(); self.num_mode.addItems(["All Regular", "Even Only", "Odd Only", "Odd Alt Size", "Even Alt Size"])
        self.num_mode.currentTextChanged.connect(self.sync_all)
        self.c_num_alt_size = self.create_linked_control(gl_scale, "Alt Size:", 5, 150, 12, 4, is_size=True, key='lbl_alt_s')
        self.c_mult = self.create_double_spin(gl_scale, "Value Multiplier:", 0.00100, 100000, 0.001, 5, 0.001, 5, key='lbl_mult')
        
        gl_scale.addWidget(self.chk_rot, 0, 0, 1, 3);
        self.lbl_patt = QLabel("Number Pattern:"); self.ui_reg['lbl_patt'] = self.lbl_patt; gl_scale.addWidget(self.lbl_patt, 3, 0); gl_scale.addWidget(self.num_mode, 3, 1, 1, 2)
        
        self.c_num_align = QComboBox(); self.c_num_align.addItems(["Center", "Left", "Right"]); self.c_num_align.currentTextChanged.connect(self.sync_all)
        self.lbl_num_align = QLabel("Text Alignment:"); self.ui_reg['lbl_num_align'] = self.lbl_num_align; self.lbl_num_align._base_txt = "Text Alignment"
        gl_scale.addWidget(self.lbl_num_align, 6, 0); gl_scale.addWidget(self.c_num_align, 6, 1, 1, 2)
        
        self.c_num_align_off = self.create_linked_control(gl_scale, "Alignment Offset:", -200, 200, 0, 7, is_size=True, key='lbl_align_off')
        
        tl.addWidget(self.g_scale)

        self.g_valbox = QGroupBox("Digital Value Box"); self.ui_reg['g_valbox'] = self.g_valbox; gl_valbox = QGridLayout(self.g_valbox); gl_valbox.setContentsMargins(15, 20, 15, 15)
        self.chk_val_box = QCheckBox("Enable Value Box"); self.ui_reg['chk_val_box'] = self.chk_val_box; self.chk_val_box.setChecked(True); self.chk_val_box.toggled.connect(self.sync_all)
        self.c_val_w = self.create_linked_control(gl_valbox, "Box Width:", 20, 500, 140, 1, is_size=True, key='lbl_box_w')
        self.c_val_h = self.create_linked_control(gl_valbox, "Box Height:", 10, 300, 45, 2, is_size=True, key='lbl_box_h')
        gl_valbox.addWidget(self.chk_val_box, 0, 0, 1, 3); tl.addWidget(self.g_valbox)

        self.g_fonts = QGroupBox("Custom Typography"); self.ui_reg['g_fonts'] = self.g_fonts; fl_fonts = QVBoxLayout(self.g_fonts); fl_fonts.setContentsMargins(15, 20, 15, 15)
        self.btn_f1 = QPushButton("Pick Scale Numbers Font"); self.ui_reg['btn_f1'] = self.btn_f1; self.btn_f1.clicked.connect(lambda: self.pick_font('scale'))
        self.btn_f2 = QPushButton("Pick Digital Box Font"); self.ui_reg['btn_f2'] = self.btn_f2; self.btn_f2.clicked.connect(lambda: self.pick_font('digital'))
        self.btn_f3 = QPushButton("Pick Unit Label Font"); self.ui_reg['btn_f3'] = self.btn_f3; self.btn_f3.clicked.connect(lambda: self.pick_font('unit'))
        fl_fonts.addWidget(self.btn_f1); fl_fonts.addWidget(self.btn_f2); fl_fonts.addWidget(self.btn_f3); tl.addWidget(self.g_fonts)

        self.g_unit = QGroupBox("Unit String Configuration"); self.ui_reg['g_unit'] = self.g_unit; gl_unit = QGridLayout(self.g_unit); gl_unit.setContentsMargins(15, 20, 15, 15)
        self.c_unit_text = QLineEdit(); self.c_unit_text.setText("RPM"); self.c_unit_text.textChanged.connect(self.sync_all)
        self.c_unit_x = self.create_linked_control(gl_unit, "X Offset (px):", -500, 500, 0, 1, is_size=True, key='lbl_off_x')
        self.c_unit_y = self.create_linked_control(gl_unit, "Y Offset (px):", -500, 500, -80, 2, is_size=True, key='lbl_off_y')
        self.lbl_unit_l = QLabel("Unit Text Label:"); self.ui_reg['lbl_unit_l'] = self.lbl_unit_l; gl_unit.addWidget(self.lbl_unit_l, 0, 0); gl_unit.addWidget(self.c_unit_text, 0, 1, 1, 2); tl.addWidget(self.g_unit)

        t_typo.setWidget(t_typo_w); t_typo.setWidgetResizable(True); tabs.addTab(t_typo, "Typography")
        
        # 5. Ticks (Tabbed Sub-menus)
        t_tick_page = QWidget(); tl_tick = QVBoxLayout(t_tick_page); tl_tick.setContentsMargins(5, 5, 5, 5)
        self.tick_tabs = QTabWidget()
        # Remove custom green style to match general theme
        
        # Major Tab
        t_maj = QWidget(); l_maj = QVBoxLayout(t_maj)
        self.btn_add_major = QPushButton("Add Major Set"); self.btn_add_major.clicked.connect(lambda: self.add_tick_set_ui(None, 'Major'))
        self.btn_add_major.setStyleSheet("QPushButton { background: #153315; color: #55ff55; border: 1px solid #225522; } QPushButton:hover { background: #1a441a; }")
        l_maj.addWidget(self.btn_add_major)
        sc_maj = QScrollArea(); sc_maj.setWidgetResizable(True); cw_maj = QWidget(); self.major_layout = QVBoxLayout(cw_maj); self.major_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sc_maj.setWidget(cw_maj); l_maj.addWidget(sc_maj); self.tick_tabs.addTab(t_maj, "Major")
 
        # Medium/Minor Tab
        t_med = QWidget(); l_med = QVBoxLayout(t_med)
        self.btn_add_med = QPushButton("Add Medium Set"); self.btn_add_med.clicked.connect(lambda: self.add_tick_set_ui(None, 'Minor'))
        self.btn_add_med.setStyleSheet("QPushButton { background: #153315; color: #55ff55; border: 1px solid #225522; } QPushButton:hover { background: #1a441a; }")
        l_med.addWidget(self.btn_add_med)
        sc_med = QScrollArea(); sc_med.setWidgetResizable(True); cw_med = QWidget(); self.med_layout = QVBoxLayout(cw_med); self.med_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sc_med.setWidget(cw_med); l_med.addWidget(sc_med); self.tick_tabs.addTab(t_med, "Minor")
 
        # Sub-Minor/Small Tab
        t_sm = QWidget(); l_sm = QVBoxLayout(t_sm)
        self.btn_add_small = QPushButton("Add Small Set"); self.btn_add_small.clicked.connect(lambda: self.add_tick_set_ui(None, 'Sub-Minor'))
        self.btn_add_small.setStyleSheet("QPushButton { background: #153315; color: #55ff55; border: 1px solid #225522; } QPushButton:hover { background: #1a441a; }")
        l_sm.addWidget(self.btn_add_small)
        sc_sm = QScrollArea(); sc_sm.setWidgetResizable(True); cw_sm = QWidget(); self.small_layout = QVBoxLayout(cw_sm); self.small_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        sc_sm.setWidget(cw_sm); l_sm.addWidget(sc_sm); self.tick_tabs.addTab(t_sm, "Sub-Minor")
 
        tl_tick.addWidget(self.tick_tabs)
        tabs.addTab(t_tick_page, "Ticks")

        # Initialize UI with defaults
        for ts in self.gauge.tick_sets:
            self.add_tick_set_ui(ts, ts['type'])
        
        # 6. Colored Arcs
        t_arcs = QWidget(); al = QVBoxLayout(t_arcs)
        self.btn_add_arc = QPushButton("Add New Arc"); self.ui_reg['btn_add_arc'] = self.btn_add_arc; self.btn_add_arc.clicked.connect(lambda: self.add_arc_ui(None))
        self.btn_add_arc.setStyleSheet("QPushButton { background: #153315; color: #55ff55; border: 1px solid #225522; } QPushButton:hover { background: #1a441a; }")
        al.addWidget(self.btn_add_arc)
        self.arcs_scroll = QScrollArea(); self.arcs_scroll.setWidgetResizable(True)
        self.arcs_container = QWidget(); self.arcs_layout = QVBoxLayout(self.arcs_container)
        self.arcs_layout.setAlignment(Qt.AlignmentFlag.AlignTop); self.arcs_layout.setSpacing(10)
        self.arcs_scroll.setWidget(self.arcs_container); al.addWidget(self.arcs_scroll)
        tabs.addTab(t_arcs, "Arcs")

        # 7. Custom Sections (Unified List)
        t_sec = QWidget(); sl = QVBoxLayout(t_sec); sl.setContentsMargins(10, 10, 10, 10)
        self.btn_add_sec = QPushButton("Add New Section"); self.ui_reg['btn_add_sec'] = self.btn_add_sec; self.btn_add_sec.clicked.connect(lambda *args: self.add_sec_ui(None))
        self.btn_add_sec.setStyleSheet("QPushButton { background: #153315; color: #55ff55; border: 1px solid #225522; } QPushButton:hover { background: #1a441a; }")
        sl.addWidget(self.btn_add_sec)
        
        self.sec_scroll = QScrollArea(); self.sec_scroll.setWidgetResizable(True)
        self.sec_container = QWidget(); self.sections_layout = QVBoxLayout(self.sec_container)
        self.sections_layout.setAlignment(Qt.AlignmentFlag.AlignTop); self.sections_layout.setSpacing(10)
        self.sec_scroll.setWidget(self.sec_container); sl.addWidget(self.sec_scroll)
        tabs.addTab(t_sec, "Sections")

        self.t_geo = t_geo; self.t_ind = t_ind; self.t_typo = t_typo; self.t_tick = t_tick_page
        self.t_arc = t_arcs; self.t_sec = t_sec

        # 8. Live Simulation Suite (Integrated advanced options)
        t_sim_tab = QWidget(); sl_sim = QVBoxLayout(t_sim_tab); sl_sim.setContentsMargins(10, 10, 10, 10)
        
        self.g_sim_basic = QGroupBox("Manual Testing Suite"); test_ly = QGridLayout(self.g_sim_basic); test_ly.setContentsMargins(15, 20, 15, 15)
        self.c_sim_val = QDoubleSpinBox(); self.c_sim_val.setRange(-10000, 100000); self.c_sim_val.setValue(0)
        self.c_sim_sld = QSlider(Qt.Orientation.Horizontal); self.c_sim_sld.setRange(0, 10000)
        self.c_sim_sld.setStyleSheet("QSlider::handle:horizontal { background: #777777; } QSlider::handle:horizontal:hover { background: #aaaaaa; }")
        self.c_sim_val.valueChanged.connect(self.on_sim_box_changed)
        self.c_sim_sld.valueChanged.connect(self.on_sim_sld_changed)
        self.chk_show_needle = QCheckBox("Show Needle While Editing"); self.ui_reg['chk_show_needle'] = self.chk_show_needle; self.chk_show_needle._base_txt = "Show Needle While Editing"; self.chk_show_needle.setChecked(True); self.chk_show_needle.toggled.connect(self.sync_all)
        self.lbl_sim1 = QLabel("Manual Value:"); test_ly.addWidget(self.lbl_sim1, 0, 0); test_ly.addWidget(self.c_sim_val, 0, 1); test_ly.addWidget(self.c_sim_sld, 1, 0, 1, 2); test_ly.addWidget(self.chk_show_needle, 1, 2)
        sl_sim.addWidget(self.g_sim_basic)
        
        self.g_sim_udp = QGroupBox("OutSim UDP Advanced Telemetry"); udp_ly = QGridLayout(self.g_sim_udp); udp_ly.setContentsMargins(15, 20, 15, 15)
        self.sim_ip = QLineEdit("192.168.1.50"); self.sim_port = QSpinBox(); self.sim_port.setRange(1000, 65535); self.sim_port.setValue(9999)
        self.btn_toggle_udp = QPushButton("Start UDP Telemetry (OutSim)"); self.btn_toggle_udp.setCheckable(True); self.btn_toggle_udp.clicked.connect(self.toggle_udp)
        udp_ly.addWidget(QLabel("OutSim IP:"), 0, 0); udp_ly.addWidget(self.sim_ip, 0, 1); udp_ly.addWidget(QLabel("OutSim Port:"), 1, 0); udp_ly.addWidget(self.sim_port, 1, 1); udp_ly.addWidget(self.btn_toggle_udp, 2, 0, 1, 2)
        sl_sim.addWidget(self.g_sim_udp)
        
        self.chk_ontop = QCheckBox("Stay Always in Overlay (Always on Top)"); self.chk_ontop.toggled.connect(self.toggle_on_top)
        self.lbl_ontop_note = QLabel("(Short flash is normal; signifies activation)"); self.lbl_ontop_note.setStyleSheet("color: #888888; font-style: italic; font-size: 11px;")
        self.ui_reg['lbl_ontop_note'] = self.lbl_ontop_note; self.lbl_ontop_note._base_txt = "(Short flash is normal; signifies activation)"
        hl_ontop = QHBoxLayout(); hl_ontop.addWidget(self.chk_ontop); hl_ontop.addWidget(self.lbl_ontop_note); hl_ontop.addStretch()
        sl_sim.addLayout(hl_ontop)
        sl_sim.addStretch()
        tabs.addTab(t_sim_tab, "Simulation")
        self.t_sim = t_sim_tab
        self.controls_layout.addWidget(tabs)

        self.btn_lock = QPushButton("Lock Dashboard Resize"); self.ui_reg['btn_lock'] = self.btn_lock; self.btn_lock._base_txt = "Lock Dashboard Resize"
        self.btn_lock.setCheckable(True)
        self.btn_lock.clicked.connect(self.toggle_resize_lock)
        self.controls_layout.addWidget(self.btn_lock)
        
        self.retranslate_ui()

    def open_adv_sim(self):
        pass # Integrated into Simulation tab

    def toggle_on_top(self, checked):
        if checked: self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else: self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def toggle_udp(self, checked):
        if checked:
            self.telemetry_thread = TelemetryThread(self.sim_ip.text(), self.sim_port.value())
            self.telemetry_thread.telemetry_updated.connect(self.gauge.update_telemetry)
            self.telemetry_thread.start()
            self.btn_toggle_udp.setText("Stop UDP Telemetry")
            self.btn_toggle_udp.setStyleSheet("QPushButton { background: #331515; color: #ff5555; }")
        else:
            if self.telemetry_thread: self.telemetry_thread.stop(); self.telemetry_thread = None
            self.btn_toggle_udp.setText("Start UDP Telemetry (OutSim)")
            self.btn_toggle_udp.setStyleSheet("")

    def closeEvent(self, event):
        if self.telemetry_thread: self.telemetry_thread.stop(); self.telemetry_thread = None
        event.accept()

    def on_sim_box_changed(self, v):
        if self._is_syncing: return
        self._is_syncing = True; rng = self.gauge.max_value - self.gauge.min_value
        if rng != 0: self.c_sim_sld.setValue(int(((v - self.gauge.min_value) / rng) * 10000))
        self.gauge.target_value = v; self._is_syncing = False

    def on_sim_sld_changed(self, v):
        if self._is_syncing: return
        self._is_syncing = True; rng = self.gauge.max_value - self.gauge.min_value
        target = self.gauge.min_value + (v / 10000.0) * rng
        self.c_sim_val.setValue(target); self.gauge.target_value = target; self._is_syncing = False

    def add_arc_ui(self, arc_data=None):
        if arc_data is None:
            arc_data = {'name': '', 'en': True, 'min': 0, 'max': 1000, 'r': 260, 't': 10, 'col': QColor("#a6e3a1"), 'layer': 'Bottom'}
            self.gauge.arcs.append(arc_data)
        
        w = QGroupBox(arc_data.get('name') or f"Arc {len(self.arc_widgets)+1}"); l = QGridLayout(w)
        chk_en = QCheckBox("Enable"); chk_en.setChecked(arc_data.get('en', True)); chk_en.toggled.connect(self.sync_arcs)
        c_name = QLineEdit(arc_data.get('name', '')); c_name.setPlaceholderText(f"Arc {len(self.arc_widgets)+1}")
        c_min = QDoubleSpinBox(); c_min.setRange(-10000, 100000); c_min.setValue(arc_data['min']); c_min.valueChanged.connect(self.sync_arcs)
        c_max = QDoubleSpinBox(); c_max.setRange(-10000, 100000); c_max.setValue(arc_data['max']); c_max.valueChanged.connect(self.sync_arcs)
        c_r = QDoubleSpinBox(); c_r.setRange(10, 500); c_r.setValue(float(arc_data['r'])); c_r.setDecimals(0); c_r.valueChanged.connect(self.sync_arcs)
        c_t = QDoubleSpinBox(); c_t.setRange(1, 100); c_t.setValue(float(arc_data['t'])); c_t.setDecimals(0); c_t.valueChanged.connect(self.sync_arcs)
        c_l = QComboBox(); c_l.addItems(["Bottom", "Top"]); c_l.setCurrentText(arc_data.get('layer', 'Bottom')); c_l.currentTextChanged.connect(self.sync_arcs)
        btn_c = QPushButton("Color"); btn_d = QPushButton("Delete")
        
        lbl_n = QLabel("Name:"); lbl_n._base_txt = "Name"; l.addWidget(lbl_n,0,1); l.addWidget(c_name,0,2,1,2)
        lbl_min = QLabel("Minimum Value:"); lbl_min._base_txt = "Minimum Value"; l.addWidget(lbl_min,1,0); l.addWidget(c_min,1,1)
        lbl_max = QLabel("Maximum Value:"); lbl_max._base_txt = "Maximum Value"; l.addWidget(lbl_max,1,2); l.addWidget(c_max,1,3)
        lbl_r = QLabel("Radius:"); lbl_r._base_txt = "Radius"; l.addWidget(lbl_r,2,0); l.addWidget(c_r,2,1)
        lbl_t = QLabel("Thickness:"); lbl_t._base_txt = "Thickness"; l.addWidget(lbl_t,2,2); l.addWidget(c_t,2,3)
        lbl_l = QLabel("Layer:"); lbl_l._base_txt = "Layer"; l.addWidget(lbl_l,3,0); l.addWidget(c_l,3,1)
        l.addWidget(btn_c,3,2); l.addWidget(btn_d,3,3)
        l.addWidget(chk_en,0,0)
        btn_d.setStyleSheet("QPushButton { background: #331515; color: #ff5555; border: 1px solid #552222; } QPushButton:hover { background: #441a1a; }")
        
        # Registration for Unit Scaling
        self.size_controls.append({'spn': c_r, 'lbl': None, 'min': 10, 'max': 500, 'base_txt': 'Radius'})
        self.size_controls.append({'spn': c_t, 'lbl': None, 'min': 1, 'max': 100, 'base_txt': 'Thickness'})
        
        ud = {'w': w, 'en': chk_en, 'name': c_name, 'min': c_min, 'max': c_max, 'r': c_r, 't': c_t, 'layer': c_l, 'btn_c': btn_c, 'btn_d': btn_d, 'data': arc_data}
        # Remember controls for cleanup
        ud['size_ctrls'] = [c_r, c_t]
        c_name.editingFinished.connect(lambda _x=ud: _x['w'].setTitle(_x['name'].text() or f"Arc {self.arc_widgets.index(_x)+1}"))
        c_name.textChanged.connect(self.sync_arcs)
        self.arc_widgets.append(ud); self.arcs_layout.addWidget(w)
        btn_c.clicked.connect(lambda *args, x=ud: self.pick_arc_color(x))
        btn_d.clicked.connect(lambda *args, x=ud: self.delete_arc(x))
        self.sync_arcs()

    def reindex_arcs(self):
        for i, ud in enumerate(self.arc_widgets):
            if not ud['name'].text(): ud['w'].setTitle(f"Arc {i+1}")

    def sync_arcs(self, *args, **kwargs):
        if hasattr(self, 'undo_timer') and not self._is_undoing: self.undo_timer.start()
        if self._is_syncing: return
        self.is_dirty = True
        self._is_syncing = True
        for ud in self.arc_widgets:
            ud['data'].update({
                'name': ud['name'].text(), 
                'en': ud['en'].isChecked(), 
                'min': ud['min'].value(), 
                'max': ud['max'].value(), 
                'r': self.unit_to_px(ud['r'].value()), 
                't': self.unit_to_px(ud['t'].value()), 
                'layer': ud['layer'].currentText()
            })
        self.gauge.update(); self._is_syncing = False

    def pick_arc_color(self, ud):
        c = QColorDialog.getColor(parent=self)
        if c.isValid(): ud['data']['col'] = c; self.sync_arcs(); self.gauge.update()

    def delete_arc(self, ud):
        if ud in self.arc_widgets: self.arc_widgets.remove(ud)
        ud['w'].deleteLater()
        if 'size_ctrls' in ud:
            self.size_controls = [c for c in self.size_controls if c.get('spn') not in ud['size_ctrls']]
        if ud['data'] in self.gauge.arcs: self.gauge.arcs.remove(ud['data'])
        self.reindex_arcs()
        self.sync_arcs()

    def add_sec_ui(self, sec_data=None):
        if sec_data is None:
            sec_data = {'name': '', 'en': True, 'target': 'Minor', 'min': 5000, 'max': 8000, 'sh': 'Triangle', 'r': 280, 'l': 20, 't': 6, 'col': QColor("#ff0000"), 'fs': 24}
            self.gauge.sections.append(sec_data)
        
        w = QGroupBox(sec_data.get('name') or f"Section {len(self.sec_widgets)+1}"); l = QGridLayout(w)
        chk_en = QCheckBox("Enable"); chk_en.setChecked(sec_data.get('en', True)); chk_en.toggled.connect(self.sync_secs)
        c_name = QLineEdit(sec_data.get('name', '')); c_name.setPlaceholderText(f"Section {len(self.sec_widgets)+1}")
        c_tar = QComboBox(); c_tar.addItems(["Major", "Minor", "Sub-Minor", "text"]); c_tar.setCurrentText(sec_data['target']); c_tar.currentTextChanged.connect(self.sync_secs)
        c_min = QDoubleSpinBox(); c_min.setRange(-10000, 100000); c_min.setValue(sec_data['min']); c_min.valueChanged.connect(self.sync_secs)
        c_max = QDoubleSpinBox(); c_max.setRange(-10000, 100000); c_max.setValue(sec_data['max']); c_max.valueChanged.connect(self.sync_secs)
        c_sh = QComboBox(); c_sh.addItems(["Dot", "Rectangle", "Rounded Rectangle", "Line", "Triangle"]); c_sh.setCurrentText(sec_data['sh']); c_sh.currentTextChanged.connect(self.sync_secs)
        c_r = QDoubleSpinBox(); c_r.setRange(10, 500); c_r.setValue(float(sec_data['r'])); c_r.setDecimals(0); c_r.valueChanged.connect(self.sync_secs)
        c_l = QDoubleSpinBox(); c_l.setRange(1, 150); c_l.setValue(float(sec_data['l'])); c_l.setDecimals(0); c_l.valueChanged.connect(self.sync_secs)
        c_t = QDoubleSpinBox(); c_t.setRange(1, 100); c_t.setValue(float(sec_data['t'])); c_t.setDecimals(0); c_t.valueChanged.connect(self.sync_secs)
        c_fs = QDoubleSpinBox(); c_fs.setRange(5, 150); c_fs.setValue(float(sec_data['fs'])); c_fs.setDecimals(0); c_fs.valueChanged.connect(self.sync_secs)
        
        btn_c = QPushButton("Color"); btn_d = QPushButton("Delete")
        lbl_n = QLabel("Name:"); lbl_n._base_txt = "Name"; l.addWidget(lbl_n,0,1,1,1); l.addWidget(c_name,0,2, 1, 2)
        lbl_tar = QLabel("Target:"); lbl_tar._base_txt = "Target"; l.addWidget(lbl_tar,1,0); l.addWidget(c_tar,1,1, 1, 3)
        lbl_min = QLabel("Minimum Value:"); lbl_min._base_txt = "Minimum Value"; l.addWidget(lbl_min,2,0); l.addWidget(c_min,2,1)
        lbl_max = QLabel("Maximum Value:"); lbl_max._base_txt = "Maximum Value"; l.addWidget(lbl_max,2,2); l.addWidget(c_max,2,3)
        lbl_sh = QLabel("Shape:"); lbl_sh._base_txt = "Shape"; l.addWidget(lbl_sh,3,0); l.addWidget(c_sh,3,1)
        lbl_r = QLabel("Radius:"); lbl_r._base_txt = "Radius"; l.addWidget(lbl_r,3,2); l.addWidget(c_r,3,3)
        lbl_l = QLabel("Length:"); lbl_l._base_txt = "Length"; l.addWidget(lbl_l,4,0); l.addWidget(c_l,4,1)
        lbl_t = QLabel("Thickness:"); lbl_t._base_txt = "Thickness"; l.addWidget(lbl_t,4,2); l.addWidget(c_t,4,3)
        lbl_fs = QLabel("Text Font Size:"); lbl_fs._base_txt = "Text Font Size"; l.addWidget(lbl_fs,5,0); l.addWidget(c_fs,5,1)
        l.addWidget(btn_c,5,2); l.addWidget(btn_d,5,3); l.addWidget(chk_en,0,0)
        btn_d.setStyleSheet("QPushButton { background: #331515; color: #ff5555; border: 1px solid #552222; } QPushButton:hover { background: #441a1a; }")
        
        # Registration for Unit Scaling
        self.size_controls.append({'spn': c_r, 'lbl': None, 'min': 10, 'max': 500, 'base_txt': 'Radius'})
        self.size_controls.append({'spn': c_l, 'lbl': None, 'min': 1, 'max': 150, 'base_txt': 'Length'})
        self.size_controls.append({'spn': c_t, 'lbl': None, 'min': 1, 'max': 100, 'base_txt': 'Thickness'})
        self.size_controls.append({'spn': c_fs, 'lbl': None, 'min': 5, 'max': 150, 'base_txt': 'Text Font Size'})

        ud = {'w': w, 'en': chk_en, 'name': c_name, 'target': c_tar, 'min': c_min, 'max': c_max, 'sh': c_sh, 'r': c_r, 'l': c_l, 't': c_t, 'fs': c_fs, 'btn_c': btn_c, 'btn_d': btn_d, 'data': sec_data}
        ud['size_ctrls'] = [c_r, c_l, c_t, c_fs]
        c_name.editingFinished.connect(lambda _x=ud: _x['w'].setTitle(_x['name'].text() or f"Section {self.sec_widgets.index(_x)+1}"))
        c_name.textChanged.connect(self.sync_secs)
        self.sec_widgets.append(ud)
        
        self.sections_layout.addWidget(w)
        
        btn_c.clicked.connect(lambda *args, x=ud: self.pick_sec_color(x))
        btn_d.clicked.connect(lambda *args, x=ud: self.delete_sec(x))
        self.sync_secs()

    def sync_secs(self, *args, **kwargs):
        if hasattr(self, 'undo_timer') and not self._is_undoing: self.undo_timer.start()
        if self._is_syncing: return
        self.is_dirty = True
        self._is_syncing = True
        for ud in self.sec_widgets:
            ud['data'].update({
                'name': ud['name'].text(), 
                'en': ud['en'].isChecked(), 
                'target': ud['target'].currentText(), 
                'min': ud['min'].value(), 
                'max': ud['max'].value(), 
                'sh': ud['sh'].currentText(), 
                'r': self.unit_to_px(ud['r'].value()), 
                'l': self.unit_to_px(ud['l'].value()), 
                't': self.unit_to_px(ud['t'].value()), 
                'fs': ud['fs'].value()
            })
        self.gauge.update(); self._is_syncing = False

    def pick_sec_color(self, ud):
        c = QColorDialog.getColor(parent=self)
        if c.isValid(): ud['data']['col'] = c; self.sync_secs(); self.gauge.update()

    def reindex_secs(self):
        for i, ud in enumerate(self.sec_widgets):
            if not ud['name'].text(): ud['w'].setTitle(f"Section {i+1}")

    def delete_sec(self, ud):
        if ud in self.sec_widgets: self.sec_widgets.remove(ud)
        ud['w'].deleteLater()
        if 'size_ctrls' in ud:
            self.size_controls = [c for c in self.size_controls if c.get('spn') not in ud['size_ctrls']]
        if ud['data'] in self.gauge.sections: self.gauge.sections.remove(ud['data'])
        self.reindex_secs()
        self.sync_secs()

    def add_tick_set_ui(self, ts_data=None, ts_type='Major'):
        if ts_data is None:
            ts_data = {'name': 'New Set', 'type': ts_type, 'en': True, 'cnt': 10, 'sh': 'Line', 'r': 260, 'l': 15, 't': 3, 'col': QColor("#ffffff"), 'layer': 'Bottom'}
            self.gauge.tick_sets.append(ts_data)
        
        w = QGroupBox(ts_data.get('name') or "Tick Set"); l = QGridLayout(w)
        chk_en = QCheckBox("Enabled"); chk_en.setChecked(ts_data.get('en', True)); chk_en.toggled.connect(self.sync_ticks)
        c_name = QLineEdit(ts_data.get('name', '')); c_name.textChanged.connect(self.sync_ticks)
        c_type = QComboBox(); c_type.addItems(["Major", "Minor", "Sub-Minor"]); c_type.setCurrentText(ts_data.get('type', 'Major')); c_type.currentTextChanged.connect(self.sync_ticks)
        c_cnt = QSpinBox(); c_cnt.setRange(0, 500); c_cnt.setValue(ts_data.get('cnt', 10)); c_cnt.valueChanged.connect(self.sync_ticks)
        c_sh = QComboBox(); c_sh.addItems(["Dot", "Rectangle", "Rounded Rectangle", "Line", "Triangle"]); c_sh.setCurrentText(ts_data.get('sh', 'Line')); c_sh.currentTextChanged.connect(self.sync_ticks)
        c_r = QDoubleSpinBox(); c_r.setRange(10, 500); c_r.setValue(float(ts_data.get('r', 260))); c_r.setDecimals(0); c_r.valueChanged.connect(self.sync_ticks)
        c_l = QDoubleSpinBox(); c_l.setRange(1, 150); c_l.setValue(float(ts_data.get('l', 15))); c_l.setDecimals(0); c_l.valueChanged.connect(self.sync_ticks)
        c_t = QDoubleSpinBox(); c_t.setRange(1, 100); c_t.setValue(float(ts_data.get('t', 3))); c_t.setDecimals(0); c_t.valueChanged.connect(self.sync_ticks)
        c_lay = QComboBox(); c_lay.addItems(["Bottom", "Top"]); c_lay.setCurrentText(ts_data.get('layer', 'Bottom')); c_lay.currentTextChanged.connect(self.sync_ticks)
        
        btn_c = QPushButton("Color"); btn_d = QPushButton("Delete")
        btn_d.setStyleSheet("QPushButton { background: #331515; color: #ff5555; border: 1px solid #552222; } QPushButton:hover { background: #441a1a; }")

        l.addWidget(chk_en, 0, 0)
        lbl_name = QLabel("Name:"); self.ui_reg['lbl_tick_name'] = lbl_name; lbl_name._base_txt = "Name"
        l.addWidget(lbl_name, 0, 1); l.addWidget(c_name, 0, 2, 1, 2)
        
        lbl_sh = QLabel("Shape:"); self.ui_reg['lbl_tick_sh'] = lbl_sh; lbl_sh._base_txt = "Shape"
        l.addWidget(lbl_sh, 1, 0); l.addWidget(c_sh, 1, 1)
        
        lbl_cnt = QLabel("Count:"); self.ui_reg['lbl_tick_cnt'] = lbl_cnt; lbl_cnt._base_txt = "Count"
        l.addWidget(lbl_cnt, 1, 2); l.addWidget(c_cnt, 1, 3)

        l.addWidget(QLabel("Radius:"), 2, 0); l.addWidget(c_r, 2, 1); l.addWidget(QLabel("Length:"), 2, 2); l.addWidget(c_l, 2, 3)
        l.addWidget(QLabel("Thickness:"), 3, 0); l.addWidget(c_t, 3, 1); l.addWidget(QLabel("Layer:"), 3, 2); l.addWidget(c_lay, 3, 3)
        l.addWidget(btn_c, 4, 0, 1, 2); l.addWidget(btn_d, 4, 2, 1, 2)

        self.size_controls.append({'spn': c_r, 'lbl': None, 'min': 10, 'max': 500, 'base_txt': 'Radius'})
        self.size_controls.append({'spn': c_l, 'lbl': None, 'min': 1, 'max': 150, 'base_txt': 'Length'})
        self.size_controls.append({'spn': c_t, 'lbl': None, 'min': 1, 'max': 100, 'base_txt': 'Thickness'})

        ud = {'w': w, 'en': chk_en, 'name': c_name, 'type_combo': c_type, 'cnt': c_cnt, 'sh': c_sh, 'r': c_r, 'l': c_l, 't': c_t, 'lay': c_lay, 'btn_c': btn_c, 'btn_d': btn_d, 'data': ts_data}
        ud['size_ctrls'] = [c_r, c_l, c_t]
        self.tick_widgets.append(ud)
        
        target_layout = self.major_layout if ts_type == 'Major' else (self.med_layout if ts_type == 'Minor' else self.small_layout)
        target_layout.addWidget(w)
        
        btn_c.clicked.connect(lambda *args, x=ud: self.pick_tick_color(x))
        btn_d.clicked.connect(lambda *args, x=ud: self.delete_tick_set(x))

    def sync_ticks(self):
        if hasattr(self, 'undo_timer') and not self._is_undoing: self.undo_timer.start()
        if self._is_syncing: return
        self.is_dirty = True
        self._is_syncing = True
        for ud in self.tick_widgets:
            old_type = ud['data'].get('type')
            new_type = ud['type_combo'].currentText()
            
            # Tab Migration Logic
            if old_type != new_type:
                target_layout = self.major_layout if new_type == 'Major' else (self.med_layout if new_type == 'Minor' else self.small_layout)
                target_layout.addWidget(ud['w'])
                ud['data']['type'] = new_type

            ud['data'].update({
                'name': ud['name'].text(), 'en': ud['en'].isChecked(), 'type': new_type,
                'cnt': ud['cnt'].value(), 'sh': ud['sh'].currentText(), 'r': self.unit_to_px(ud['r'].value()),
                'l': self.unit_to_px(ud['l'].value()), 't': self.unit_to_px(ud['t'].value()), 'layer': ud['lay'].currentText()
            })
        self.gauge.update(); self._is_syncing = False

    def pick_tick_color(self, ud):
        c = QColorDialog.getColor(parent=self)
        if c.isValid(): ud['data']['col'] = c; self.sync_ticks(); self.gauge.update()

    def delete_tick_set(self, ud):
        if ud in self.tick_widgets: self.tick_widgets.remove(ud)
        ud['w'].deleteLater()
        if 'size_ctrls' in ud:
            self.size_controls = [c for c in self.size_controls if c.get('spn') not in ud['size_ctrls']]
        if ud['data'] in self.gauge.tick_sets: self.gauge.tick_sets.remove(ud['data'])
        self.sync_ticks()




    def pick_color(self, target):
        c = QColorDialog.getColor(parent=self)
        if c.isValid():
            if target == 'bg1': self.gauge.bg_color_1 = c
            elif target == 'bg2': self.gauge.bg_color_2 = c
            elif target == 'ind_p': self.gauge.needle_ind['col'] = c
            elif target == 'ind_t': self.gauge.needle_tail['col'] = c
            elif target == 'ind_h': self.gauge.needle_pin['col'] = c
            elif target == 'ind_d': self.gauge.needle_decor['col'] = c
            elif target == 'ind_dot': self.gauge.center_dot_col = c
            self.sync_all()

    def pick_font(self, target):
        cur = self.gauge.text['font'] if target == 'scale' else (self.gauge.val_box['font'] if target == 'digital' else self.gauge.unit_label['font'])
        dlg = QFontDialog(self)
        dlg.setCurrentFont(cur)
        if dlg.exec():
            new_font = QFont(dlg.selectedFont())
            if target == 'scale': self.gauge.text['font'] = new_font
            elif target == 'digital': self.gauge.val_box['font'] = new_font
            else: self.gauge.unit_label['font'] = new_font
            self.sync_all()

    def create_linked_control(self, layout, label, min_v, max_v, init_v, row=None, is_size=False, key=None):
        sld = QSlider(Qt.Orientation.Horizontal); sld.setRange(min_v, max_v); sld.setValue(int(init_v))
        if is_size: spn = QDoubleSpinBox(); spn.setRange(float(min_v), float(max_v)); spn.setValue(float(init_v)); spn.setDecimals(2)
        else: spn = QSpinBox(); spn.setRange(int(min_v), int(max_v)); spn.setValue(int(init_v))
        spn.setFixedWidth(70)
        
        # Consistent Base Text (Clean original English)
        base = label.replace(" (px):", "").replace(" (cm):", "").replace(":", "").strip()
        lbl_obj = QLabel(label)
        lbl_obj._base_txt = base
        lbl_obj._is_size = is_size
        if key: self.ui_reg[key] = lbl_obj

        if row is not None: layout.addWidget(lbl_obj, row, 0); layout.addWidget(sld, row, 1); layout.addWidget(spn, row, 2)
        else: layout.addWidget(lbl_obj); layout.addWidget(sld); layout.addWidget(spn)

        if is_size:
            self.size_controls.append({'sld': sld, 'spn': spn, 'lbl': lbl_obj, 'min': min_v, 'max': max_v, 'base_txt': base})
            sld.valueChanged.connect(lambda v: spn.setValue(self.px_to_unit(v)))
            spn.valueChanged.connect(lambda v: sld.setValue(int(self.unit_to_px(v))))
            sld.valueChanged.connect(self.sync_all)
        else:
            sld.valueChanged.connect(spn.setValue); spn.valueChanged.connect(sld.setValue); sld.valueChanged.connect(self.sync_all)

        return sld

    def create_double_spin(self, layout, label, min_v, max_v, init_v, row, step=1.0, decimals=2, is_size=False, key=None):
        spn = QDoubleSpinBox(); spn.setRange(min_v, max_v); spn.setValue(init_v); spn.setSingleStep(step); spn.setDecimals(decimals)
        base = label.replace(" (px):", "").replace(" (cm):", "").replace(":", "").strip()
        lbl_obj = QLabel(label)
        lbl_obj._base_txt = base
        lbl_obj._is_size = is_size
        if key: self.ui_reg[key] = lbl_obj
            
        layout.addWidget(lbl_obj, row, 0); layout.addWidget(spn, row, 1, 1, 2)
        
        if is_size:
            self.size_controls.append({'spn': spn, 'lbl': lbl_obj, 'min': min_v, 'max': max_v, 'base_txt': base})
        
        spn.valueChanged.connect(self.sync_all)
        return spn

    def px_to_unit(self, px): return px / self.px_per_cm if self.unit_mode == "cm" else px
    def unit_to_px(self, val): return val * self.px_per_cm if self.unit_mode == "cm" else val

    def on_unit_mode_changed(self, txt):
        new_mode = "cm" if "Centimeter" in txt else "px"
        if new_mode == self.unit_mode: return
        self.unit_mode = new_mode
        self.update_all_unit_ui()

    def on_px_cm_changed(self, v):
        self.px_per_cm = v
        if self.unit_mode == "cm": self.update_all_unit_ui()

    def update_all_unit_ui(self):
        self._is_syncing = True
        u = "cm" if self.unit_mode == "cm" else "px"
        for ctrl in self.size_controls:
            # Update Label
            if ctrl.get('lbl') is not None:
                u = "cm" if self.unit_mode == "cm" else "px"
                base = ctrl['base_txt']
                # Use re-translation logic for correctness
                trans = self.translations.get(base, {}).get("it", base) if self.lang == "it" else base
                ctrl['lbl'].setText(f"{trans} ({u}):")
            
            # Update SpinBox Range & Value
            if 'spn' in ctrl:
                spn = ctrl['spn']
                curr_px = self.unit_to_px(spn.value()) if hasattr(self, '_prev_unit_mode') and self._prev_unit_mode != self.unit_mode else (spn.value() if self.unit_mode == "px" else spn.value() * getattr(self, '_prev_px_per_cm', self.px_per_cm))
                # Correction: The Slider 'sld' always holds pixels.
                if 'sld' in ctrl: curr_px = ctrl['sld'].value()
                
                spn.blockSignals(True)
                if isinstance(spn, QDoubleSpinBox):
                    spn.setDecimals(2 if self.unit_mode == "cm" else 0)
                spn.setRange(self.px_to_unit(ctrl['min']), self.px_to_unit(ctrl['max']))
                spn.setValue(self.px_to_unit(curr_px))
                spn.blockSignals(False)
        self._is_syncing = False
        self.sync_all()


    def toggle_resize_lock(self, locked):
        self.splitter.handle(1).setEnabled(not locked)
        self.btn_lock.setText("Unlock Dashboard Resize" if locked else "Lock Dashboard Resize")
        if locked: self.btn_lock.setStyleSheet("QPushButton { background: #333333; color: #aaaaaa; }")
        else: self.btn_lock.setStyleSheet("")

    def sync_all(self):
        if hasattr(self, 'undo_timer') and not self._is_undoing: self.undo_timer.start()
        if self._is_syncing: return
        self.is_dirty = True
        self._is_syncing = True; g = self.gauge
        
        # Geometry sliders always hold Pixel values
        g.gauge_w = self.c_size.value()
        g.gauge_h = self.c_size.value()
        g.bg_mode = self.bg_mode.currentText()
            
        g.setFixedSize(g.gauge_w, g.gauge_h)
        g.rim['en'] = self.chk_rim.isChecked()
        g.min_value, g.max_value = self.c_min.value(), self.c_max.value()
        g.start_angle, g.end_angle = self.c_start_ang.value(), self.c_end_ang.value()
        if hasattr(self, 'c_mult'): g.scale_multiplier = self.c_mult.value()
        
        g.text['fs'] = self.c_num_size.value()
        g.text['alt_fs'] = self.c_num_alt_size.value()
        g.text['mode'] = self.num_mode.currentText()
        g.text['dist'] = self.c_num_dist.value()
        g.text['rot'] = self.chk_rot.isChecked()
        g.text['align'] = self.c_num_align.currentText()
        g.text['align_offset'] = self.c_num_align_off.value()
        g.val_box['en'] = self.chk_val_box.isChecked()
        g.unit_label['text'] = self.c_unit_text.text()
        g.unit_label['x'] = self.c_unit_x.value()
        g.unit_label['y'] = self.c_unit_y.value()
        g.val_box['suffix'] = ' ' + self.c_unit_text.text() if self.c_unit_text.text() else ''
        g.val_box['w'] = self.c_val_w.value()
        g.val_box['h'] = self.c_val_h.value()
        
        g.show_needle = self.chk_show_needle.isChecked()
        
        g.anim_inertia = self.c_inertia.value() / 100.0
        g.needle_ind.update({'sh': self.ind_sh.currentText(), 'l': self.c_ind_l.value(), 't': self.c_ind_t.value()})
        g.needle_tail.update({'sh': self.tail_sh.currentText(), 'l': self.c_tail_l.value(), 't': self.c_tail_t.value()})
        g.needle_pin.update({'sh': self.pin_sh.currentText(), 'r': self.c_pin_r.value()})
        g.needle_decor.update({'en': self.decor_en.isChecked(), 'r': self.c_decor_r.value(), 't': self.c_decor_t.value()})
        
        self.sync_ticks()
        
        for cb in[self.ind_sh, self.tail_sh, self.pin_sh]: 
            try: cb.currentIndexChanged.disconnect(self.sync_all) 
            except: pass
            cb.currentIndexChanged.connect(self.sync_all)
            
        g.update(); self._is_syncing = False

    # ── Shared export-done dialog ────────────────────────────────────────────
    def show_export_done(self, path):
        """Show a success dialog with an Open Folder button."""
        is_it = (self.lang == "it")
        dlg = QDialog(self)
        dlg.setWindowTitle("Esportazione completata" if is_it else "Export Successful")
        dlg.setMinimumWidth(440)
        dlg.setStyleSheet("""
            QDialog  { background: #1a1a1a; color: #e0e0e0; font-family: 'Segoe UI'; }
            QLabel   { color: #cccccc; font-size: 13px; padding: 4px; }
            QPushButton { background: #222222; border: 1px solid #444; border-radius: 5px;
                          padding: 8px 18px; font-weight: bold; color: #e0e0e0; }
            QPushButton:hover { background: #333; border-color: #777; }
            QPushButton#btn_folder { background: #1a3a1a; color: #55ff55;
                                     border: 1px solid #336633; }
            QPushButton#btn_folder:hover { background: #1f4a1f; }
        """)
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(22, 18, 22, 18)
        vl.setSpacing(12)
        title_lbl = QLabel("✅  " + ("File esportato con successo:" if is_it else "File exported successfully:"))
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        path_lbl = QLabel(path)
        path_lbl.setWordWrap(True)
        path_lbl.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        vl.addWidget(title_lbl)
        vl.addWidget(path_lbl)
        hl = QHBoxLayout(); hl.setSpacing(10)
        btn_folder = QPushButton("📂  " + ("Apri Cartella" if is_it else "Open Folder"))
        btn_folder.setObjectName("btn_folder")
        btn_ok = QPushButton("OK")
        btn_folder.clicked.connect(lambda: os.startfile(os.path.dirname(os.path.abspath(path))))
        btn_ok.clicked.connect(dlg.accept)
        hl.addWidget(btn_folder); hl.addStretch(); hl.addWidget(btn_ok)
        vl.addLayout(hl)
        dlg.exec()

    def export_png(self):
        res_w = self.exp_res.value()
        res_h = int(res_w * (self.gauge.gauge_h / self.gauge.gauge_w))
        path, _ = QFileDialog.getSaveFileName(self, "Export PNG", "", "PNG (*.png)")
        if path:
            img = QImage(res_w, res_h, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img)
            self.gauge.paint_gauge(p, res_w, res_h, exp_needle=self.chk_exp_needle.isChecked(), exp_val=self.chk_exp_val.isChecked())
            p.end()
            if img.save(path):
                self.show_export_done(path)

    def export_svg(self):
        res_w = self.exp_res.value()
        res_h = int(res_w * (self.gauge.gauge_h / self.gauge.gauge_w))
        path, _ = QFileDialog.getSaveFileName(self, "Export SVG", "", "SVG (*.svg)")
        if path:
            gen = QSvgGenerator()
            gen.setFileName(path)
            gen.setSize(QSize(res_w, res_h))
            gen.setViewBox(QRectF(0, 0, res_w, res_h))
            p = QPainter(gen)
            self.gauge.paint_gauge(p, res_w, res_h, exp_needle=self.chk_exp_needle.isChecked(), exp_val=self.chk_exp_val.isChecked())
            p.end()
            self.show_export_done(path)

    def export_plotter(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Plotter Cut-Lines (DXF)", "", "DXF (*.dxf)")
        if not path: return

        from PyQt6.QtGui import QCursor
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        try:
            g = self.gauge

            # ── Physical-scale helper ────────────────────────────────────────────
            # px_per_cm is user-set (default 37.8 px = 1 cm).
            # All internal values are stored in px. Conversion: px → (10/px_per_cm) mm
            def px_to_mm(px):
                return (px / self.px_per_cm) * 10.0

            # Qt angles: 0 = 3-o'clock, clockwise.
            # DXF angles: 0 = 3-o'clock, counter-clockwise.
            def qt_to_dxf_angle(qt_deg):
                return (90.0 - qt_deg) % 360.0

            doc = ezdxf.new('R2010')
            msp = doc.modelspace()
            span = g.end_angle - g.start_angle

            doc.layers.new(name='CUT',  dxfattribs={'color': 1})   # red  - geometry
            doc.layers.new(name='TEXT', dxfattribs={'color': 3})   # green - text outlines

            def cut_a(): return {'layer': 'CUT',  'color': 256}
            def txt_a(): return {'layer': 'TEXT', 'color': 256}

            # 1. Outer circle (gauge boundary)
            outer_r_mm = px_to_mm(g.gauge_w / 2.0)
            msp.add_circle((0, 0), outer_r_mm, dxfattribs=cut_a())

            # 2. Bezel rim
            if g.rim.get('en', True):
                rim_t_mm = px_to_mm(g.rim.get('t', 8))
                rim_r_mm = outer_r_mm - rim_t_mm / 2.0
                if rim_r_mm > 0:
                    msp.add_circle((0, 0), rim_r_mm, dxfattribs=cut_a())

            # 3. Tick marks
            for ts in g.tick_sets:
                if not ts.get('en', True): continue
                total_steps = g.calculate_tick_count(ts)
                if total_steps <= 0: continue
                r_mm       = px_to_mm(ts.get('r', 260))
                l_mm       = px_to_mm(ts.get('l', 15))
                t_mm       = px_to_mm(ts.get('t', 3))
                sh         = ts.get('sh', 'Line')
                inner_r_mm = r_mm - l_mm
                for i in range(total_steps + 1):
                    qt_angle = g.start_angle + (i * span / total_steps)
                    rad = math.radians(qt_to_dxf_angle(qt_angle))
                    cos_a = math.cos(rad); sin_a = math.sin(rad)
                    ox = r_mm * cos_a;       oy = r_mm * sin_a
                    ix = inner_r_mm * cos_a; iy = inner_r_mm * sin_a
                    if sh in ('Line', 'Rectangle', 'Rounded Rectangle'):
                        msp.add_line((ix, iy), (ox, oy), dxfattribs=cut_a())
                    elif sh == 'Dot':
                        msp.add_circle(((ox+ix)/2.0, (oy+iy)/2.0), t_mm/2.0, dxfattribs=cut_a())
                    elif sh == 'Triangle':
                        perp = rad + math.pi / 2.0; w = t_mm / 2.0
                        p1 = (ox, oy)
                        p2 = (ix + math.cos(perp)*w, iy + math.sin(perp)*w)
                        p3 = (ix - math.cos(perp)*w, iy - math.sin(perp)*w)
                        msp.add_lwpolyline([p1, p2, p3, p1], dxfattribs=cut_a())
                QApplication.processEvents()

            # 4. Colored arcs
            rng = g.max_value - g.min_value
            if rng > 0:
                for arc in g.arcs:
                    if not arc.get('en', True): continue
                    arc_r_mm = px_to_mm(arc.get('r', 260))
                    arc_min  = max(g.min_value, arc.get('min', 0))
                    arc_max  = min(g.max_value, arc.get('max', 1000))
                    if arc_min >= arc_max: continue
                    qt_start  = g.start_angle + ((arc_min - g.min_value) / rng) * span
                    qt_end    = g.start_angle + ((arc_max - g.min_value) / rng) * span
                    dxf_end   = qt_to_dxf_angle(qt_start)
                    dxf_start = qt_to_dxf_angle(qt_end)
                    msp.add_arc((0, 0), arc_r_mm, dxf_start, dxf_end, dxfattribs=cut_a())

            # 5. Full scale arc outline
            scale_r_mm    = px_to_mm(g.tick_sets[0].get('r', 260) if g.tick_sets else 260)
            dxf_arc_end   = qt_to_dxf_angle(g.start_angle)
            dxf_arc_start = qt_to_dxf_angle(g.end_angle)
            msp.add_arc((0, 0), scale_r_mm, dxf_arc_start, dxf_arc_end, dxfattribs=cut_a())

            # 6. Numbers & typography: SVG → DXF polylines
            # Strategy: render the gauge to a temp SVG in plotter_mode (every text label
            # becomes an outlined <path> element via QPainterPath::addText).
            # Then use standard XML parsing to grab every <path d="..."> attribute
            # directly as a string, feed it into svgelements.Path() for segment
            # iteration, and emit each sub-path as a DXF LWPOLYLINE on the TEXT layer.
            tmp_svg = None
            try:
                import tempfile
                import xml.etree.ElementTree as _ET
                from svgelements import Path as SvgPath

                svg_w  = int(g.gauge_w)
                svg_h  = int(g.gauge_h)
                cx_svg = svg_w / 2.0   # canvas centre

                with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tf:
                    tmp_svg = tf.name

                # Paint gauge in plotter_mode → text becomes outlined paths
                gen2 = QSvgGenerator()
                gen2.setFileName(tmp_svg)
                gen2.setSize(QSize(svg_w, svg_h))
                gen2.setViewBox(QRectF(0, 0, svg_w, svg_h))
                old_plotter = g.plotter_mode
                g.plotter_mode = True
                pp = QPainter(gen2)
                g.paint_gauge(pp, svg_w, svg_h, exp_needle=False, exp_val=False)
                pp.end()
                g.plotter_mode = old_plotter

                QApplication.processEvents()

                # Scale: 1 SVG-pixel → real mm
                svg_scale = 10.0 / self.px_per_cm

                def s2d(x_s, y_s):
                    """SVG pixel → DXF mm, centred & Y-flipped."""
                    return ((x_s - cx_svg) * svg_scale,
                            -(y_s - cx_svg) * svg_scale)

                N = 12   # line segments per Bézier curve

                def cubic(p0, p1, p2, p3):
                    out = []
                    for k in range(N + 1):
                        t = k / N; mt = 1 - t
                        out.append((
                            mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0],
                            mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
                        ))
                    return out

                def quad(p0, p1, p2):
                    out = []
                    for k in range(N + 1):
                        t = k / N; mt = 1 - t
                        out.append((
                            mt**2*p0[0] + 2*mt*t*p1[0] + t**2*p2[0],
                            mt**2*p0[1] + 2*mt*t*p1[1] + t**2*p2[1]
                        ))
                    return out

                def flush_pts(pts):
                    if len(pts) >= 2:
                        msp.add_lwpolyline(
                            [s2d(x, y) for x, y in pts],
                            dxfattribs=txt_a()
                        )

                # ── Parse SVG with standard XML ─────────────────────────────────
                tree = _ET.parse(tmp_svg)
                root = tree.getroot()

                # ElementTree prefixes tags with the namespace URI
                def iter_paths(node):
                    tag = node.tag.split('}')[-1] if '}' in node.tag else node.tag
                    if tag == 'path':
                        yield node
                    for child in node:
                        yield from iter_paths(child)

                for path_elem in iter_paths(root):
                    d_str = path_elem.get('d', '').strip()
                    if not d_str:
                        continue
                    try:
                        # Parse the raw d-string into a Path object and iterate segs
                        parsed = SvgPath(d_str)
                        segs = list(parsed)
                        if not segs:
                            continue

                        sub = []; cx_p, cy_p = 0.0, 0.0
                        for seg in segs:
                            st = type(seg).__name__

                            if st == 'Move':
                                flush_pts(sub); sub = []
                                cx_p = float(seg.end.x)
                                cy_p = float(seg.end.y)
                                sub.append((cx_p, cy_p))

                            elif st == 'Line':
                                cx_p = float(seg.end.x)
                                cy_p = float(seg.end.y)
                                sub.append((cx_p, cy_p))

                            elif st == 'QuadraticBezier':
                                pts = quad(
                                    (cx_p, cy_p),
                                    (float(seg.control.x), float(seg.control.y)),
                                    (float(seg.end.x), float(seg.end.y))
                                )
                                sub.extend(pts[1:])
                                cx_p, cy_p = float(seg.end.x), float(seg.end.y)

                            elif st == 'CubicBezier':
                                pts = cubic(
                                    (cx_p, cy_p),
                                    (float(seg.control1.x), float(seg.control1.y)),
                                    (float(seg.control2.x), float(seg.control2.y)),
                                    (float(seg.end.x),      float(seg.end.y))
                                )
                                sub.extend(pts[1:])
                                cx_p, cy_p = sub[-1]

                            elif st == 'Close':
                                if sub:
                                    sub.append(sub[0])   # Close the loop
                                flush_pts(sub); sub = []
                                cx_p, cy_p = 0.0, 0.0

                        flush_pts(sub)   # emit any remaining open sub-path

                    except Exception:
                        pass   # skip malformed individual paths

                QApplication.processEvents()

            except Exception as svg_err:
                print(f"[SVG->DXF] Typography error: {svg_err}")
            finally:
                if tmp_svg:
                    try: os.unlink(tmp_svg)
                    except Exception: pass

            # Save DXF
            doc.saveas(path)
            QApplication.restoreOverrideCursor()
            self.show_export_done(path)

        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Export Error", f"Failed to export DXF:\n{str(e)}")



    def get_state_dict(self):
        g = self.gauge
        def s_val(v): return {"px": v, "cm": round(v / self.px_per_cm, 4)}
        return {
            'bg1': g.bg_color_1.name(), 'bg2': g.bg_color_2.name(), 'bg_mode': g.bg_mode,
            'unit_mode': self.unit_mode, 'px_per_cm': self.px_per_cm, 'lang': self.lang,
            'min': g.min_value, 'max': g.max_value, 'scale_mult': getattr(g, 'scale_multiplier', 0.001),
            'start_angle': g.start_angle, 'end_angle': g.end_angle,
            'num_fs': s_val(g.text['fs']), 'num_alt_fs': s_val(g.text.get('alt_fs', 12)), 
            'num_mode': g.text.get('mode', 'All Regular'), 'num_rot': g.text['rot'], 
            'num_align': g.text.get('align', 'Center'), 'num_align_off': s_val(g.text.get('align_offset', 0)),
            'num_dist': s_val(g.text['dist']), 'num_font': g.text['font'].toString(),
            'val_box': {'en': g.val_box['en'], 'w': s_val(g.val_box['w']), 'h': s_val(g.val_box['h']), 'font': g.val_box['font'].toString()},
            'unit_text': g.unit_label['text'], 'unit_font': g.unit_label['font'].toString(), 
            'unit_x': s_val(g.unit_label.get('x', 0)), 'unit_y': s_val(g.unit_label.get('y', -80)),
            'gauge_w': s_val(getattr(g, 'gauge_w', 600)), 'gauge_h': s_val(getattr(g, 'gauge_h', 600)),
            'show_needle_editing': g.show_needle,
            'needle_bind_target': getattr(g, 'needle_bind_target', 'Current Value'),
            'arcs': [{'name': a.get('name', ''), 'en': a.get('en', True), 'min': a['min'], 'max': a['max'], 'r': s_val(a['r']), 't': s_val(a['t']), 'col': a['col'].name(), 'layer': a.get('layer', 'Bottom')} for a in g.arcs],
            'tick_sets': [{'name': t.get('name', ''), 'en': t.get('en', True), 'type': t['type'], 'cnt': t['cnt'], 'sh': t['sh'], 'r': s_val(t['r']), 'l': s_val(t['l']), 't': s_val(t['t']), 'col': t['col'].name(), 'layer': t.get('layer', 'Bottom')} for t in g.tick_sets],
            'sections': [{'name': s.get('name', ''), 'en': s.get('en', True), 'target': s['target'], 'min': s['min'], 'max': s['max'], 'sh': s['sh'], 'r': s_val(s['r']), 'l': s_val(s['l']), 't': s_val(s['t']), 'col': s['col'].name(), 'fs': s_val(s['fs'])} for s in g.sections],
            'needle_ind': {**{k: s_val(v) if k in ['l', 't'] else v for k, v in g.needle_ind.items()}, 'col': g.needle_ind['col'].name()}, 
            'needle_tail': {**{k: s_val(v) if k in ['l', 't'] else v for k, v in g.needle_tail.items()}, 'col': g.needle_tail['col'].name()}, 
            'needle_pin': {**{k: s_val(v) if k in ['r'] else v for k, v in g.needle_pin.items()}, 'col': g.needle_pin['col'].name()}, 
            'needle_decor': {**{k: s_val(v) if k in ['r', 't'] else v for k, v in g.needle_decor.items()}, 'col': g.needle_decor['col'].name()}
        }

    def load_state_dict(self, d):
        self._is_syncing = True
        self._is_undoing = True
        g = self.gauge

        def l_val(entry, fallback=0):
            if isinstance(entry, dict) and 'px' in entry: return entry['px']
            return float(entry) if entry is not None else fallback

        g.bg_color_1 = QColor(d.get('bg1', g.bg_color_1.name()))
        g.bg_color_2 = QColor(d.get('bg2', g.bg_color_2.name()))
        self.unit_mode = d.get('unit_mode', 'px')
        self.px_per_cm = d.get('px_per_cm', 37.8)
        self.lang = d.get('lang', 'en')
        self.c_lang.setCurrentText("Italiano" if self.lang == "it" else "English")
        self.c_unit_mode.setCurrentText("Centimeters (cm)" if self.unit_mode == "cm" else "Pixels (px)")
        self.c_px_cm.setValue(self.px_per_cm)
        if 'center_dot_col' in d: g.center_dot_col = QColor(d['center_dot_col'])
        if 'needle_ind' in d: g.needle_ind['col'] = QColor(d['needle_ind'].get('col', g.needle_ind['col'].name()))
        if 'needle_tail' in d: g.needle_tail['col'] = QColor(d['needle_tail'].get('col', g.needle_tail['col'].name()))
        if 'needle_pin' in d: g.needle_pin['col'] = QColor(d['needle_pin'].get('col', g.needle_pin['col'].name()))
        if 'needle_decor' in d: g.needle_decor['col'] = QColor(d['needle_decor'].get('col', g.needle_decor['col'].name()))
        if 'ticks' in d:
            for k in['big', 'med', 'small']:
                if k in d['ticks']:
                    g.ticks[k]['col'] = QColor(d['ticks'][k].get('col', g.ticks[k]['col'].name()))

        self.c_size.setValue(int(l_val(d.get('gauge_w'), 600)))
        bg_m = d.get('bg_mode', 'Radial Gradient')
        if bg_m == "Carbon Fibre": bg_m = "Cross Weave" # Migration: old Carbon Fibre was what's now Cross Weave
        self.bg_mode.setCurrentText(bg_m)
        self.c_min.setValue(d.get('min', 0.0))
        self.c_max.setValue(d.get('max', 8000.0))
        self.c_start_ang.setValue(d.get('start_angle', 135))
        self.c_end_ang.setValue(d.get('end_angle', 405))
        self.c_mult.setValue(d.get('scale_mult', 0.001))
        self.c_num_size.setValue(int(l_val(d.get('num_fs'), 18)))
        self.c_num_alt_size.setValue(int(l_val(d.get('num_alt_fs'), 12)))
        self.num_mode.setCurrentText(d.get('num_mode', 'All Regular'))
        self.c_num_dist.setValue(int(l_val(d.get('num_dist'), 210)))
        self.chk_rot.setChecked(d.get('num_rot', False))
        self.c_num_align.setCurrentText(d.get('num_align', 'Center'))
        self.c_num_align_off.setValue(int(l_val(d.get('num_align_off'), 0)))
        self.c_needle_bind.setCurrentText(d.get('needle_bind_target', 'Current Value'))
        self.c_unit_text.setText(d.get('unit_text', 'RPM'))
        self.c_unit_x.setValue(int(l_val(d.get('unit_x'), 0)))
        self.c_unit_y.setValue(int(l_val(d.get('unit_y'), -80)))
        self.chk_show_needle.setChecked(d.get('show_needle_editing', True))
        if 'num_font' in d: f = QFont(); f.fromString(d['num_font']); self.gauge.text['font'] = f
        if 'unit_font' in d: f = QFont(); f.fromString(d['unit_font']); self.gauge.unit_label['font'] = f
        
        # Ticks Migration & Loading
        for ud in list(self.tick_widgets): ud['w'].deleteLater()
        # Clean size_controls from dynamically created widgets
        dynamic_spns = []
        for ud in self.tick_widgets + self.arc_widgets + self.sec_widgets:
            if 'size_ctrls' in ud: dynamic_spns.extend(ud['size_ctrls'])
        self.size_controls = [c for c in self.size_controls if c.get('spn') not in dynamic_spns]
        
        self.tick_widgets.clear(); self.gauge.tick_sets.clear()
        if 'tick_sets' in d:
            for t in d['tick_sets']:
                ts_type = t.get('type', 'Major')
                ts = {'name': t.get('name', ''), 'en': t.get('en', True), 'type': ts_type, 'cnt': t.get('cnt', 10), 'sh': t.get('sh', 'Line'), 'r': l_val(t.get('r'), 260), 'l': l_val(t.get('l'), 15), 't': l_val(t.get('t'), 3), 'col': QColor(t.get('col', '#ffffff')), 'layer': t.get('layer', 'Bottom')}
                self.gauge.tick_sets.append(ts); self.add_tick_set_ui(ts, ts_type)
        elif 'ticks' in d:
            # Migration from old format
            for k, name, internal_type in [('big', 'Major', 'Major'), ('med', 'Minor', 'Minor'), ('small', 'Sub-Minor', 'Sub-Minor')]:
                old = d['ticks'][k]
                ts = {'name': name, 'type': internal_type, 'en': old.get('en', True), 'cnt': old.get('cnt', 10), 'sh': old.get('sh', 'Line'), 'r': l_val(old.get('r'), 260), 'l': l_val(old.get('l'), 15), 't': l_val(old.get('t'), 3), 'col': QColor(old.get('col', '#ffffff')), 'layer': 'Bottom'}
                self.gauge.tick_sets.append(ts); self.add_tick_set_ui(ts, internal_type)

        for ud in list(self.arc_widgets): self.delete_arc(ud)
        self.gauge.arcs.clear()
        for a in d.get('arcs', []):
            arc_data = {'name': a.get('name', ''), 'en': a.get('en', True), 'min': a.get('min', 0), 'max': a.get('max', 1000), 'r': l_val(a.get('r'), 260), 't': l_val(a.get('t'), 10), 'col': QColor(a.get('col', '#a6e3a1')), 'layer': a.get('layer', 'Bottom')}
            self.gauge.arcs.append(arc_data)
            self.add_arc_ui(arc_data)
        
        for ud in list(self.sec_widgets): self.delete_sec(ud)
        self.gauge.sections.clear()
        for s in d.get('sections', []):
            target = s.get('target', 'Minor')
            # Migrate old targets
            if target == 'big': target = 'Major'
            elif target == 'med': target = 'Minor'
            elif target == 'small': target = 'Sub-Minor'
            
            sd = {'name': s.get('name', ''), 'en': s.get('en', True), 'target': target, 'min': s.get('min', 0), 'max': s.get('max', 1000), 'sh': s.get('sh', 'Triangle'), 'r': l_val(s.get('r'), 280), 'l': l_val(s.get('l'), 15), 't': l_val(s.get('t'), 3), 'col': QColor(s.get('col', '#ff0000')), 'fs': l_val(s.get('fs'), 18)}
            self.gauge.sections.append(sd)
            self.add_sec_ui(sd)
            
        if 'val_box' in d:
            self.chk_val_box.setChecked(d['val_box'].get('en', True))
            self.c_val_w.setValue(int(l_val(d['val_box'].get('w'), 160)))
            self.c_val_h.setValue(int(l_val(d['val_box'].get('h'), 70)))
            if 'font' in d['val_box']: f = QFont(); f.fromString(d['val_box']['font']); self.gauge.val_box['font'] = f

        if 'needle_ind' in d:
            self.ind_sh.setCurrentText(d['needle_ind'].get('sh', 'Trapezoid'))
            self.c_ind_l.setValue(int(l_val(d['needle_ind'].get('l'), 240)))
            self.c_ind_t.setValue(int(l_val(d['needle_ind'].get('t'), 8)))
        if 'needle_tail' in d:
            self.tail_sh.setCurrentText(d['needle_tail'].get('sh', 'Trapezoid'))
            self.c_tail_l.setValue(int(l_val(d['needle_tail'].get('l'), 80)))
            self.c_tail_t.setValue(int(l_val(d['needle_tail'].get('t'), 16)))
        if 'needle_pin' in d:
            self.pin_sh.setCurrentText(d['needle_pin'].get('sh', 'Circle'))
            self.c_pin_r.setValue(int(l_val(d['needle_pin'].get('r'), 15)))
        if 'needle_decor' in d:
            self.decor_en.setChecked(d['needle_decor'].get('en', True))
            self.c_decor_r.setValue(int(l_val(d['needle_decor'].get('r'), 8)))
            self.c_decor_t.setValue(int(l_val(d['needle_decor'].get('t'), 3)))


        self._is_syncing = False
        self._is_undoing = False
        self.retranslate_ui()
        self.sync_all()

    def push_state(self):
        if hasattr(self, '_is_undoing') and self._is_undoing: return
        state = self.get_state_dict()
        if not self.history or json.dumps(self.history[self.history_index], sort_keys=True) != json.dumps(state, sort_keys=True):
            self.history = self.history[:self.history_index + 1]
            self.history.append(state)
            if len(self.history) > 30: self.history.pop(0)
            else: self.history_index += 1

    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.load_state_dict(self.history[self.history_index])

    def redo(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.load_state_dict(self.history[self.history_index])

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "Gauge Design (*.gaugedesign)")
        if path:
            with open(path, 'w') as f: json.dump(self.get_state_dict(), f)
            self.is_dirty = False

    def on_language_changed(self, txt):
        self.lang = "it" if "Italiano" in txt else "en"
        self.retranslate_ui()
        if self.help_window: self.help_window.retranslate()

    def show_help(self):
        if not self.help_window:
            self.help_window = HelpWindow(self)
        self.help_window.show()
        self.help_window.raise_()
        self.help_window.activateWindow()

    def get_tr(self, text):
        mapping = {
            "Gauge Designer Studio": {"it": "Studio Design Tachimetri"},
            "Project Files": {"it": "File del Progetto"},
            "Save Project (.gaugedesign)": {"it": "Salva Progetto (.gaugedesign)"},
            "Load Project (.gaugedesign)": {"it": "Carica Progetto (.gaugedesign)"},
            "Undo": {"it": "Annulla"},
            "Redo": {"it": "Ripristina"},
            "Export Settings": {"it": "Impostazioni Esportazione"},
            "Include Value Box in Export": {"it": "Includi Box Valore nell'Esportazione"},
            "Include Needle in Export": {"it": "Includi Lancetta nell'Esportazione"},
            "Export Width (PX):": {"it": "Larghezza Esportazione (PX):"},
            "Export PNG High-Res": {"it": "Esporta PNG Alta Risoluzione"},
            "Export SVG Vector": {"it": "Esporta SVG Vettoriale"},
            "Export Plotter Cut-Lines (DXF)": {"it": "Esporta Plotter Cut-Lines (DXF)"},
            "Language / Lingua": {"it": "Lingua / Language"},
            "Measurement Units": {"it": "Unità di Misura"},
            "Current Unit:": {"it": "Unità Corrente:"},
            "Pixels per CM:": {"it": "Pixel per CM:"},
            "Enable Bezel Outer Rim": {"it": "Abilita Ghiera Esterna"},
            "BG Style:": {"it": "Stile Sfondo:"},
            "Edge Color": {"it": "Colore Bordo"},
            "Center Color": {"it": "Colore Centrale"},
            "UI Pixels": {"it": "Pixel UI"},
            "Minimum Value": {"it": "Valore Minimo"},
            "Maximum Value": {"it": "Valore Massimo"},
            "Start Angle": {"it": "Angolo Inizio"},
            "End Angle": {"it": "Angolo Fine"},
            "Indicator Point": {"it": "Punto Indicatore"},
            "Length": {"it": "Lunghezza"},
            "Thickness": {"it": "Spessore"},
            "Shape:": {"it": "Forma:"},
            "Pick Color": {"it": "Scegli Colore"},
            "Counter-Weight Tail": {"it": "Contrappeso Lancetta"},
            "Hub & Decor Ring": {"it": "Mozzo e Anello Decorato"},
            "Pin Rad": {"it": "Raggio Perno"},
            "Pin Color": {"it": "Colore Perno"},
            "Enable Decor Ring": {"it": "Abilita Anello Decorativo"},
            "Ring Rad": {"it": "Raggio Anello"},
            "Ring Thick": {"it": "Spessore Anello"},
            "Ring Color": {"it": "Colore Anello"},
            "Center Dot Color": {"it": "Colore Punto Centrale"},
            "Inertia Smoothing %": {"it": "Smoothing Inerzia %"},
            "Data Simulation Binding": {"it": "Simulazione Binding Dati"},
            "Scale Numbers": {"it": "Numeri della Scala"},
            "Rotate Scale Numbers": {"it": "Ruota Numeri Scala"},
            "Font Size": {"it": "Dimensione Font"},
            "Distance From Center": {"it": "Distanza dal Centro"},
            "Number Pattern:": {"it": "Pattern Numeri:"},
            "Alt Size": {"it": "Dimensione Alt."},
            "Value Multiplier": {"it": "Moltiplicatore Valore"},
            "Digital Value Box": {"it": "Box Valore Digitale"},
            "Enable Value Box": {"it": "Abilita Box Valore"},
            "Box Width": {"it": "Larghezza Box"},
            "Box Height": {"it": "Altezza Box"},
            "Custom Typography": {"it": "Tipografia Personalizzata"},
            "Pick Scale Numbers Font": {"it": "Scegli Font Numeri Scala"},
            "Pick Digital Box Font": {"it": "Scegli Font Box Digitale"},
            "Pick Unit Label Font": {"it": "Scegli Font Etichetta Unità"},
            "Unit String Configuration": {"it": "Configurazione Stringa Unità"},
            "Unit Text Label:": {"it": "Etichetta Testo Unità:"},
            "X Offset (px)": {"it": "Offset X (px)"},
            "Y Offset (px)": {"it": "Offset Y (px)"},
            "Add New Arc": {"it": "Aggiungi Nuovo Arco"},
            "Add New Section": {"it": "Aggiungi Nuova Sezione"},
            "Live Studio Simulator": {"it": "Simulatore di Studio"},
            "Manual Testing Value:": {"it": "Valore di Test Manuale:"},
            "Show Needle While Editing": {"it": "Mostra Lancetta in Editing"},
            "OutSim IP:": {"it": "IP OutSim:"},
            "OutSim Port:": {"it": "Porta OutSim:"},
            "Start UDP Telemetry (OutSim)": {"it": "Avvia Telemetria UDP"},
            "Lock Dashboard Resize": {"it": "Blocca Ridimensionamento"},
            "Help": {"it": "Guida"},
            "Cross Weave": {"it": "Trama Incrociata"},
            "Text Alignment": {"it": "Allineamento Testo"},
            "Alignment Offset": {"it": "Offset Allineamento"},
            "Left": {"it": "Sinistra"},
            "Right": {"it": "Destra"},
            "Major Ticks": {"it": "Tacche Principali"},
            "Medium Ticks": {"it": "Tacche Medie"},
            "Small Ticks": {"it": "Tacche Piccole"},
            "Add Major Set": {"it": "Aggiungi Principale"},
            "Add Medium Set": {"it": "Aggiungi Media"},
            "Add Small Set": {"it": "Aggiungi Piccola"},
            "Color": {"it": "Colore"},
            "Delete": {"it": "Elimina"},
            "Layer": {"it": "Livello"},
            "Shape": {"it": "Forma"},
            "Radius": {"it": "Raggio"},
            "Length": {"it": "Lunghezza"},
            "Thickness": {"it": "Spessore"},
            "Major": {"it": "Principali"},
            "Minor": {"it": "Secondarie"},
            "Sub-Minor": {"it": "Piccole"},
            "Project": {"it": "Progetto"},
            "Geometry": {"it": "Geometria"},
            "Indicator": {"it": "Indicatore"},
            "Typography": {"it": "Tipografia"},
            "Ticks": {"it": "Tacche"},
            "Arcs": {"it": "Archi"},
            "Sections": {"it": "Sezioni"},
            "Simulation": {"it": "Simulazione"},
            "Stay Always in Overlay (Always on Top)": {"it": "Rimani Sempre in Overlay (In Primo Piano)"},
            "(Short flash is normal; signifies activation)": {"it": "(Un breve flash è normale; significa che ha funzionato)"}
        }
        if self.lang == "it": return mapping.get(text, {}).get("it", text)
        return text

    def retranslate_ui(self):
        for key, widget in self.ui_reg.items():
            txt = getattr(widget, "_base_txt", "")
            if not txt:
                if isinstance(widget, QLabel): txt = widget.text()
                elif isinstance(widget, QPushButton): txt = widget.text()
                elif isinstance(widget, QGroupBox): txt = widget.title()
                elif isinstance(widget, QCheckBox): txt = widget.text()
            
            # Clean base text (remove units and colons for safer mapping)
            base = txt.replace(" (px):", "").replace(" (cm):", "").replace(":", "").strip()
            
            # Special case for labels with units (px/cm)
            if hasattr(widget, "_is_size") and widget._is_size:
                u = "cm" if self.unit_mode == "cm" else "px"
                translated = f"{self.get_tr(base)} ({u}):"
            else:
                translated = self.get_tr(base)
                if ":" in txt and not translated.endswith(":"): translated += ":"

            if isinstance(widget, QLabel): widget.setText(translated)
            elif isinstance(widget, QPushButton): widget.setText(translated)
            elif isinstance(widget, QGroupBox): widget.setTitle(translated)
            elif isinstance(widget, QCheckBox): widget.setText(translated)
        
        # Translate Main Tab Labels
        tab_map = {
            0: "Project", 1: "Geometry", 2: "Indicator", 3: "Typography", 
            4: "Ticks", 5: "Arcs", 6: "Sections", 7: "Simulation"
        }
        for idx, base in tab_map.items():
            if idx < self.tabs.count():
                self.tabs.setTabText(idx, self.get_tr(base))
        
        # Dynamic Arc/Section Widgets
        for ud in self.arc_widgets:
            ud['w'].setTitle(self.get_tr("Arc") + f" {self.arc_widgets.index(ud)+1}" if not ud['name'].text() else ud['name'].text())
            ud['en'].setText(self.get_tr("Enabled"))
            ud['btn_c'].setText(self.get_tr("Color"))
            ud['btn_d'].setText(self.get_tr("Delete"))
            for lbl in ud['w'].findChildren(QLabel):
                bt = getattr(lbl, "_base_txt", lbl.text().replace(":", "").strip())
                lbl.setText(self.get_tr(bt) + ":")

        for ud in self.sec_widgets:
            ud['w'].setTitle(self.get_tr("Section") + f" {self.sec_widgets.index(ud)+1}" if not ud['name'].text() else ud['name'].text())
            ud['en'].setText(self.get_tr("Enabled"))
            ud['btn_c'].setText(self.get_tr("Color"))
            ud['btn_d'].setText(self.get_tr("Delete"))
            for lbl in ud['w'].findChildren(QLabel):
                bt = getattr(lbl, "_base_txt", lbl.text().replace(":", "").strip())
                lbl.setText(self.get_tr(bt) + ":")

        for ud in self.tick_widgets:
            ud['w'].setTitle(self.get_tr("Tick Set") + f" {self.tick_widgets.index(ud)+1}" if not ud['name'].text() else ud['name'].text())
            ud['en'].setText(self.get_tr("Enabled"))
            ud['btn_c'].setText(self.get_tr("Color"))
            ud['btn_d'].setText(self.get_tr("Delete"))
            for lbl in ud['w'].findChildren(QLabel):
                bt = getattr(lbl, "_base_txt", lbl.text().replace(":", "").strip())
                lbl.setText(self.get_tr(bt) + ":")

        # Tabs
        tab_names = {
            0: {"en": "Project", "it": "Progetto"},
            1: {"en": "Wallpaper", "it": "Sfondo"},
            2: {"en": "Indicator", "it": "Lancetta"},
            3: {"en": "Typography", "it": "Tipografia"},
            4: {"en": "Ticks", "it": "Tacche"},
            5: {"en": "Arcs", "it": "Archi"},
            6: {"en": "Sections", "it": "Sezioni"}
        }
        for i, names in tab_names.items():
            if i < self.tabs.count():
                self.tabs.setTabText(i, names[self.lang])
        
        if self.btn_lock.isChecked():
            self.btn_lock.setText("Unlock Dashboard Resize" if self.lang=="en" else "Sblocca Ridimensionamento")
        else:
            self.btn_lock.setText("Lock Dashboard Resize" if self.lang=="en" else "Blocca Ridimensionamento")

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Gauge Design (*.gaugedesign)")
        if path:
            with open(path, 'r') as f: self.load_state_dict(json.load(f))
            self.is_dirty = False

    def closeEvent(self, event):
        if self.is_dirty:
            title = "Unsaved Changes" if self.lang == "en" else "Modifiche non salvate"
            msg = "You have unsaved changes. Do you want to save before closing?" if self.lang == "en" else "Hai delle modifiche non salvate. Vuoi salvare prima di chiudere?"
            
            box = QMessageBox(self)
            box.setWindowTitle(title)
            box.setText(msg)
            box.setIcon(QMessageBox.Icon.Question)
            
            save_btn = box.addButton("Save" if self.lang == "en" else "Salva", QMessageBox.ButtonRole.YesRole)
            discard_btn = box.addButton("Don't Save" if self.lang == "en" else "Non salvare", QMessageBox.ButtonRole.NoRole)
            cancel_btn = box.addButton("Cancel" if self.lang == "en" else "Annulla", QMessageBox.ButtonRole.RejectRole)
            
            box.exec()
            
            clicked = box.clickedButton()
            if clicked == save_btn:
                self.save_project()
                if not self.is_dirty: event.accept()
                else: event.ignore()
            elif clicked == discard_btn:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion"); win = DesignerWindow(); win.showMaximized(); sys.exit(app.exec())
