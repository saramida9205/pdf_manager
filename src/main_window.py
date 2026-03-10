import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QLabel, QScrollArea, QFileDialog, 
    QMessageBox, QSplitter, QDialog, QFormLayout, 
    QSpinBox, QDialogButtonBox, QTextEdit, QLineEdit,
    QCheckBox, QPushButton, QComboBox
)
from PyQt6.QtGui import QAction, QImage, QPixmap
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtCore import Qt, QEvent, QTimer

from pdf_processor import PDFProcessor
from interactive_viewer import InteractiveGraphicsView


class MainWindow(QMainWindow):
    def __init__(self, initial_file=None):
        super().__init__()
        
        self.processor = PDFProcessor()
        self.current_zoom = 2.0
        self.page_edits_map = {}
        self.last_page = -1
        
        self.init_ui()

        # 외부에서 넘어온 PDF 경로가 존재하면 UI 표시 후 강제로 파일 열기 처리
        if initial_file:
            # 약간의 지연 후 띄워주는 것이 GUI 그리기 안정성에 좋음 (QTimer 사용 가능하지만, 여기선 바로 호출)
            QTimer.singleShot(100, lambda: self.open_file_by_path(initial_file))

    def init_ui(self):
        self.setWindowTitle("PDF Manager")
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
        export_img_action.triggered.connect(self.export_images_dialog)
        file_menu.addAction(export_img_action)
        
        import_img_action = QAction('이미지로 PDF 생성(&P)...', self)
        import_img_action.triggered.connect(self.import_images_dialog)
        file_menu.addAction(import_img_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('끝내기(&X)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        tool_menu = menubar.addMenu('도구(&T)')
        
        merge_action = QAction('PDF 병합(&M)...', self)
        merge_action.triggered.connect(self.merge_pdfs_dialog)
        tool_menu.addAction(merge_action)
        
        extract_action = QAction('페이지 추출(&E)...', self)
        extract_action.triggered.connect(self.extract_pages_dialog)
        tool_menu.addAction(extract_action)
        
        extract_text_action = QAction('현재 페이지 텍스트 추출(&X)', self)
        extract_text_action.triggered.connect(self.extract_text_dialog)
        tool_menu.addAction(extract_text_action)
        
        tool_menu.addSeparator()
        
        optimize_action = QAction('PDF 최적화 저장...(&O)', self)
        optimize_action.triggered.connect(self.optimize_pdf_dialog)
        tool_menu.addAction(optimize_action)
        
        secure_action = QAction('PDF 보안 저장...(&S)', self)
        secure_action.triggered.connect(self.secure_pdf_dialog)
        tool_menu.addAction(secure_action)
        
        help_menu = menubar.addMenu('도움말(&H)')
        
        usage_action = QAction('도움말 (기본 사용법)(&U)', self)
        usage_action.triggered.connect(self.show_help_dialog)
        help_menu.addAction(usage_action)
        
        about_action = QAction('제작자 정보(&A)', self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        # 메뉴바 우측 정렬을 위한 여백 추가
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        menubar.setCornerWidget(spacer, Qt.Corner.TopLeftCorner) # Qt6에서 QMenuBar 우측 정렬 꼼수나 CornerWidget 사용
        
        # 우측 하단이나 우측 상단을 위한 Corner Widget (오른쪽 위)
        author_label = QLabel(" Made by SaRaM_ida(망고아빠) ")
        author_label.setStyleSheet("color: #7f8fa6; font-size: 12px; font-weight: bold; margin-right: 10px;")
        menubar.setCornerWidget(author_label, Qt.Corner.TopRightCorner)

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

    def export_images_dialog(self):
        if not self.processor.is_open:
            QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
            return

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        initial_dir = os.path.join(base_dir, 'pdfs')
        
        # 파일 다이얼로그로 저장할 형태(여러 이미지의 저장 폴더 이름 또는 단일 TIF 파일 이름) 선택
        save_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "이미지로 내보내기",
            os.path.join(initial_dir, "extracted_images"),
            "PNG Images (*.png);;JPEG Images (*.jpg);;TIFF Images (*.tif);;Multi-page TIFF (*.tif)"
        )
        
        if not save_path:
            return
            
        # 선택된 필터에 따라 포맷 결정
        img_format = "png"
        if "PNG" in selected_filter:
            img_format = "png"
        elif "JPEG" in selected_filter:
            img_format = "jpg"
        elif "Multi-page" in selected_filter:
            img_format = "tif_multi"
        elif "TIFF" in selected_filter:
            img_format = "tif"
            
        # 다중 TIFF가 아니라면(폴더에 개별 이미지로 저장될 경우),
        # save_path에 확장자가 붙어 있다면 제거하여 폴더 이름으로 사용
        output_target = save_path
        if img_format != "tif_multi":
            output_target, _ = os.path.splitext(save_path)
            
        success, error_msg = self.processor.save_as_images(output_target, img_format)
        
        if success:
            QMessageBox.information(self, "완료", f"이미지 변환이 완료되었습니다:\n{output_target}")
        else:
            QMessageBox.critical(self, "오류", f"이미지 변환 중 오류가 발생했습니다:\n{error_msg}")

    def import_images_dialog(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        initial_dir = os.path.join(base_dir, 'pdfs')
        
        # 병합할 이미지 파일 선택
        img_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "PDF로 묶을 이미지 선택",
            initial_dir,
            "Images (*.png *.jpg *.jpeg *.tif *.tiff);;All Files (*)"
        )
        
        if not img_paths:
            return
            
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "새 PDF 저장",
            os.path.join(initial_dir, 'from_images.pdf'),
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return
            
        success, error_msg = PDFProcessor.images_to_pdf(img_paths, save_path)
        if success:
            QMessageBox.information(self, "완료", f"새 PDF 파일이 생성되었습니다:\n{save_path}")
            self.load_pdf(save_path)
        else:
            QMessageBox.critical(self, "오류", f"PDF 생성 중 오류가 발생했습니다:\n{error_msg}")

    def merge_pdfs_dialog(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        initial_dir = os.path.join(base_dir, 'pdfs')
        
        # 병합할 여러 파일 선택
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "병합할 PDF 파일들 선택",
            initial_dir,
            "PDF Files (*.pdf)"
        )
        
        if not file_paths or len(file_paths) < 2:
            if len(file_paths) == 1:
                QMessageBox.warning(self, "알림", "병합하려면 2개 이상의 PDF 파일을 선택해야 합니다.")
            return

        # 저장할 위치 선택
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "병합된 PDF 저장",
            os.path.join(initial_dir, 'merged.pdf'),
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return
            
        success, error_msg = PDFProcessor.merge_pdfs(file_paths, save_path)
        if success:
            QMessageBox.information(self, "완료", f"PDF 병합이 완료되었습니다:\n{save_path}")
            self.load_pdf(save_path)
        else:
            QMessageBox.critical(self, "오류", f"PDF 병합 중 오류가 발생했습니다:\n{error_msg}")

    def extract_pages_dialog(self):
        if not self.processor.is_open:
            QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("페이지 추출")
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        max_page = self.processor.page_count
        
        start_spin = QSpinBox()
        start_spin.setRange(1, max_page)
        start_spin.setValue(1)
        
        end_spin = QSpinBox()
        end_spin.setRange(1, max_page)
        end_spin.setValue(max_page)
        
        form_layout.addRow("시작 페이지:", start_spin)
        form_layout.addRow("끝 페이지:", end_spin)
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            start_page = start_spin.value()
            end_page = end_spin.value()
            
            if start_page > end_page:
                QMessageBox.warning(self, "오류", "끝 페이지가 시작 페이지보다 클 수 없습니다.")
                return
                
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            initial_dir = os.path.join(base_dir, 'pdfs')
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "추출한 PDF 저장",
                os.path.join(initial_dir, 'extracted.pdf'),
                "PDF Files (*.pdf)"
            )
            
            if not save_path:
                return
                
            success, error_msg = PDFProcessor.extract_pages(
                self.processor._filepath, save_path, start_page, end_page)
                
            if success:
                QMessageBox.information(self, "완료", f"PDF 추출이 완료되었습니다:\n{save_path}")
                self.load_pdf(save_path)
            else:
                QMessageBox.critical(self, "오류", f"PDF 추출 중 오류가 발생했습니다:\n{error_msg}")

    def extract_text_dialog(self):
        if not self.processor.is_open:
            QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
            return
            
        current_row = self.page_list_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "알림", "텍스트를 추출할 페이지가 선택되지 않았습니다.")
            return
            
        extracted_text = self.processor.get_page_text(current_row)
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"텍스트 추출 - 페이지 {current_row + 1}")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setPlainText(extracted_text)
        text_edit.setReadOnly(True)  # 복사는 가능하되 편집은 불가하게
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.exec()

    def optimize_pdf_dialog(self):
        if not self.processor.is_open:
            QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
            return

        self._save_current_edits()
        if self.page_edits_map:
            reply = QMessageBox.question(
                self, 
                "저장 확인", 
                "편집 중인 내용이 있습니다. 현재 편집본을 임시로 원본에 통합한 후 최적화를 진행하시겠습니까?\n(아니오를 선택하면 편집 전 원본 상태만 최적화됩니다.)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Cancel:
                return
            elif reply == QMessageBox.StandardButton.Yes:
                # 사용자가 편집한 내용을 원본 파일에 덮어써서 임시 통합
                success, msg = self.processor.save_edited_pdf(self.processor._filepath, self.page_edits_map)
                if success:
                    self.page_edits_map.clear()
                    self.load_pdf(self.processor._filepath)
                else:
                    QMessageBox.warning(self, "오류", f"통합 저장 중 오류가 발생했습니다: {msg}")
                    return

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        initial_dir = os.path.join(base_dir, 'pdfs')
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "최적화된 PDF 저장",
            os.path.join(initial_dir, 'optimized.pdf'),
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return
            
        original_size = os.path.getsize(self.processor._filepath)
        
        success, error_msg = self.processor.optimize_pdf(save_path)
        if success:
            optimized_size = os.path.getsize(save_path)
            
            # 용량 차이 계산 (KB 단위)
            orig_kb = original_size / 1024
            opti_kb = optimized_size / 1024
            saved_percent = (1 - optimized_size / original_size) * 100 if original_size > 0 else 0
            
            msg = (f"PDF 최적화가 완료되었습니다!\n\n"
                   f"저장 경로: {save_path}\n"
                   f"원본 용량: {orig_kb:.1f} KB\n"
                   f"최적화 용량: {opti_kb:.1f} KB\n"
                   f"용량 절감률: {saved_percent:.1f}%")
            QMessageBox.information(self, "완료", msg)
            self.load_pdf(save_path)
        else:
            QMessageBox.critical(self, "오류", f"최적화 중 오류가 발생했습니다:\n{error_msg}")

    def secure_pdf_dialog(self):
        if not self.processor.is_open:
            QMessageBox.warning(self, "알림", "열려있는 PDF 파일이 없습니다.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("PDF 보안 저장 설정")
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()

        # 암호 입력
        user_pw_input = QLineEdit()
        user_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        user_pw_input.setPlaceholderText("비워두면 암호 없이 열 수 있음")
        
        owner_pw_input = QLineEdit()
        owner_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        owner_pw_input.setPlaceholderText("권한을 우회하기 위한 마스터 암호")
        
        # 권한 체크박스
        chk_print = QCheckBox("인쇄 허용")
        chk_print.setChecked(True)
        
        chk_copy = QCheckBox("복사 허용 (텍스트/이미지)")
        chk_copy.setChecked(True)
        
        chk_edit = QCheckBox("수정 및 주석 허용")
        chk_edit.setChecked(True)
        
        form_layout.addRow("열기 암호:", user_pw_input)
        form_layout.addRow("소유자 암호:", owner_pw_input)
        form_layout.addRow("권한 설정:", chk_print)
        form_layout.addRow("", chk_copy)
        form_layout.addRow("", chk_edit)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            initial_dir = os.path.join(base_dir, 'pdfs')
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "보안이 적용된 PDF 저장",
                os.path.join(initial_dir, 'secured.pdf'),
                "PDF Files (*.pdf)"
            )
            
            if not save_path:
                return
                
            success, error_msg = self.processor.save_with_security(
                output_path=save_path,
                user_pw=user_pw_input.text(),
                owner_pw=owner_pw_input.text(),
                allow_print=chk_print.isChecked(),
                allow_copy=chk_copy.isChecked(),
                allow_edit=chk_edit.isChecked()
            )
            
            if success:
                QMessageBox.information(self, "완료", f"보안 설정된 PDF가 저장되었습니다:\n{save_path}")
                # 암호가 걸린 문서를 다시 로드할 경우 암호 입력 처리가 필요할 수 있으므로
                # 여기서는 재로드하지 않고 안내문만 표시. (혹은 향후 암호 입력 프롬프트 구현 가능)
            else:
                QMessageBox.critical(self, "오류", f"보안 설정 저장 중 오류가 발생했습니다:\n{error_msg}")

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
