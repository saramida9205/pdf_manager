from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem,
    QGraphicsRectItem, QGraphicsItem, QFileDialog, QGraphicsSceneMouseEvent,
    QInputDialog, QMenu, QDialog, QVBoxLayout, QHBoxLayout, QFontComboBox,
    QSpinBox, QPushButton, QTextEdit, QDialogButtonBox, QColorDialog
)
from PyQt6.QtGui import QPixmap, QColor, QFont, QPen, QBrush, QCursor
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QPointF

class ResizablePixmapItem(QGraphicsObject if hasattr(QGraphicsPixmapItem, 'metaObject') else QGraphicsPixmapItem):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.resizing = False
        self.handle_size = 10
        self.start_rect = QRectF()
        self.start_pos = QPointF()
        self.aspect_ratio = pixmap.width() / pixmap.height() if pixmap.height() != 0 else 1
        
        # Original size is the pixmap size
        self.current_width = float(pixmap.width())
        self.current_height = float(pixmap.height())

    def boundingRect(self):
        # We need extra space for the handles when selected
        rect = QRectF(0, 0, self.current_width, self.current_height)
        if self.isSelected():
            rect.adjust(-self.handle_size, -self.handle_size, self.handle_size, self.handle_size)
        return rect
        
    def paint(self, painter, option, widget=None):
        # Draw the scaled pixmap
        target_rect = QRectF(0, 0, self.current_width, self.current_height)
        source_rect = QRectF(self.pixmap().rect())
        painter.drawPixmap(target_rect, self.pixmap(), source_rect)
        
        # Draw selection handles
        if self.isSelected():
            painter.setPen(QPen(Qt.GlobalColor.blue, 1, Qt.PenStyle.DashLine))
            painter.drawRect(target_rect)
            
            painter.setBrush(QBrush(Qt.GlobalColor.blue))
            painter.setPen(QPen(Qt.GlobalColor.black))
            # Bottom Right Handle
            br_handle = QRectF(self.current_width - self.handle_size/2, self.current_height - self.handle_size/2, self.handle_size, self.handle_size)
            painter.drawRect(br_handle)
            
    def hoverMoveEvent(self, event):
        if self.isSelected():
            pos = event.pos()
            # Check if near bottom right corner
            if pos.x() >= self.current_width - self.handle_size and pos.y() >= self.current_height - self.handle_size:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)
        
    def mousePressEvent(self, event):
        if self.isSelected() and event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            if pos.x() >= self.current_width - self.handle_size and pos.y() >= self.current_height - self.handle_size:
                self.resizing = True
                self.start_pos = event.scenePos()
                self.start_rect = QRectF(0, 0, self.current_width, self.current_height)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            diff = event.scenePos() - self.start_pos
            new_width = self.start_rect.width() + diff.x()
            new_height = new_width / self.aspect_ratio
            
            if new_width > 20 and new_height > 20:
                self.prepareGeometryChange()
                self.current_width = new_width
                self.current_height = new_height
                self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
        else:
            super().mouseReleaseEvent(event)
            
            
class TextEditDialog(QDialog):
    def __init__(self, text="", font_family="Malgun Gothic", font_size=16, color=Qt.GlobalColor.black, parent=None):
        super().__init__(parent)
        self.setWindowTitle("텍스트 설정 및 입력")
        self.resize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # 툴바: 폰트, 크기, 색상
        toolbar = QHBoxLayout()
        
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont(font_family))
        self.font_combo.currentFontChanged.connect(self.update_preview)
        toolbar.addWidget(self.font_combo)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 144)
        self.size_spin.setValue(int(font_size))
        self.size_spin.valueChanged.connect(self.update_preview)
        toolbar.addWidget(self.size_spin)
        
        self.color_btn = QPushButton("색상 설정")
        if isinstance(color, QColor):
            self.current_color = color
        else:
            self.current_color = QColor(color)
        self.color_btn.setStyleSheet(f"background-color: {self.current_color.name()}")
        self.color_btn.clicked.connect(self.choose_color)
        toolbar.addWidget(self.color_btn)
        
        layout.addLayout(toolbar)
        
        # 텍스트 에디터 영역
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.textChanged.connect(self.update_preview)
        layout.addWidget(self.text_edit)
        
        self.update_preview()
        
        # 하단 버튼
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "색상 선택")
        if color.isValid():
            self.current_color = color
            # RGB 밝기에 따른 텍스트 표시 반전 (가시성)
            brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
            text_color = "black" if brightness > 125 else "white"
            self.color_btn.setStyleSheet(f"background-color: {self.current_color.name()}; color: {text_color};")
            self.update_preview()
            
    def update_preview(self):
        font = self.font_combo.currentFont()
        font.setPointSize(self.size_spin.value())
        self.text_edit.setFont(font)
        self.text_edit.setStyleSheet(f"color: {self.current_color.name()}")
        
    def get_data(self):
        return {
            'text': self.text_edit.toPlainText(),
            'font_family': self.font_combo.currentFont().family(),
            'font_size': self.size_spin.value(),
            'color': self.current_color
        }

