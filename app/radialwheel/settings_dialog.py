"""Диалог „Настройки на колелото“ – 8 страници (спец. модул Д)."""
import copy
import logging
import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
                               QRadioButton, QScrollArea, QSlider, QSpinBox, QStackedWidget, QVBoxLayout, QWidget)

from . import autostart, icons, winapi
from .config import DEFAULTS, SECTOR_IDS, cfg
from .i18n import LANGUAGES, tr

log = logging.getLogger(__name__)

QSS = """
QDialog, QWidget#page { background:#2B2B2B; color:#ECE6D4; font-family:'Segoe UI'; font-size:13px; }
QLabel { color:#ECE6D4; }
QLabel#hint { color:#A9A596; }
QListWidget { background:#222; border:1px solid #111; color:#ECE6D4; outline:0; }
QListWidget::item { padding:6px 8px; border-radius:4px; }
QListWidget::item:selected { background:#4A76C5; color:white; }
QListWidget#nav { min-width:190px; max-width:190px; }
QListWidget#nav::item { padding:4px 8px; }
QLineEdit[bad="true"] { border:1px solid #D84848; }
QScrollArea { border:none; background:transparent; }
QPushButton { background:#3A3A3A; color:#ECE6D4; border:1px solid #141414; border-radius:5px; padding:6px 14px; }
QPushButton:hover { background:#454545; border-color:#6897E8; }
QPushButton#danger { background:#A81C1C; border-color:#6b1010; color:white; }
QPushButton#danger:hover { background:#C82828; }
QCheckBox, QRadioButton { color:#ECE6D4; spacing:8px; }
QComboBox, QSpinBox, QLineEdit { background:#1E1E1E; color:#ECE6D4; border:1px solid #111; border-radius:4px; padding:4px 8px; min-height:22px; }
QComboBox QAbstractItemView { background:#1E1E1E; color:#ECE6D4; selection-background-color:#4A76C5; }
QSlider::groove:horizontal { height:6px; background:#5A6D94; border-radius:3px; }
QSlider::sub-page:horizontal { background:#8FA8D8; border-radius:3px; }
QSlider::handle:horizontal { background:#E4E4E4; border:1px solid #333; width:14px; margin:-6px 0; border-radius:4px; }
"""

PAGES = ["view", "layout", "icons", "folders", "programs", "shortcuts", "favorites", "internet", "grids",
         "functions", "themes", "hotkeys", "sounds", "update", "reset"]
NAV_ICON = {"folders": "sector_folders", "programs": "sector_programs", "shortcuts": "sector_keyboard",
            "favorites": "sector_favorites", "internet": "sector_internet", "grids": "set_layout"}
SCROLL_PAGES = {"folders", "programs", "shortcuts", "favorites", "internet", "grids"}
KEYS = (["Space", "Tab", "Insert", "Home", "End", "`"] + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        + [str(i) for i in range(10)] + [f"F{i}" for i in range(1, 13)])


class DropZone(QPushButton):
    """Зона за плъзгане и пускане на .zip (или клик за избор на файл)."""
    zipChosen = Signal(str)

    def __init__(self, text):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setStyleSheet("QPushButton{border:2px dashed #777;border-radius:12px;font-size:14px;}"
                           "QPushButton:hover{border-color:#4A76C5;}")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.toLocalFile().lower().endswith(".zip"):
                self.zipChosen.emit(u.toLocalFile())
                break


