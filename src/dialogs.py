import os
from PyQt6.QtWidgets import (
    QMessageBox, QFileDialog, QDialog, QVBoxLayout, QFormLayout,
    QSpinBox, QDialogButtonBox, QTextEdit, QLineEdit, QCheckBox, QHBoxLayout, QComboBox, QPushButton
)
from pdf_processor import PDFProcessor

def export_images_dialog(main_window):
    if not main_window.processor.is_open:
        QMessageBox.warning(main_window, "알림", "열려있는 PDF 파일이 없습니다.")
        return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    initial_dir = os.path.join(base_dir, 'pdfs')
    
    save_path, selected_filter = QFileDialog.getSaveFileName(
        main_window,
        "이미지로 내보내기",
        os.path.join(initial_dir, "extracted_images"),
        "PNG Images (*.png);;JPEG Images (*.jpg);;TIFF Images (*.tif);;Multi-page TIFF (*.tif)"
    )
    
    if not save_path:
        return
        
    img_format = "png"
    if "PNG" in selected_filter:
        img_format = "png"
    elif "JPEG" in selected_filter:
        img_format = "jpg"
    elif "Multi-page" in selected_filter:
        img_format = "tif_multi"
    elif "TIFF" in selected_filter:
        img_format = "tif"
        
    output_target = save_path
    if img_format != "tif_multi":
        output_target, _ = os.path.splitext(save_path)
        
    success, error_msg = main_window.processor.save_as_images(output_target, img_format)
    
    if success:
        QMessageBox.information(main_window, "완료", f"이미지 변환이 완료되었습니다:\n{output_target}")
    else:
        QMessageBox.critical(main_window, "오류", f"이미지 변환 중 오류가 발생했습니다:\n{error_msg}")


def import_images_dialog(main_window):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    initial_dir = os.path.join(base_dir, 'pdfs')
    
    img_paths, _ = QFileDialog.getOpenFileNames(
        main_window,
        "PDF로 묶을 이미지 선택",
        initial_dir,
        "Images (*.png *.jpg *.jpeg *.tif *.tiff);;All Files (*)"
    )
    
    if not img_paths:
        return
        
    save_path, _ = QFileDialog.getSaveFileName(
        main_window,
        "새 PDF 저장",
        os.path.join(initial_dir, 'from_images.pdf'),
        "PDF Files (*.pdf)"
    )
    
    if not save_path:
        return
        
    success, error_msg = PDFProcessor.images_to_pdf(img_paths, save_path)
    if success:
        QMessageBox.information(main_window, "완료", f"새 PDF 파일이 생성되었습니다:\n{save_path}")
        main_window.load_pdf(save_path)
    else:
        QMessageBox.critical(main_window, "오류", f"PDF 생성 중 오류가 발생했습니다:\n{error_msg}")


def merge_pdfs_dialog(main_window):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    initial_dir = os.path.join(base_dir, 'pdfs')
    
    file_paths, _ = QFileDialog.getOpenFileNames(
        main_window,
        "병합할 PDF 파일들 선택",
        initial_dir,
        "PDF Files (*.pdf)"
    )
    
    if not file_paths or len(file_paths) < 2:
        if len(file_paths) == 1:
            QMessageBox.warning(main_window, "알림", "병합하려면 2개 이상의 PDF 파일을 선택해야 합니다.")
        return

    save_path, _ = QFileDialog.getSaveFileName(
        main_window,
        "병합된 PDF 저장",
        os.path.join(initial_dir, 'merged.pdf'),
        "PDF Files (*.pdf)"
    )
    
    if not save_path:
        return
        
    success, error_msg = PDFProcessor.merge_pdfs(file_paths, save_path)
    if success:
        QMessageBox.information(main_window, "완료", f"PDF 병합이 완료되었습니다:\n{save_path}")
        main_window.load_pdf(save_path)
    else:
        QMessageBox.critical(main_window, "오류", f"PDF 병합 중 오류가 발생했습니다:\n{error_msg}")


class ExtractPagesDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("페이지 추출")
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        max_page = self.main_window.processor.page_count
        
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, max_page)
        self.start_spin.setValue(1)
        
        self.end_spin = QSpinBox()
        self.end_spin.setRange(1, max_page)
        self.end_spin.setValue(max_page)
        
        form_layout.addRow("시작 페이지:", self.start_spin)
        form_layout.addRow("끝 페이지:", self.end_spin)
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def extract(self):
        start_page = self.start_spin.value()
        end_page = self.end_spin.value()
        
        if start_page > end_page:
            QMessageBox.warning(self, "오류", "끝 페이지가 시작 페이지보다 클 수 없습니다.")
            return
            
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        initial_dir = os.path.join(base_dir, 'pdfs')
        save_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "추출한 PDF 저장",
            os.path.join(initial_dir, 'extracted.pdf'),
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return
            
        success, error_msg = PDFProcessor.extract_pages(
            self.main_window.processor._filepath, save_path, start_page, end_page)
            
        if success:
            QMessageBox.information(self.main_window, "완료", f"PDF 추출이 완료되었습니다:\n{save_path}")
            self.main_window.load_pdf(save_path)
        else:
            QMessageBox.critical(self.main_window, "오류", f"PDF 추출 중 오류가 발생했습니다:\n{error_msg}")

def show_extract_pages_dialog(main_window):
    if not main_window.processor.is_open:
        QMessageBox.warning(main_window, "알림", "열려있는 PDF 파일이 없습니다.")
        return
    dialog = ExtractPagesDialog(main_window)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        dialog.extract()


def show_extract_text_dialog(main_window):
    if not main_window.processor.is_open:
        QMessageBox.warning(main_window, "알림", "열려있는 PDF 파일이 없습니다.")
        return
        
    current_row = main_window.page_list_widget.currentRow()
    if current_row < 0:
        QMessageBox.warning(main_window, "알림", "텍스트를 추출할 페이지가 선택되지 않았습니다.")
        return
        
    extracted_text = main_window.processor.get_page_text(current_row)
    
    dialog = QDialog(main_window)
    dialog.setWindowTitle(f"텍스트 추출 - 페이지 {current_row + 1}")
    dialog.resize(600, 400)
    
    layout = QVBoxLayout(dialog)
    
    text_edit = QTextEdit()
    text_edit.setPlainText(extracted_text)
    text_edit.setReadOnly(True)
    layout.addWidget(text_edit)
    
    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)
    
    dialog.exec()