class EditableTextItem(QGraphicsTextItem):
    def __init__(self, text="", font_family="Malgun Gothic", font_size=16, color=Qt.GlobalColor.black, parent=None):
        super().__init__(text, parent)
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        
        self.font_family = font_family
        self.font_size = font_size
        self.font_color = QColor(color)
        self.apply_style()
        
    def apply_style(self):
        font = QFont(self.font_family, self.font_size)
        self.setFont(font)
        self.setDefaultTextColor(self.font_color)
        
    def mouseDoubleClickEvent(self, event):
        dialog = TextEditDialog(self.toPlainText(), self.font_family, self.font_size, self.font_color)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data['text'].strip():
                self.setPlainText(data['text'])
                self.font_family = data['font_family']
                self.font_size = data['font_size']
                self.font_color = data['color']
                self.apply_style()
            else:
                if self.scene():
                    self.scene().removeItem(self)

class InteractiveGraphicsView(QGraphicsView):
    # Modes: 0=Viewer, 1=Add Text, 2=Add Image
    MODE_VIEWER = 0
    MODE_ADD_TEXT = 1
    MODE_ADD_IMAGE = 2
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        self.base_pixmap_item = None
        self.current_mode = self.MODE_VIEWER
        self.zoom_factor = 1.0
        
        # Storage for edits per page format: {page_idx: [{'type': 'text'|'image', ...}]}
        # We will hold edits mainly as items during viewing. 
        # But this class just manages the current page. The external window will handle switching.
        self.page_width = 0
        self.page_height = 0

    def set_mode(self, mode):
        self.current_mode = mode
        if mode == self.MODE_VIEWER:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)

    def set_base_image(self, pixmap):
        self.scene.clear()
        self.base_pixmap_item = self.scene.addPixmap(pixmap)
        self.base_pixmap_item.setZValue(-1) # Background
        self.page_width = pixmap.width()
        self.page_height = pixmap.height()
        
    def add_image_item(self, pixmap, pos, file_path=""):
        item = ResizablePixmapItem(pixmap)
        item.setPos(pos)
        item.image_path = file_path # custom field to store path for later PDF insertion
        self.scene.addItem(item)
        return item
        
    def add_text_item(self, text, font_family, font_size, color, pos):
        item = EditableTextItem(text, font_family, font_size, color)
        item.setPos(pos)
        self.scene.addItem(item)
        return item
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Map view coordinates to scene coordinates
            scene_pos = self.mapToScene(event.pos())
            
            # Check if clicked on the page boundaries
            if self.base_pixmap_item and self.base_pixmap_item.boundingRect().contains(scene_pos):
                if self.current_mode == self.MODE_ADD_TEXT:
                    item_at = self.itemAt(event.pos())
                    if item_at == self.base_pixmap_item or item_at is None:
                        dialog = TextEditDialog()
                        if dialog.exec() == QDialog.DialogCode.Accepted:
                            data = dialog.get_data()
                            if data['text'].strip():
                                self.add_text_item(data['text'], data['font_family'], data['font_size'], data['color'], scene_pos)
                            self.set_mode(self.MODE_VIEWER) # Revert to viewer after adding
                        event.accept()
                        return
                        
                elif self.current_mode == self.MODE_ADD_IMAGE:
                    item_at = self.itemAt(event.pos())
                    if item_at == self.base_pixmap_item or item_at is None:
                        file_path, _ = QFileDialog.getOpenFileName(self, "이미지 추가", "", "Images (*.png *.jpg *.jpeg *.bmp)")
                        if file_path:
                            pixmap = QPixmap(file_path)
                            self.add_image_item(pixmap, scene_pos, file_path)
                            self.set_mode(self.MODE_VIEWER)
                        event.accept()
                        return
                        
        super().mousePressEvent(event)
        
    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_factor *= 1.2
                self.scale(1.2, 1.2)
            else:
                self.zoom_factor /= 1.2
                self.scale(1/1.2, 1/1.2)
            event.accept()
        else:
            super().wheelEvent(event)
            
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            for item in self.scene.selectedItems():
                if item != self.base_pixmap_item:
                    self.scene.removeItem(item)
        super().keyPressEvent(event)
        
    def get_current_edits(self, original_width, original_height):
        # The base_pixmap was rendered at a specific resolution (zoom_factor in get_page_image).
        # We need to calculate scaling factors to map back to original PDF points.
        scale_x = original_width / self.page_width if self.page_width else 1.0
        scale_y = original_height / self.page_height if self.page_height else 1.0
        
        edits = []
        for item in self.scene.items():
            if item == self.base_pixmap_item:
                continue
                
            if isinstance(item, EditableTextItem):
                color = item.defaultTextColor()
                pos = item.scenePos()
                # item.boundingRect().width() is in scene coords
                fs = item.font().pointSize()
                edits.append({
                    'type': 'text',
                    'text': item.toPlainText(),
                    'point': (pos.x() * scale_x, pos.y() * scale_y),
                    'color': (item.font_color.red(), item.font_color.green(), item.font_color.blue()),
                    'fontsize': item.font_size * scale_y,
                    'font_family': item.font_family
                })
            elif isinstance(item, ResizablePixmapItem):
                pos = item.scenePos()
                width = item.current_width
                height = item.current_height
                
                rect = (
                    pos.x() * scale_x, 
                    pos.y() * scale_y, 
                    (pos.x() + width) * scale_x, 
                    (pos.y() + height) * scale_y
                )
                
                edits.append({
                    'type': 'image',
                    'path': getattr(item, 'image_path', ''),
                    'rect': rect
                })
        return edits
