import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QLabel, QScrollArea, QFileDialog, 
    QMessageBox, QSplitter, QDialog, QFormLayout, 
    QSpinBox, QDialogButtonBox, QTextEdit, QLineEdit,
    QCheckBox, QPushButton, QComboBox, QApplication
)
from PyQt6.QtGui import QAction, QImage, QPixmap
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtCore import Qt, QEvent, QTimer

from pdf_processor import PDFProcessor
from interactive_viewer import InteractiveGraphicsView
import dialogs


class MainWindow(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        
        self.processor = PDFProcessor()
        self.current_zoom = 2.0
        self.page_edits_map = {}
        self.last_page = -1
        
        from PyQt6.QtCore import QSettings
        self.settings = QSettings("SaRaM", "PDFManager")
        self.recent_files = self.settings.value("recent_files", [])
        self.init_ui()

        # 외부에서 넘어온 PDF 경로가 존재하면 UI 표시 후 강제로 파일 열기 처리
        if initial_file:
            # 약간의 지연 후 띄워주는 것이 GUI 그리기 안정성에 좋음 (QTimer 사용 가능하지만, 여기선 바로 호출)
            QTimer.singleShot(100, lambda: self.open_file_by_path(initial_file))

    def init_ui(self):
        self.setWindowTitle("PDF Manager")
        self.setAcceptDrops(True)
        self.resize(1000, 700)
        self.setGeometry(100, 100, 1200, 800) # Added from instruction

        # 메뉴 설정
        self.create_menu()

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # QSplitter를 사용하여 왼쪽 썸네일 리스트, 오른쪽 뷰어 분리
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 왼쪽: 페이지 목록
        self.page_list_widget = QListWidget()
        self.page_list_widget.currentRowChanged.connect(self.on_page_selected)
        splitter.addWidget(self.page_list_widget)

        # 오른쪽: 우측 패널 (뷰어 + 주석 패널)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 툴바 영역 (상단)
        toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["기본 보기 모드", "텍스트 추가 모드", "이미지 추가 모드"])
        self.mode_combo.currentIndexChanged.connect(self.change_editor_mode)
        
        self.save_edits_btn = QPushButton("편집된 내용 병합하여 PDF 저장")
        self.save_edits_btn.clicked.connect(self.save_edited_pdf)
        
        toolbar_layout.addWidget(QLabel("에디터 모드:"))
        toolbar_layout.addWidget(self.mode_combo)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.save_edits_btn)
        
        right_layout.addWidget(toolbar_widget)

        # 서드파티 뷰어 (InteractiveGraphicsView)
        self.viewer = InteractiveGraphicsView()
        self.viewer.viewport().installEventFilter(self)
        right_layout.addWidget(self.viewer)
        
        # 뷰어 하단: 주석(Annotation) 패널
        self.annot_panel = QWidget()
        annot_layout = QHBoxLayout(self.annot_panel)
        annot_layout.setContentsMargins(5, 5, 5, 5)
        
        self.annot_text_edit = QLineEdit()
        self.annot_text_edit.setPlaceholderText("현재 페이지 오른쪽 위에 추가할 주석(팝업 노트) 내용을 입력하세요...")
        annot_layout.addWidget(self.annot_text_edit)
        
        self.annot_add_btn = QPushButton("현재 페이지 주석 추가 저장")
        self.annot_add_btn.clicked.connect(self.add_annotation)
        annot_layout.addWidget(self.annot_add_btn)
        
        self.annot_view_btn = QPushButton("현재 페이지 주석 보기")
        self.annot_view_btn.clicked.connect(self.view_annotations)
        annot_layout.addWidget(self.annot_view_btn)
        
        right_layout.addWidget(self.annot_panel)
        
        splitter.addWidget(right_widget)
        
        # Splitter 비율 설정 (왼쪽 20%, 오른쪽 80%)
        splitter.setSizes([200, 800])

    def create_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('파일(&F)')
        
        open_action = QAction('열기(&O)...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)
        
        export_img_action = QAction('이미지로 내보내기(&I)...', self)
        export_img_action.triggered.connect(lambda: dialogs.export_images_dialog(self))
        file_menu.addAction(export_img_action)
        
        import_img_action = QAction('이미지로 PDF 생성(&P)...', self)
        import_img_action.triggered.connect(lambda: dialogs.import_images_dialog(self))
        file_menu.addAction(import_img_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('끝내기(&X)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        tool_menu = menubar.addMenu('도구(&T)')
        
        merge_action = QAction('PDF 병합(&M)...', self)
        merge_action.triggered.connect(lambda: dialogs.merge_pdfs_dialog(self))
        tool_menu.addAction(merge_action)
        
        extract_action = QAction('페이지 추출(&E)...', self)
        extract_action.triggered.connect(lambda: dialogs.show_extract_pages_dialog(self))
        tool_menu.addAction(extract_action)
        
        extract_text_action = QAction('현재 페이지 텍스트 추출(&X)', self)
        extract_text_action.triggered.connect(lambda: dialogs.show_extract_text_dialog(self))
        tool_menu.addAction(extract_text_action)
        
        tool_menu.addSeparator()
        
        optimize_action = QAction('PDF 최적화 저장...(&O)', self)
        optimize_action.triggered.connect(lambda: dialogs.optimize_pdf_dialog(self))
        tool_menu.addAction(optimize_action)
        
        secure_action = QAction('PDF 보안 저장...(&S)', self)
        secure_action.triggered.connect(lambda: dialogs.show_secure_pdf_dialog(self))
        tool_menu.addAction(secure_action)
        
        help_menu = menubar.addMenu('도움말(&H)')
        
        usage_action = QAction('도움말 (기본 사용법)(&U)', self)
        usage_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(usage_action)
        
        about_action = QAction('제작자 정보(&A)', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        menubar.setCornerWidget(spacer, Qt.Corner.TopLeftCorner)
        
        author_label = QLabel(" Made by SaRaM_ida(망고아빠) ")
        author_label.setStyleSheet("color: #7f8fa6; font-size: 12px; font-weight: bold; margin-right: 10px;")
        menubar.setCornerWidget(author_label, Qt.Corner.TopRightCorner)

    def update_recent_menu(self):
        try:
            self.recent_menu.clear()
            for path in self.recent_files:
                if os.path.exists(path):
                    action = QAction(os.path.basename(path), self)
                    action.setData(path)
                    action.triggered.connect(lambda checked, p=path: self.open_file_by_path(p))
                    self.recent_menu.addAction(action)
            if not self.recent_files:
                action = QAction("최근 파일 없음", self)
                action.setEnabled(False)
                self.recent_menu.addAction(action)
        except Exception:
            pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls: return
        paths = [u.toLocalFile() for u in urls if u.toLocalFile().lower().endswith('.pdf')]
        
        if len(paths) == 1:
            self.open_file_by_path(paths[0])
        elif len(paths) > 1:
            reply = QMessageBox.question(
                self, '여러 PDF 열기', 
                f'{len(paths)}개의 파일을 병합하시겠습니까?\n(아니오 선택 시 첫 번째 파일만 엽니다)',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                dialogs.merge_pdfs_dialog(self)
            else:
                self.open_file_by_path(paths[0])

    def perform_search(self):
        if not hasattr(self, 'search_input'): return
        query = self.search_input.text()
        if not query:
            self.clear_search()
            return
            
        self.search_results = self.processor.highlight_search(query)
        self.current_search_idx = -1
        
        if self.search_results:
            self.search_next()
        else:
            QMessageBox.information(self, "검색 결과", "일치하는 텍스트가 없습니다.")
            if hasattr(self, 'search_label'): self.search_label.setText("0/0")

    def search_next(self):
        if not hasattr(self, 'search_results') or not self.search_results: return
        self.current_search_idx = (self.current_search_idx + 1) % len(self.search_results)
        page = self.search_results[self.current_search_idx]
        if hasattr(self, 'search_label'): self.search_label.setText(f"{self.current_search_idx + 1}/{len(self.search_results)}")
        self.go_to_page(page)

    def search_prev(self):
        if not hasattr(self, 'search_results') or not self.search_results: return
        self.current_search_idx = (self.current_search_idx - 1) % len(self.search_results)
        page = self.search_results[self.current_search_idx]
        if hasattr(self, 'search_label'): self.search_label.setText(f"{self.current_search_idx + 1}/{len(self.search_results)}")
        self.go_to_page(page)

    def clear_search(self):
        if hasattr(self, 'search_results'):
            self.search_results = []
        if hasattr(self, 'search_label'): self.search_label.setText("")
        if self.processor.is_open:
            if hasattr(self, 'page_list_widget'):
                self.render_page(self.page_list_widget.currentRow())


    def open_file_dialog(self):
            # src의 상위 폴더(pdf_manager) 밑의 pdfs 폴더를 초기 경로로 설정
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pdf_dir = os.path.join(base_dir, 'pdfs')
            if not os.path.exists(pdf_dir):
                pdf_dir = base_dir
            
            filepath, _ = QFileDialog.getOpenFileName(
                self, 
                "PDF 파일 열기", 
                pdf_dir, 
                "PDF Files (*.pdf)"
            )
            
            if filepath:
                self.open_file_by_path(filepath)

    def open_file_by_path(self, filepath):
            success, error_msg = self.processor.open_pdf(filepath)
            if success:
                self.current_page = 0
                # 에디터 관련 데이터 초기화
                self.viewer.set_mode(self.viewer.MODE_VIEWER)
                self.mode_combo.setCurrentIndex(0)
                
                self.update_page_list()
                if self.processor.page_count > 0:
                    self.page_list_widget.setCurrentRow(0)
                self.setWindowTitle(f"PDF Manager - {os.path.basename(filepath)}")
            else:
                QMessageBox.critical(self, "오류", f"PDF 파일을 열 수 없습니다:\n{error_msg}")

    def load_pdf(self, file_path):
            self.open_file_by_path(file_path)

    def add_annotation(self):
            text = self.annot_text_edit.text().strip()
            if not text:
                QMessageBox.warning(self, "알림", "주석 내용을 입력하세요.")
                return
                
            if not self.processor.is_open:
                QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
                return
                
            current_row = self.page_list_widget.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "알림", "주석을 추가할 페이지가 선택되지 않았습니다.")
                return
    
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            initial_dir = os.path.join(base_dir, 'pdfs')
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "주석이 추가된 PDF 저장",
                os.path.join(initial_dir, 'annotated.pdf'),
                "PDF Files (*.pdf)"
            )
            
            if not save_path:
                return
                
            success, error_msg = self.processor.add_text_annotation(current_row, text, save_path)
            
            if success:
                QMessageBox.information(self, "완료", f"주석이 추가되어 {save_path}에 저장되었습니다.\n(현재 문서에 덮어쓰지 않은 경우 새로 엽니다.)")
                self.annot_text_edit.clear()
                self.load_pdf(save_path)
            else:
                QMessageBox.critical(self, "오류", f"주석 추가 중 오류가 발생했습니다:\n{error_msg}")

    def view_annotations(self):
            if not self.processor.is_open:
                QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
                return
                
            current_row = self.page_list_widget.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "알림", "확인할 페이지가 선택되지 않았습니다.")
                return
                
            annots = self.processor.get_annotations(current_row)
            if not annots:
                QMessageBox.information(self, "주석 확인", "이 페이지에는 텍스트 주석이 없습니다.")
                return
                
            text = "\n\n------------------------\n\n".join(annots)
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"페이지 {current_row + 1} 주석 목록")
            dialog.resize(500, 350)
            
            layout = QVBoxLayout(dialog)
            text_edit = QTextEdit()
            text_edit.setPlainText(text)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)
            
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.exec()

    def update_page_list(self):
            """왼쪽 목록 뷰에 페이지들을 채웁니다."""
            self.page_list_widget.blockSignals(True)
            self.page_list_widget.clear()
            
            for i in range(self.processor.page_count):
                self.page_list_widget.addItem(f"페이지 {i + 1}")
                
            self.page_list_widget.blockSignals(False)

    def on_page_selected(self, row):
            if row < 0 or not self.processor.is_open:
                return
                
            # 페이지 변경 전 이전 페이지의 상태 저장
            if self.last_page != row:
                self._save_current_edits()
                self.last_page = row
                
            self.render_page(row)

    def render_page(self, page_number):
            # PIL 이미지 추출
            pil_img = self.processor.get_page_image(page_number, zoom_factor=self.current_zoom)
            
            if not pil_img:
                # 렌더링 실패 처리
                return
    
            # QImage로 변환
            # PIL Image를 QImage로 바꾸려면 byte string으로 변환 후 포맷 지정 필요
            data = pil_img.tobytes("raw", "RGB")
            qimage = QImage(data, pil_img.width, pil_img.height, pil_img.width * 3, QImage.Format.Format_RGB888)
            
            # QLabel에 QPixmap 형태로 보여주기
            pixmap = QPixmap.fromImage(qimage)
            self.viewer.set_base_image(pixmap)

    def change_editor_mode(self, index):
            self.viewer.set_mode(index)

    def _save_current_edits(self):
            # 현재 화면의 에디트 상태를 맵에 저장
            if self.last_page >= 0 and self.processor.is_open:
                page = self.processor._document.load_page(self.last_page)
                # 원본 PDF의 폭과 높이를 알아냅니다.
                rect = page.rect
                ow = rect.width
                oh = rect.height
                edits = self.viewer.get_current_edits(ow, oh)
                if edits:
                    self.page_edits_map[self.last_page] = edits
                elif self.last_page in self.page_edits_map:
                    del self.page_edits_map[self.last_page]

    def save_edited_pdf(self):
            if not self.processor.is_open:
                QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
                return False
                
            self._save_current_edits()
            if not self.page_edits_map:
                QMessageBox.information(self, "알림", "저장할 편집 내용(텍스트/이미지)이 없습니다.")
                return False
                
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            initial_dir = os.path.join(base_dir, 'pdfs')
            save_path, _ = QFileDialog.getSaveFileName(self, "편집된 PDF 저장", os.path.join(initial_dir, 'edited.pdf'), "PDF Files (*.pdf)")
            if not save_path:
                return False
                
            success, msg = self.processor.save_edited_pdf(save_path, self.page_edits_map)
            if success:
                QMessageBox.information(self, "완료", f"편집된 PDF가 성공적으로 저장되었습니다:\n{save_path}")
                # 편집 내용을 비우고 새 파일 로드
                self.page_edits_map.clear()
                self.load_pdf(save_path)
                return True
            else:
                QMessageBox.critical(self, "오류", f"저장 중 오류가 발생했습니다:\n{msg}")
                return False

    def show_help_dialog(self):
            msg = (
                "<b>[PDF Manager 기본 사용법]</b><br><br>"
                "1. <b>파일 열기</b>: 메뉴의 '파일' > '열기' 또는 Ctrl+O 를 눌러 PDF를 엽니다.<br>"
                "2. <b>페이지 이동</b>: 왼쪽 목록을 클릭하거나 문서 위에서 마우스 휠을 스크롤합니다.<br>"
                "3. <b>화면 확대/축소</b>: 뷰어 위에서 'Ctrl + 마우스 휠'을 사용합니다.<br>"
                "4. <b>텍스트/이미지 추가</b>: 상단 에디터 모드를 변경 후 화면을 클릭해 추가하고, <b>더블클릭</b>하여 재수정할 수 있습니다.<br>"
                "5. <b>주석(노트) 추가</b>: 우측 하단 패널에 내용을 적고 '현재 페이지 주석 추가 저장' 버튼을 누릅니다.<br>"
                "6. <b>확장 기능</b>: 상단 '도구' 메뉴에서 병합, 추출, 최적화, 보안 저장을 할 수 있습니다."
            )
            QMessageBox.information(self, "도움말", msg)

    def show_about_dialog(self):
            msg = (
                "<h2>PDF Manager</h2>"
                "<p><b>버전:</b> 1.0.0</p>"
                "<p><b>제작자:</b> SaRaM_ida(망고아빠)</p>"
                "<p><b>이메일:</b> <a href='mailto:saramida@gmail.com'>saramida@gmail.com</a></p>"
                "<br><p>이 프로그램은 PyQt6 및 PyMuPDF를 활용하여 제작되었습니다.</p>"
            )
            QMessageBox.about(self, "제작자 정보", msg)

    def eventFilter(self, obj, event):
            if obj == self.viewer.viewport() and event.type() == QEvent.Type.Wheel:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    # InteractiveGraphicsView 자체의 확대/축소 로직에 맡김
                    return False
                else:
                    # 뷰어 영역 일반 스크롤 중 끝 도달 시 페이지 이동
                    vbar = self.viewer.verticalScrollBar()
                    delta = event.angleDelta().y()
                    current = self.page_list_widget.currentRow()
                    
                    if delta > 0:  # 휠 업
                        if vbar.value() == vbar.minimum() and current > 0:
                            self.page_list_widget.setCurrentRow(current - 1)
                            return True
                    elif delta < 0:  # 휠 다운
                        if vbar.value() == vbar.maximum() and current < self.processor.page_count - 1 and current != -1:
                            self.page_list_widget.setCurrentRow(current + 1)
                            return True
    
            return super().eventFilter(obj, event)

    def closeEvent(self, event):
            """앱 종료 시 편집된 내용이 있는지 확인합니다."""
            if not self.processor.is_open:
                event.accept()
                return
                
            # 현재 화면 상태 저장 시도
            self._save_current_edits()
            
            # 편집된 내용이 맵에 존재하면 확인 창 띄우기
            if self.page_edits_map:
                reply = QMessageBox.question(
                    self, 
                    '저장 확인',
                    "편집된 내용이 아직 문서에 저장되지 않았습니다.\n저장하시겠습니까?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Save
                )
                
                if reply == QMessageBox.StandardButton.Save:
                    # 저장 성공 시에만 닫기 승인
                    if self.save_edited_pdf():
                        event.accept()
                    else:
                        event.ignore()
                elif reply == QMessageBox.StandardButton.Discard:
                    event.accept()
                else:
                    # 취소 선택 시 닫기 동작 취소
                    event.ignore()
            else:
                event.accept()