def optimize_pdf_dialog(main_window):
    if not main_window.processor.is_open:
        QMessageBox.warning(main_window, "알림", "열려있는 PDF 파일이 없습니다.")
        return

    main_window._save_current_edits()
    if main_window.page_edits_map:
        reply = QMessageBox.question(
            main_window, 
            "저장 확인", 
            "편집 중인 내용이 있습니다. 현재 편집본을 임시로 원본에 통합한 후 최적화를 진행하시겠습니까?\n(아니오를 선택하면 편집 전 원본 상태만 최적화됩니다.)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        elif reply == QMessageBox.StandardButton.Yes:
            success, msg = main_window.processor.save_edited_pdf(main_window.processor._filepath, main_window.page_edits_map)
            if success:
                main_window.page_edits_map.clear()
                main_window.load_pdf(main_window.processor._filepath)
            else:
                QMessageBox.warning(main_window, "오류", f"통합 저장 중 오류가 발생했습니다: {msg}")
                return

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    initial_dir = os.path.join(base_dir, 'pdfs')
    
    save_path, _ = QFileDialog.getSaveFileName(
        main_window,
        "최적화된 PDF 저장",
        os.path.join(initial_dir, 'optimized.pdf'),
        "PDF Files (*.pdf)"
    )
    
    if not save_path:
        return
        
    original_size = os.path.getsize(main_window.processor._filepath)
    
    success, error_msg = main_window.processor.optimize_pdf(save_path)
    if success:
        optimized_size = os.path.getsize(save_path)
        orig_kb = original_size / 1024
        opti_kb = optimized_size / 1024
        saved_percent = (1 - optimized_size / original_size) * 100 if original_size > 0 else 0
        
        msg = (f"PDF 최적화가 완료되었습니다!\n\n"
               f"저장 경로: {save_path}\n"
               f"원본 용량: {orig_kb:.1f} KB\n"
               f"최적화 용량: {opti_kb:.1f} KB\n"
               f"용량 절감률: {saved_percent:.1f}%")
        QMessageBox.information(main_window, "완료", msg)
        main_window.load_pdf(save_path)
    else:
        QMessageBox.critical(main_window, "오류", f"최적화 중 오류가 발생했습니다:\n{error_msg}")


class SecurePDFDialog(QDialog):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle("PDF 보안 저장 설정")
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.user_pw_input = QLineEdit()
        self.user_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.user_pw_input.setPlaceholderText("비워두면 암호 없이 열 수 있음")
        
        self.owner_pw_input = QLineEdit()
        self.owner_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.owner_pw_input.setPlaceholderText("권한을 우회하기 위한 마스터 암호")
        
        self.chk_print = QCheckBox, QHBoxLayout, QComboBox, QPushButton("인쇄 허용")
        self.chk_print.setChecked(True)
        
        self.chk_copy = QCheckBox, QHBoxLayout, QComboBox, QPushButton("복사 허용 (텍스트/이미지)")
        self.chk_copy.setChecked(True)
        
        self.chk_edit = QCheckBox, QHBoxLayout, QComboBox, QPushButton("수정 및 주석 허용")
        self.chk_edit.setChecked(True)
        
        form_layout.addRow("열기 암호:", self.user_pw_input)
        form_layout.addRow("소유자 암호:", self.owner_pw_input)
        form_layout.addRow("권한 설정:", self.chk_print)
        form_layout.addRow("", self.chk_copy)
        form_layout.addRow("", self.chk_edit)
        
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def secure_save(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        initial_dir = os.path.join(base_dir, 'pdfs')
        save_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "보안이 적용된 PDF 저장",
            os.path.join(initial_dir, 'secured.pdf'),
            "PDF Files (*.pdf)"
        )
        
        if not save_path:
            return
            
        success, error_msg = self.main_window.processor.save_with_security(
            output_path=save_path,
            user_pw=self.user_pw_input.text(),
            owner_pw=self.owner_pw_input.text(),
            allow_print=self.chk_print.isChecked(),
            allow_copy=self.chk_copy.isChecked(),
            allow_edit=self.chk_edit.isChecked()
        )
        
        if success:
            QMessageBox.information(self.main_window, "완료", f"보안 설정된 PDF가 저장되었습니다:\n{save_path}")
        else:
            QMessageBox.critical(self.main_window, "오류", f"보안 설정 저장 중 오류가 발생했습니다:\n{error_msg}")

def show_secure_pdf_dialog(main_window):
    if not main_window.processor.is_open:
        QMessageBox.warning(main_window, "알림", "열려있는 PDF 파일이 없습니다.")
        return
    dialog = SecurePDFDialog(main_window)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        dialog.secure_save()

    def add_watermark(self, output_path, wm_type="text", content="", pages="all", position="center", opacity=0.5, color=(0.4, 0.4, 0.4)):
        if not self.is_open:
            return False, "열려있는 문서가 없습니다."
            
        try:
            out_pdf = fitz.open()
            out_pdf.insert_pdf(self._document)
            
            for i in range(out_pdf.page_count):
                if pages != "all" and i not in pages:
                    continue
                    
                page = out_pdf[i]
                rect = page.rect
                
                if wm_type == "text":
                    font_size = min(rect.width, rect.height) / 8
                    
                    # Estimate text width (rough)
                    text_length = fitz.get_text_length(content, fontname="helv", fontsize=font_size)
                    
                    if position == "center":
                        x = (rect.width - text_length) / 2
                        y = (rect.height + font_size) / 2
                    elif position == "top_left":
                        x = 50
                        y = 50 + font_size
                    elif position == "bottom_right":
                        x = rect.width - text_length - 50
                        y = rect.height - 50
                    else: # default
                        x, y = 50, 50
                        
                    point = fitz.Point(x, y)
                    page.insert_text(point, content, fontsize=font_size, color=color, fill_opacity=opacity)
                    
                elif wm_type == "image":
                    import os
                    if not os.path.exists(content):
                        continue
                        
                    # Calculate position (center 50% width)
                    w = rect.width * 0.5
                    h = rect.height * 0.5
                    
                    if position == "center":
                        x0 = (rect.width - w) / 2
                        y0 = (rect.height - h) / 2
                    elif position == "top_left":
                        x0, y0 = 50, 50
                    elif position == "bottom_right":
                        x0 = rect.width - w - 50
                        y0 = rect.height - h - 50
                    else:
                        x0, y0 = 50, 50
                        
                    img_rect = fitz.Rect(x0, y0, x0 + w, y0 + h)
                    page.insert_image(img_rect, filename=content, keep_proportion=True) # opacity may not be directly supported without altering alpha
                    
            out_pdf.save(output_path, garbage=4, deflate=True)
            out_pdf.close()
            return True, ""
        except Exception as e:
            return False, str(e)
