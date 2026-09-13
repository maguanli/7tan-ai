
"""
封面编辑器 — 手动模式画布编辑器 (Phase 5)
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QColorDialog, QListWidget, QListWidgetItem, QFileDialog,
    QSplitter, QGraphicsView, QGraphicsScene, QGraphicsTextItem,
    QGraphicsPixmapItem, QGraphicsRectItem, QMenu, QInputDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QPainter, QPixmap, QImage, QColor, QFont, QPen, QBrush,
    QLinearGradient, QFontMetrics, QAction,
)
from pathlib import Path
from loguru import logger

class CoverEditor(QWidget):
    """手动封面编辑器 — QPainter 渲染画布 + 图层管理"""
    finished = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._canvas_w, self._canvas_h = 1280, 720
        self._layers: list[dict] = []
        self._history: list[list[dict]] = []
        self._redo_stack: list[list[dict]] = []
        self._selected_idx: int = -1
        self._bg_color = QColor("#1a1a2e")
        self._bg_image: QPixmap | None = None
        self._setup_ui()
        self._add_default_layers()

    # ---- UI ----
    def _setup_ui(self):
        layout = QHBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左：图层面板
        lw = QWidget(); ll = QVBoxLayout(lw)
        ll.addWidget(QLabel("<b>📑 图层</b>"))
        self._layer_list = QListWidget()
        self._layer_list.currentRowChanged.connect(self._on_layer_select)
        self._layer_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._layer_list.customContextMenuRequested.connect(self._layer_menu)
        ll.addWidget(self._layer_list)
        bh = QHBoxLayout()
        for t, s in [("+文字", self._add_text), ("+图片", self._add_image), ("🗑", self._del_layer)]:
            b = QPushButton(t); b.clicked.connect(s); bh.addWidget(b)
        ll.addLayout(bh); splitter.addWidget(lw)

        # 中：画布
        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setMinimumSize(640, 360)
        self._update_canvas_bg()
        splitter.addWidget(self._view)

        # 右：属性面板
        rw = QWidget(); rl = QVBoxLayout(rw)
        rl.addWidget(QLabel("<b>🎨 属性</b>"))
        self._prop_label = QLabel("选中图层以编辑")
        self._prop_label.setWordWrap(True)
        rl.addWidget(self._prop_label)
        rl.addStretch()
        splitter.addWidget(rw)
        splitter.setSizes([180, 640, 200])
        layout.addWidget(splitter)

        # 底部工具栏
        tbw = QWidget(); tbl = QHBoxLayout(tbw)
        for t, s in [
            ("🎨背景色", self._set_bg), ("🖼背景图", self._set_bg_img),
            ("↩撤销", self._undo), ("↪重做", self._redo),
            ("📤导出PNG", self._export_png), ("📤导出JPG", self._export_jpg),
        ]:
            b = QPushButton(t); b.clicked.connect(s); tbl.addWidget(b)
        tbl.addStretch()
        layout.addWidget(tbw)

    # ---- 画布 ----
    def _update_canvas_bg(self):
        self._scene.clear()
        r = QRectF(0, 0, self._canvas_w, self._canvas_h)
        if self._bg_image:
            self._scene.addPixmap(self._bg_image.scaled(self._canvas_w, self._canvas_h, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        else:
            self._scene.addRect(r, QPen(Qt.PenStyle.NoPen), QBrush(self._bg_color))
        self._scene.setSceneRect(r)
        self._view.fitInView(r, Qt.AspectRatioMode.KeepAspectRatio)
        for i, layer in enumerate(self._layers):
            self._render_layer(layer, i)

    def _render_layer(self, layer: dict, idx: int):
        t = layer.get("type", "text")
        x, y = layer.get("x", 100), layer.get("y", 200)
        if t == "text":
            item = QGraphicsTextItem(layer.get("content", "文字"))
            f = QFont(layer.get("font", "Microsoft YaHei"), layer.get("size", 48))
            item.setFont(f)
            item.setDefaultTextColor(QColor(layer.get("color", "#FFFFFF")))
            item.setPos(x, y)
            item.setData(0, idx)
            item.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, True)
            item.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, True)
            self._scene.addItem(item)
        elif t == "image":
            path = layer.get("path", "")
            if path and Path(path).exists():
                pm = QPixmap(path).scaledToWidth(layer.get("w", 300), Qt.TransformationMode.SmoothTransformation)
                item = QGraphicsPixmapItem(pm)
                item.setPos(x, y)
                item.setData(0, idx)
                item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, True)
                item.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, True)
                self._scene.addItem(item)

    # ---- 图层操作 ----
    def _add_default_layers(self):
        self._layers = [{
            "type": "text", "content": "视频标题", "x": 640, "y": 300,
            "font": "Microsoft YaHei", "size": 64, "color": "#FFFFFF",
        }]
        self._refresh_layers()

    def _add_text(self):
        text, ok = QInputDialog.getText(self, "添加文字", "文字内容:")
        if ok and text:
            self._push_history()
            self._layers.append({
                "type": "text", "content": text, "x": 200, "y": 200,
                "font": "Microsoft YaHei", "size": 48, "color": "#FFFFFF",
            })
            self._refresh_layers()

    def _add_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "",
            "图片 (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self._push_history()
            self._layers.append({
                "type": "image", "path": path, "x": 100, "y": 100, "w": 300,
            })
            self._refresh_layers()

    def _del_layer(self):
        if self._selected_idx >= 0:
            self._push_history()
            self._layers.pop(self._selected_idx)
            self._selected_idx = min(self._selected_idx, len(self._layers) - 1)
            self._refresh_layers()

    def _refresh_layers(self):
        self._layer_list.clear()
        for i, layer in enumerate(self._layers):
            t = layer.get("type", "text")
            label = f"{'📝' if t == 'text' else '🖼'} {layer.get('content', layer.get('path', f'图层{i+1}'))[:20]}"
            self._layer_list.addItem(label)
        self._update_canvas_bg()
        if self._selected_idx >= 0 and self._selected_idx < len(self._layers):
            self._layer_list.setCurrentRow(self._selected_idx)
            self._show_layer_props(self._layers[self._selected_idx])
        else:
            self._prop_label.setText("选中图层以编辑")

    def _on_layer_select(self, idx: int):
        self._selected_idx = idx
        if 0 <= idx < len(self._layers):
            self._show_layer_props(self._layers[idx])

    def _show_layer_props(self, layer: dict):
        t = layer.get("type", "text")
        lines = [f"类型: {t}"]
        for k in ["content", "font", "size", "color", "x", "y"]:
            if k in layer:
                lines.append(f"{k}: {layer[k]}")
        self._prop_label.setText("\n".join(lines))

    def _layer_menu(self, pos):
        menu = QMenu()
        menu.addAction("上移", lambda: self._move_layer(-1))
        menu.addAction("下移", lambda: self._move_layer(1))
        menu.addAction("删除", self._del_layer)
        menu.exec(self._layer_list.mapToGlobal(pos))

    def _move_layer(self, delta: int):
        if self._selected_idx < 0: return
        ni = self._selected_idx + delta
        if 0 <= ni < len(self._layers):
            self._push_history()
            self._layers[self._selected_idx], self._layers[ni] = self._layers[ni], self._layers[self._selected_idx]
            self._selected_idx = ni
            self._refresh_layers()

    # ---- 背景 ----
    def _set_bg(self):
        c = QColorDialog.getColor(self._bg_color, self, "选择背景色")
        if c.isValid():
            self._bg_color = c; self._bg_image = None; self._update_canvas_bg()

    def _set_bg_img(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择背景图", "",
            "图片 (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self._bg_image = QPixmap(path); self._update_canvas_bg()

    # ---- 撤销/重做 ----
    def _push_history(self):
        import copy
        self._history.append(copy.deepcopy(self._layers))
        self._redo_stack.clear()
        if len(self._history) > 20:
            self._history.pop(0)

    def _undo(self):
        if not self._history: return
        self._redo_stack.append(self._layers)
        self._layers = self._history.pop()
        self._selected_idx = -1
        self._refresh_layers()

    def _redo(self):
        if not self._redo_stack: return
        self._history.append(self._layers)
        self._layers = self._redo_stack.pop()
        self._selected_idx = -1
        self._refresh_layers()

    # ---- 导出 ----
    def _export_png(self): return self._do_export("PNG")
    def _export_jpg(self): return self._do_export("JPG")

    def _do_export(self, fmt: str) -> str | None:
        path, _ = QFileDialog.getSaveFileName(self, f"导出{fmt}", "cover." + fmt.lower(),
            f"{fmt} (*.{fmt.lower()})")
        if not path: return None
        img = QImage(self._canvas_w, self._canvas_h, QImage.Format.Format_ARGB32)
        p = QPainter(img)
        if self._bg_image:
            p.drawPixmap(0, 0, self._bg_image.scaled(self._canvas_w, self._canvas_h, Qt.AspectRatioMode.KeepAspectRatioByExpanding))
        else:
            p.fillRect(0, 0, self._canvas_w, self._canvas_h, self._bg_color)
        for layer in self._layers:
            self._paint_layer(p, layer)
        p.end()
        img.save(path, fmt, 95)
        self.finished.emit(path)
        return path

    def _paint_layer(self, p: QPainter, layer: dict):
        t = layer.get("type", "text")
        x, y = layer.get("x", 100), layer.get("y", 200)
        if t == "text":
            f = QFont(layer.get("font", "Microsoft YaHei"), layer.get("size", 48))
            p.setFont(f)
            p.setPen(QColor(layer.get("color", "#FFFFFF")))
            p.drawText(x, y, layer.get("content", ""))
        elif t == "image":
            path = layer.get("path", "")
            if path and Path(path).exists():
                pm = QPixmap(path).scaledToWidth(layer.get("w", 300), Qt.TransformationMode.SmoothTransformation)
                p.drawPixmap(x, y, pm)

    # ---- 与 AI 引擎集成 ----
    def load_result(self, result: dict):
        """载入 AI 引擎生成结果到画布"""
        self._push_history()
        # 背景
        bg = result.get("background_file", "")
        if bg and Path(bg).exists():
            self._bg_image = QPixmap(bg)
        elif result.get("bg_color"):
            self._bg_color = QColor(result["bg_color"])
        # 图层
        self._layers = result.get("layers", [])
        self._refresh_layers()

    def get_cover_data(self) -> dict:
        """导出封面数据（供持久化）"""
        return {
            "canvas_size": (self._canvas_w, self._canvas_h),
            "bg_color": self._bg_color.name(),
            "bg_image_path": str(getattr(self, '_bg_image_path', '')),
            "layers": self._layers,
        }

    def load_cover_data(self, data: dict):
        """从持久化数据恢复"""
        if "canvas_size" in data:
            self._canvas_w, self._canvas_h = data["canvas_size"]
        if "bg_color" in data:
            self._bg_color = QColor(data["bg_color"])
        if "bg_image_path" in data and data["bg_image_path"]:
            path = data["bg_image_path"]
            if Path(path).exists():
                self._bg_image = QPixmap(path)
                self._bg_image_path = path
        if "layers" in data:
            self._layers = data["layers"]
        self._refresh_layers()