class GridPreview(QWidget):
    """Схематичен преглед на панела (колони × редове, пропорции на плочките)."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(190)
        self.n = self.cols = self.rows = 1
        self.tw = self.th = 96
        self.pw = self.ph = 100
        self.header = 26

    def set_grid(self, n, cols, rows, tw, th, pw, ph, header):
        self.n, self.cols, self.rows, self.tw, self.th, self.pw, self.ph, self.header = n, cols, rows, tw, th, pw, ph, header
        self.update()

    def paintEvent(self, _):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = min((self.width() - 20) / self.pw, (self.height() - 20) / self.ph)
        ox, oy = (self.width() - self.pw * k) / 2, (self.height() - self.ph * k) / 2
        p.setPen(QPen(QColor("#141414"), 1))
        p.setBrush(QColor("#303030"))
        p.drawRoundedRect(QRectF(ox, oy, self.pw * k, self.ph * k), 8, 8)
        p.setBrush(QColor("#222222"))
        p.drawRoundedRect(QRectF(ox + 6 * k, oy + 6 * k, self.pw * k - 12 * k, self.header * k), 4, 4)
        gap, pad = 6, 8
        x0 = ox + (6 + pad) * k
        y0 = oy + (6 + self.header + pad) * k
        avail = self.pw - 12 - 2 * pad
        grid_w = self.cols * self.tw + (self.cols - 1) * gap
        extra = max(0, (avail - grid_w) / self.cols)             # плочките се разпъват, ако панелът е по-широк
        tw = self.tw + extra
        for i in range(self.n):
            r, c = divmod(i, self.cols)
            p.setBrush(QColor("#4A76C5") if i == 0 else QColor("#3F3F3F"))
            p.setPen(QPen(QColor("#9BBDF9" if i == 0 else "#161616"), 1))
            p.drawRoundedRect(QRectF(x0 + c * (tw + gap) * k, y0 + r * (self.th + gap) * k, tw * k, self.th * k), 4, 4)
        p.end()


class SettingsDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.c = controller
        self.setWindowTitle(tr("settings.title"))
        self.setWindowIcon(QIcon(icons.builtin("app")))
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setStyleSheet(QSS)
        self.resize(960, 620)
        root = QHBoxLayout(self)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(24, 24))
        for p in PAGES:
            it = QListWidgetItem(QIcon(icons.builtin(NAV_ICON.get(p, "set_" + p))), tr("set." + p))
            self.nav.addItem(it)
        self.stack = QStackedWidget()
        root.addWidget(self.nav)
        root.addWidget(self.stack, 1)
        self._builders = [getattr(self, "page_" + p) for p in PAGES]
        self.rebuild_pages()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

    def rebuild_pages(self):
        cur = self.stack.currentIndex()
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        for pid, b in zip(PAGES, self._builders):
            page = b()
            if pid in SCROLL_PAGES:
                sa = QScrollArea()
                sa.setWidgetResizable(True)
                sa.setWidget(page)
                page = sa
            self.stack.addWidget(page)
        self.stack.setCurrentIndex(max(0, cur))

    def open_page(self, i):
        if isinstance(i, str):
            i = PAGES.index(i) if i in PAGES else 0
        self.nav.setCurrentRow(max(0, min(i, len(PAGES) - 1)))
        self.show()
        self.raise_()
        self.activateWindow()

    # ------------------------------------------------------------ помощни
    def _color_button(self, get, set_, title=None):
        """Бутон-мостра: клик отваря избор на цвят с прозрачност; ✕ връща цвета по подразбиране."""
        box = QWidget()
        hl = QHBoxLayout(box)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(4)
        b = QPushButton(tr("color.pick"))
        b.setMinimumWidth(110)
        x = QPushButton("✕")
        x.setFixedWidth(30)
        x.setToolTip(tr("color.clear"))

        def paint():
            c = get()
            col = QColor(c) if c else QColor()
            if col.isValid():
                lum = (col.red() * 299 + col.green() * 587 + col.blue() * 114) / 1000
                b.setStyleSheet(f"background:rgba({col.red()},{col.green()},{col.blue()},{col.alpha()});"
                                f"color:{'#000' if lum > 140 or col.alpha() < 110 else '#fff'};")
                b.setText(f"{col.name()}  ·  {round(col.alphaF() * 100)} %")
            else:
                b.setStyleSheet("")
                b.setText(tr("color.default"))
            x.setEnabled(bool(c))

        def pick():
            cur = QColor(get()) if get() else QColor("#3F3F3F")
            col = QColorDialog.getColor(cur, self, title or tr("color.title"), QColorDialog.ShowAlphaChannel)
            if col.isValid():
                set_(col.name(QColor.HexArgb))
                paint()

        def clear():
            set_("")
            paint()
        b.clicked.connect(pick)
        x.clicked.connect(clear)
        hl.addWidget(b)
        hl.addWidget(x)
        paint()
        box.repaint_color = paint
        return box

    def _page(self, title, hint=""):
        w = QWidget()
        w.setObjectName("page")
        lay = QVBoxLayout(w)
        h = QLabel(f"<h2>{title}</h2>")
        lay.addWidget(h)
        if hint:
            lb = QLabel(hint)
            lb.setObjectName("hint")
            lb.setWordWrap(True)
            lay.addWidget(lb)
        return w, lay

    def commit(self, relayout=True):
        cfg.save()
        if relayout:
            self.c.apply_config()

    # ------------------------------------------------------------ 1. Изглед
    def page_view(self):
        w, lay = self._page(tr("set.view"))
        form = QFormLayout()
        op = QSlider(Qt.Horizontal)
        op.setRange(30, 100)
        op.setValue(int(cfg["appearance"]["opacity"] * 100))
        op_lbl = QLabel(f"{op.value()} %")
        sc = QSlider(Qt.Horizontal)
        sc.setRange(60, 200)
        sc.setValue(int(cfg["appearance"]["scale"] * 100))
        sc_lbl = QLabel(f"{sc.value()} %")
        an = QCheckBox(tr("view.animations"))
        an.setChecked(cfg["appearance"]["animations"])

        def set_op(v):
            op_lbl.setText(f"{v} %")
            cfg["appearance"]["opacity"] = v / 100
            self.commit(False)

        def set_sc(v):
            sc_lbl.setText(f"{v} %")
            cfg["appearance"]["scale"] = v / 100
            self.commit()
        op.valueChanged.connect(set_op)
        sc.valueChanged.connect(set_sc)
        an.toggled.connect(lambda v: (cfg["appearance"].__setitem__("animations", v), self.commit(False)))
        r1, r2 = QHBoxLayout(), QHBoxLayout()
        r1.addWidget(op, 1), r1.addWidget(op_lbl)
        r2.addWidget(sc, 1), r2.addWidget(sc_lbl)
        form.addRow(tr("view.opacity"), r1)
        form.addRow(tr("view.scale"), r2)
        form.addRow("", an)
        lay.addLayout(form)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------ 2. Подредба
    def page_layout(self):
        w, lay = self._page(tr("set.layout"), tr("layout.hint"))
        lst = QListWidget()
        lst.setIconSize(QSize(34, 34))
        lst.setDragDropMode(QAbstractItemView.InternalMove)
        lst.setDefaultDropAction(Qt.MoveAction)
        clock = ["12:00", "1:30", "3:00", "4:30", "6:00", "7:30", "9:00", "10:30"]
        for i, sid in enumerate(cfg["sector_order"]):
            it = QListWidgetItem(QIcon(icons.pixmap(self._sector_icon(sid), 34)), f"{tr('sector.' + sid)}")
            it.setData(Qt.UserRole, sid)
            lst.addItem(it)
        info = QLabel("")
        info.setObjectName("hint")

        def changed(*_):
            order = [lst.item(i).data(Qt.UserRole) for i in range(lst.count())]
            if sorted(order) == sorted(SECTOR_IDS):
                cfg["sector_order"] = order
                info.setText("   ·   ".join(f"{clock[i]} {tr('sector.' + s)}" for i, s in enumerate(order)))
                self.commit()
        lst.model().rowsMoved.connect(changed)
        info.setText("   ·   ".join(f"{clock[i]} {tr('sector.' + s)}" for i, s in enumerate(cfg["sector_order"])))
        info.setWordWrap(True)
        lay.addWidget(lst, 1)
        lay.addWidget(info)
        return w

    def _sector_icon(self, sid):
        custom = cfg["custom_icons"].get(sid, "")
        if custom and os.path.exists(os.path.expandvars(custom)):
            return custom
        name = {"system": "windows"}.get(sid, sid)
        return icons.builtin("sector_" + name)

    # ------------------------------------------------------------ 3. Икони
    def page_icons(self):
        w, lay = self._page(tr("set.icons"), tr("icons.hint"))
        for sid in cfg["sector_order"]:
            row = QHBoxLayout()
            pic = QLabel()
            pic.setFixedSize(40, 40)
            pic.setPixmap(icons.pixmap(self._sector_icon(sid), 36))
            name = QLabel(tr("sector." + sid))
            b1, b2 = QPushButton(tr("icons.choose")), QPushButton(tr("icons.default"))

            def choose(_=False, sid=sid):
                p, _f = QFileDialog.getOpenFileName(self, tr("icons.dialog"), "", "Icons (*.png *.svg *.ico)")
                if p:
                    cfg["custom_icons"][sid] = os.path.normpath(p)
                    icons.clear_cache()
                    self.commit()
                    self.rebuild_pages()

            def default(_=False, sid=sid):
                cfg["custom_icons"].pop(sid, None)
                icons.clear_cache()
                self.commit()
                self.rebuild_pages()
            b1.clicked.connect(choose)
            b2.clicked.connect(default)
            row.addWidget(pic)
            row.addWidget(name, 1)
            row.addWidget(b1)
            row.addWidget(b2)
            lay.addLayout(row)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------ 4. Функции
    def page_functions(self):
        w, lay = self._page(tr("set.functions"))
        form = QFormLayout()
        b = cfg["behavior"]
        mode = QComboBox()
        mode.addItem(tr("func.open_hover"), "hover")
        mode.addItem(tr("func.open_click"), "click")
        mode.setCurrentIndex(0 if b["open_mode"] == "hover" else 1)
        mode.currentIndexChanged.connect(lambda i: (b.__setitem__("open_mode", mode.itemData(i)), self.commit(False)))
        delay = QSpinBox()
        delay.setRange(0, 1000)
        delay.setSingleStep(10)
        delay.setValue(b["hover_delay_ms"])
        delay.valueChanged.connect(lambda v: (b.__setitem__("hover_delay_ms", v), self.commit()))
        hide = QSpinBox()
        hide.setRange(0, 60000)
        hide.setSingleStep(250)
        hide.setValue(b["autohide_ms"])
        hide.valueChanged.connect(lambda v: (b.__setitem__("autohide_ms", v), self.commit(False)))
        af = QCheckBox(tr("func.autofocus"))
        af.setChecked(b["autofocus_search"])
        af.toggled.connect(lambda v: (b.__setitem__("autofocus_search", v), self.commit(False)))
        cp = QCheckBox(tr("func.confirm_power"))
        cp.setChecked(b["confirm_power"])
        cp.toggled.connect(lambda v: (b.__setitem__("confirm_power", v), self.commit(False)))
        au = QCheckBox(tr("func.autostart"))
        au.setChecked(autostart.is_enabled())
        au.toggled.connect(lambda v: self.c.set_autostart(v))
        lang = QComboBox()
        for code, name in LANGUAGES.items():
            lang.addItem(name, code)
        lang.setCurrentIndex(max(0, lang.findData(cfg["language"])))
        lang.currentIndexChanged.connect(lambda i: (cfg.__setitem__("language", lang.itemData(i)), self.commit(False)))
        note = QLabel(tr("func.lang_note"))
        note.setObjectName("hint")
        form.addRow(tr("func.open_mode"), mode)
        form.addRow(tr("func.delay"), delay)
        form.addRow(tr("func.autohide"), hide)
        form.addRow("", af)
        form.addRow("", cp)
        form.addRow("", au)
        form.addRow(tr("func.language"), lang)
        form.addRow("", note)
        lay.addLayout(form)
        lay.addStretch(1)
        self._autostart_box = au
        return w

    # ------------------------------------------------------------ 5. Теми
    def page_themes(self):
        w, lay = self._page(tr("set.themes"))
        a = cfg["appearance"]
        rbs = {}
        for key in ("dark", "light", "custom"):
            rb = QRadioButton(tr("theme." + key))
            rb.setChecked(a["theme"] == key)
            rbs[key] = rb
            lay.addWidget(rb)
            rb.toggled.connect(lambda on, k=key: on and (a.__setitem__("theme", k), self.commit()))
        row = QHBoxLayout()
        sw = QLabel()
        sw.setFixedSize(60, 26)

        def paint():
            sw.setStyleSheet(f"background:{a['accent']};border:1px solid #111;border-radius:4px;")
        paint()
        pick = QPushButton(tr("theme.pick"))

        def choose():
            col = QColorDialog.getColor(QColor(a["accent"]), self, tr("theme.accent"))
            if col.isValid():
                a["accent"] = col.name()
                if a["theme"] == "dark":
                    a["theme"] = "custom"
                    rbs["custom"].setChecked(True)
                paint()
                self.commit()
        pick.clicked.connect(choose)
        row.addWidget(QLabel(tr("theme.accent")))
        row.addWidget(sw)
        row.addWidget(pick)
        row.addStretch(1)
        lay.addSpacing(10)
        lay.addLayout(row)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------ 6. Преки пътища
    def page_hotkeys(self):
        w, lay = self._page(tr("set.hotkeys"))
        hk = cfg["hotkey"]
        en = QCheckBox(tr("hk.enable"))
        en.setChecked(hk["enabled"])
        lay.addWidget(en)
        mods = QHBoxLayout()
        boxes = {}
        for k, label in (("ctrl", "Ctrl"), ("alt", "Alt"), ("shift", "Shift"), ("win", "Win")):
            cb = QCheckBox(label)
            cb.setChecked(bool(hk[k]))
            boxes[k] = cb
            mods.addWidget(cb)
        key = QComboBox()
        key.addItems(KEYS)
        key.setCurrentText(hk["key"] if hk["key"] in KEYS else "Space")
        mods.addWidget(QLabel("+"))
        mods.addWidget(key)
        mods.addStretch(1)
        lay.addLayout(mods)
        mouse = QComboBox()
        for code, lbl in (("none", "hk.mouse_none"), ("middle", "hk.mouse_middle"),
                          ("xbutton1", "hk.mouse_x1"), ("xbutton2", "hk.mouse_x2")):
            mouse.addItem(tr(lbl), code)
        mouse.setCurrentIndex(max(0, mouse.findData(cfg["mouse_trigger"])))
        form = QFormLayout()
        form.addRow(tr("hk.mouse"), mouse)
        lay.addLayout(form)
        warn = QLabel(tr("hk.mouse_warn"))
        warn.setObjectName("hint")
        warn.setWordWrap(True)
        lay.addWidget(warn)
        status = QLabel("")
        status.setWordWrap(True)
        apply_ = QPushButton(tr("hk.apply"))

        def apply():
            hk["enabled"] = en.isChecked()
            for k, cb in boxes.items():
                hk[k] = cb.isChecked()
            hk["key"] = key.currentText()
            cfg["mouse_trigger"] = mouse.currentData()
            cfg.save()
            ok, msg = self.c.reload_triggers()
            status.setStyleSheet("color:#7BD88F;" if ok else "color:#FF7B7B;")
            status.setText(tr("hk.ok") if ok else msg)
        apply_.clicked.connect(apply)
        lay.addWidget(apply_, 0, Qt.AlignLeft)
        lay.addWidget(status)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------ редактор на пътища (Папки/Програми/Любими/Интернет)
    def _rows(self, lay, rows):
        """rows: речници {icon,label,value,placeholder,kinds,set,default}. Всяка промяна се записва веднага."""
        grid = QGridLayout()
        grid.setColumnStretch(2, 1)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        for r, row in enumerate(rows):
            pic = QLabel()
            pic.setFixedSize(30, 30)
            if row.get("icon"):
                pic.setPixmap(icons.pixmap(row["icon"], 26))
            edit = QLineEdit(row["value"])
            edit.setPlaceholderText(row.get("placeholder", ""))
            edit.setMinimumWidth(260)

            def save(_=None, edit=edit, row=row):
                v = edit.text().strip()
                if row.get("kinds") and v and "://" not in v:
                    v = os.path.normpath(v)
                row["set"](v)
                cfg.save()
            edit.editingFinished.connect(save)
            grid.addWidget(pic, r, 0)
            grid.addWidget(QLabel(row["label"]), r, 1)
            grid.addWidget(edit, r, 2)
            col = 3
            for kind in row.get("kinds", ()):
                b = QPushButton(tr("btn.file") if kind == "file" else tr("btn.folder"))

                def browse(_=False, kind=kind, edit=edit, save=save):
                    if kind == "file":
                        p, _f = QFileDialog.getOpenFileName(self, tr("dlg.choose_program"), os.path.expandvars(edit.text()))
                    else:
                        p = QFileDialog.getExistingDirectory(self, tr("dlg.choose_folder"), os.path.expandvars(edit.text()))
                    if p:
                        edit.setText(os.path.normpath(p))
                        save()
                b.clicked.connect(browse)
                grid.addWidget(b, r, col)
                col += 1
            if "default" in row:
                b = QPushButton(tr("icons.default") if row["default"] is not None else tr("btn.clear"))

                def reset(_=False, edit=edit, row=row, save=save):
                    edit.setText(row["default"] or "")
                    save()
                b.clicked.connect(reset)
                grid.addWidget(b, r, 5)
        lay.addLayout(grid)

    # ------------------------------------------------------------ динамични слотове (папки / програми / любими)
    def _slots_page(self, key, title, hint, kinds):
        from .panels import SLOT_KINDS, slot_visual
        w, lay = self._page(title, hint)
        top = QHBoxLayout()
        add = QPushButton("＋  " + tr("slot.add"))
        rst = QPushButton(tr("slot.reset_list"))

        def add_slot():
            cfg[key].append({"id": "custom", "path": "", "label": ""})
            cfg.save()
            self.rebuild_pages()

        def reset_list():
            cfg[key] = copy.deepcopy(DEFAULTS[key])
            cfg.save()
            self.rebuild_pages()
        add.clicked.connect(add_slot)
        rst.clicked.connect(reset_list)
        top.addWidget(add)
        top.addWidget(rst)
        top.addStretch(1)
        lay.addLayout(top)
        grid = QGridLayout()
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 2)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(5)
        lp = SLOT_KINDS[key][0]
        for r, e in enumerate(cfg[key]):
            label, icon, _tip = slot_visual(key, e)
            pic = QLabel()
            pic.setFixedSize(30, 30)
            pic.setPixmap(icons.pixmap(icon, 26))
            name = QLineEdit(e.get("label", ""))
            builtin = e.get("id", "custom") != "custom" and lp
            name.setPlaceholderText(tr(lp + e["id"]) if builtin else tr("slot.name"))
            path = QLineEdit(e.get("path", ""))
            path.setPlaceholderText("(" + tr("icons.default").lower() + ")" if builtin and key == "programs" else "")

            def save(_=None, e=e, name=name, path=path):
                e["label"] = name.text().strip()
                v = path.text().strip()
                e["path"] = os.path.normpath(v) if v and "://" not in v else v
                cfg.save()
            name.editingFinished.connect(save)
            path.editingFinished.connect(save)
            grid.addWidget(pic, r, 0)
            grid.addWidget(QLabel(f"{r + 1}"), r, 1)
            grid.addWidget(name, r, 2)
            grid.addWidget(path, r, 3)
            col = 4
            grid.addWidget(self._color_button(lambda e=e: e.get("bg", ""),
                                              lambda v, e=e: (e.__setitem__("bg", v), cfg.save())), r, col)
            col += 1
            for kind in kinds:
                b = QPushButton(tr("btn.file") if kind == "file" else tr("btn.folder"))

                def browse(_=False, kind=kind, path=path, save=save):
                    if kind == "file":
                        p, _f = QFileDialog.getOpenFileName(self, tr("dlg.choose_program"), os.path.expandvars(path.text()))
                    else:
                        p = QFileDialog.getExistingDirectory(self, tr("dlg.choose_folder"), os.path.expandvars(path.text()))
                    if p:
                        path.setText(os.path.normpath(p))
                        save()
                        self.rebuild_pages()
                b.clicked.connect(browse)
                grid.addWidget(b, r, col)
                col += 1
            for txt, delta in (("▲", -1), ("▼", 1)):
                b = QPushButton(txt)
                b.setFixedWidth(34)
                b.setEnabled(0 <= r + delta < len(cfg[key]))

                def move(_=False, r=r, delta=delta):
                    lst = cfg[key]
                    lst[r], lst[r + delta] = lst[r + delta], lst[r]
                    cfg.save()
                    self.rebuild_pages()
                b.clicked.connect(move)
                grid.addWidget(b, r, col)
                col += 1
            x = QPushButton("✕")
            x.setFixedWidth(34)
            x.setEnabled(len(cfg[key]) > 1)

            def remove(_=False, r=r):
                del cfg[key][r]
                cfg.save()
                self.rebuild_pages()
            x.clicked.connect(remove)
            grid.addWidget(x, r, col)
        lay.addLayout(grid)
        note = QLabel(tr("slot.hint_empty"))
        note.setObjectName("hint")
        lay.addWidget(note)
        lay.addStretch(1)
        return w

    def page_folders(self):
        return self._slots_page("folders", tr("set.folders"), tr("page.folders_hint"), ("dir", "file"))

    def page_programs(self):
        return self._slots_page("programs", tr("set.programs"), tr("page.programs_hint"), ("file", "dir"))

    def page_favorites(self):
        return self._slots_page("favorites", tr("set.favorites"), tr("page.favorites_hint"), ("file", "dir"))

    # ------------------------------------------------------------ визуален конфигуратор на решетката
    def page_grids(self):
        from .layout import GRID_PANELS, grid_params, panel_count
        w, lay = self._page(tr("set.grids"), tr("grid.hint"))
        a = cfg["appearance"]
        row = QHBoxLayout()
        ps = QSlider(Qt.Horizontal)
        ps.setRange(50, 150)
        ps.setValue(int(a["panel_scale"] * 100))
        ps_lbl = QLabel(f"{ps.value()} %")

        def set_ps(v):
            ps_lbl.setText(f"{v} %")
            a["panel_scale"] = v / 100
            self.commit()
            refresh()
        ps.valueChanged.connect(set_ps)
        row.addWidget(QLabel(tr("grid.panel_scale")))
        row.addWidget(ps, 1)
        row.addWidget(ps_lbl)
        lay.addLayout(row)

        sel = QComboBox()
        for sid in GRID_PANELS:
            sel.addItem(tr("panel." + sid), sid)
        mode = QComboBox()
        for code, key in (("single", "grid.single"), ("per_row", "grid.per_row"), ("rows", "grid.rows")):
            mode.addItem(tr(key), code)
        spins = {}
        form = QFormLayout()
        form.addRow(tr("grid.panel"), sel)
        form.addRow(tr("grid.mode"), mode)
        for key, rng in (("value", (1, 60)), ("tile_w", (0, 400)), ("tile_h", (0, 300)), ("icon", (0, 160)),
                         ("font", (0, 30)), ("panel_w", (0, 3000))):
            sp = QSpinBox()
            sp.setRange(*rng)
            sp.setSingleStep(2 if key != "panel_w" else 20)
            spins[key] = sp
            form.addRow(tr("grid." + key), sp)
        bgbtn = self._color_button(lambda: cfg["grid"][sel.currentData()].get("bg", ""),
                                   lambda v: (cfg["grid"][sel.currentData()].__setitem__("bg", v), self.commit()))
        form.addRow(tr("grid.bg"), bgbtn)
        lay.addLayout(form)
        summary = QLabel("")
        summary.setObjectName("hint")
        preview = GridPreview()
        reset = QPushButton(tr("grid.reset"))
        lay.addWidget(summary)
        lay.addWidget(preview, 1)
        lay.addWidget(reset, 0, Qt.AlignLeft)
        loading = [False]

        def current():
            return sel.currentData()

        def refresh():
            sid = current()
            n = panel_count(sid)
            gp = grid_params(sid, n, 1.0 * a["panel_scale"])
            preview.set_grid(n, gp["cols"], gp["rows"], gp["tile_w"], gp["tile_h"], gp["W"], gp["H"], gp["header"])
            summary.setText(tr("grid.summary", n, gp["cols"], gp["rows"], gp["W"] - 12, gp["H"] - 12))
            spins["value"].setEnabled(mode.currentData() != "single")

        def load():
            loading[0] = True
            g = cfg["grid"][current()]
            mode.setCurrentIndex(max(0, mode.findData(g["mode"])))
            for k, sp in spins.items():
                sp.setValue(int(g[k]))
            bgbtn.repaint_color()
            loading[0] = False
            refresh()

        def store(*_):
            if loading[0]:
                return
            g = cfg["grid"][current()]
            g["mode"] = mode.currentData()
            for k, sp in spins.items():
                g[k] = sp.value()
            self.commit()
            refresh()

        def do_reset():
            cfg["grid"][current()] = copy.deepcopy(DEFAULTS["grid"][current()])
            self.commit()
            load()
        sel.currentIndexChanged.connect(load)
        mode.currentIndexChanged.connect(store)
        for sp in spins.values():
            sp.valueChanged.connect(store)
        reset.clicked.connect(do_reset)
        load()
        return w

    def page_internet(self):
        w, lay = self._page(tr("set.internet"))
        lay.addWidget(QLabel(f"<b>{tr('page.browsers')}</b>"))
        rows = [{"icon": icons.builtin("br_" + e["id"]), "label": tr("browser." + e["id"]), "value": e["path"],
                 "kinds": ("file",), "default": "", "set": lambda v, e=e: e.__setitem__("path", v)}
                for e in cfg["browsers"]]
        self._rows(lay, rows)
        lay.addSpacing(8)
        lay.addWidget(QLabel(f"<b>{tr('page.sites')}</b>"))
        rows = [{"icon": icons.builtin("site_" + e["id"]), "label": tr("site." + e["id"]), "value": e["url"],
                 "default": DEFAULTS["sites"][i]["url"], "set": lambda v, e=e: v and e.__setitem__("url", v)}
                for i, e in enumerate(cfg["sites"])]
        self._rows(lay, rows)
        lay.addSpacing(8)
        lay.addWidget(QLabel(f"<b>{tr('page.bookmarks')}</b>"))
        self._rows(lay, [{"icon": icons.builtin("site_folder"), "label": tr("site.folder"), "value": cfg["bookmarks_folder"],
                          "kinds": ("dir",), "default": DEFAULTS["bookmarks_folder"],
                          "set": lambda v: cfg.__setitem__("bookmarks_folder", v)}])
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------ бързи клавишни комбинации
    def page_shortcuts(self):
        w, lay = self._page(tr("set.shortcuts"), tr("page.shortcuts_hint"))
        tips = {it["keys"]: it.get("tip") for row in cfg["quick_shortcuts"] for it in row}
        if getattr(self, "_sc_state", None) is None:           # състоянието пази и празните клетки между прерисувания
            self._sc_state = [[it["keys"] for it in row] for row in cfg["quick_shortcuts"]] or [[""]]
            ncol = max((len(r) for r in self._sc_state), default=1)
            self._sc_state = [r + [""] * (ncol - len(r)) for r in self._sc_state]
        rows = self._sc_state

        def save():
            out = []
            for row in rows:
                items = []
                for txt in row:
                    txt = txt.strip()
                    if not txt:
                        continue
                    try:
                        winapi.parse_combo(txt)
                    except ValueError:
                        continue
                    norm = "+".join(p.strip() for p in txt.split("+"))
                    items.append({"keys": norm, "tip": tips.get(norm) or norm})
                out.append(items)
            cfg["quick_shortcuts"] = [r for r in out if r]
            cfg.save()

        def structural(fn):
            fn()
            save()
            self.rebuild_pages()
            self.c.apply_config()

        def add_row():
            rows.append([""] * max(1, max((len(r) for r in rows), default=1)))

        def del_row():
            if len(rows) > 1:
                rows.pop()

        def add_col():
            if max((len(r) for r in rows), default=0) < 6:
                for r in rows:
                    r.append("")

        def del_col():
            if max((len(r) for r in rows), default=0) > 1:
                for r in rows:
                    if len(r) > 1:
                        r.pop()
        bar = QHBoxLayout()
        for key, fn in (("shortcuts.add_row", add_row), ("shortcuts.del_row", del_row),
                        ("shortcuts.add_col", add_col), ("shortcuts.del_col", del_col)):
            bt = QPushButton(tr(key))
            bt.clicked.connect(lambda _=False, fn=fn: structural(fn))
            bar.addWidget(bt)
        bar.addStretch(1)
        lay.addLayout(bar)
        grid = QGridLayout()
        for r, row in enumerate(rows):
            grid.addWidget(QLabel(tr("shortcuts.row", r + 1)), r, 0)
            for c, txt in enumerate(row):
                ed = QLineEdit(txt)
                ed.setPlaceholderText("Ctrl+C")

                def done(ed=ed, r=r, c=c):
                    t = ed.text().strip()
                    ok = True
                    if t:
                        try:
                            winapi.parse_combo(t)
                        except ValueError:
                            ok = False
                    ed.setProperty("bad", not ok)
                    ed.style().unpolish(ed)
                    ed.style().polish(ed)
                    rows[r][c] = t
                    save()
                ed.editingFinished.connect(done)
                grid.addWidget(ed, r, c + 1)
        lay.addLayout(grid)
        btn = QPushButton(tr("shortcuts.default_all"))

        def reset():
            cfg["quick_shortcuts"] = copy.deepcopy(DEFAULTS["quick_shortcuts"])
            cfg.save()
            self._sc_state = None
            self.rebuild_pages()
        btn.clicked.connect(reset)
        lay.addWidget(btn, 0, Qt.AlignLeft)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------ 7. Звуци
    def page_sounds(self):
        w, lay = self._page(tr("set.sounds"))
        cb = QCheckBox(tr("sound.enable"))
        cb.setChecked(cfg["sounds"])
        cb.toggled.connect(lambda v: (cfg.__setitem__("sounds", v), self.commit(False)))
        lay.addWidget(cb)
        lay.addStretch(1)
        return w

    # ------------------------------------------------------------ 8. Нулиране
    def page_update(self):
        from . import __version__, updater
        w, lay = self._page(tr("set.update"), tr("update.hint"))
        lay.addWidget(QLabel(tr("update.current", __version__)))
        zone = DropZone(tr("update.drop"))
        lay.addWidget(zone)
        btn = QPushButton(tr("update.choose"))
        lay.addWidget(btn, 0, Qt.AlignLeft)
        note = QLabel(tr("update.deps"))
        note.setObjectName("hint")
        lay.addWidget(note)
        lay.addStretch(1)

        def chosen(path):
            if not updater.can_update():
                QMessageBox.warning(self, tr("app.title"), tr("update.unsupported"))
                return
            try:
                prefix, new_ver = updater.inspect_zip(path)
            except updater.UpdateError as exc:
                QMessageBox.warning(self, tr("app.title"), tr("update." + str(exc)))
                return
            text = tr("update.confirm", __version__, new_ver)
            if updater.parse_version(new_ver) <= updater.parse_version(__version__):
                text += tr("update.confirm_same")
            if QMessageBox.question(self, tr("app.title"), text) != QMessageBox.Yes:
                return
            try:
                self.c.apply_update(updater.stage(path, prefix))
            except Exception as exc:
                QMessageBox.warning(self, tr("app.title"), str(exc))

        def pick():
            p, _f = QFileDialog.getOpenFileName(self, tr("update.pick_title"), "", "ZIP (*.zip)")
            if p:
                chosen(p)
        zone.clicked.connect(pick)
        btn.clicked.connect(pick)
        zone.zipChosen.connect(chosen)
        self._update_chosen = chosen
        return w

    def page_reset(self):
        w, lay = self._page(tr("set.reset"), tr("reset.text"))
        btn = QPushButton(tr("reset.button"))
        btn.setObjectName("danger")

        def do():
            if QMessageBox.question(self, tr("app.title"), tr("reset.confirm")) == QMessageBox.Yes:
                lang = cfg["language"]
                cfg.reset()
                self._sc_state = None
                icons.clear_cache()
                self.c.apply_config()
                self.c.reload_triggers()
                self.rebuild_pages()
                QMessageBox.information(self, tr("app.title"), tr("reset.done"))
        btn.clicked.connect(do)
        lay.addWidget(btn, 0, Qt.AlignLeft)
        lay.addStretch(1)
        return w
