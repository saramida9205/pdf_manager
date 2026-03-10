import fitz  # PyMuPDF
import os
from PIL import Image
from PIL import Image

class PDFProcessor:
    @staticmethod
    def merge_pdfs(input_paths, output_path):
        """여러 PDF 파일을 하나로 병합하여 저장합니다."""
        try:
            merged_doc = fitz.open()
            for path in input_paths:
                with fitz.open(path) as doc:
                    merged_doc.insert_pdf(doc)
            merged_doc.save(output_path)
            merged_doc.close()
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def extract_pages(input_path, output_path, start_page, end_page):
        """특정 페이지 범위(1-indexed)를 추출하여 새 PDF로 저장합니다."""
        try:
            with fitz.open(input_path) as doc:
                # 추출할 문서 준비
                extracted_doc = fitz.open()
                # insert_pdf는 0-indexed 기준
                extracted_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)
                
                extracted_doc.save(output_path)
                extracted_doc.close()
                return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def images_to_pdf(image_paths, output_path):
        """여러 이미지 파일 경로를 받아 하나의 PDF 파일로 묶어 저장합니다."""
        try:
            pdf_doc = fitz.open()
            for img_path in image_paths:
                # 이미지를 열어 PDF 바이너리 형식으로 변환
                with fitz.open(img_path) as img_doc:
                    pdf_bytes = img_doc.convert_to_pdf()
                    
                # 변환된 PDF 바이너리를 임시 문서로 열기
                with fitz.open("pdf", pdf_bytes) as temp_pdf:
                    pdf_doc.insert_pdf(temp_pdf)
                    
            pdf_doc.save(output_path)
            pdf_doc.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def optimize_pdf(self, output_path):
        """현재 열려있는 PDF 문서의 최적화(Acrobat 스타일 다운샘플링 등)를 수행하여 새 파일로 저장합니다."""
        if not self._document:
            return False, "열려있는 PDF 파일이 없습니다."
            
        try:
            import io
            
            # 헬퍼 함수: Pixmap을 PIL 이미지로 변환
            def get_pil_image_from_pixmap(pix):
                if pix.n - pix.alpha < 4:       # GRAY or RGB
                    fmt = "RGBA" if pix.alpha else "RGB"
                    temp_pix = pix
                else:                           # CMYK: need to convert to RGB first
                    fmt = "RGBA" if pix.alpha else "RGB"
                    temp_pix = fitz.Pixmap(fitz.csRGB, pix)
                    
                img = Image.frombytes(fmt, [temp_pix.width, temp_pix.height], temp_pix.samples)
                if temp_pix != pix:
                    temp_pix = None # free CMYK temp pixmap
                return img

            # 문서 복사본 생성 (원본 유지)
            # fitz.open()의 stream 기능 등을 쓸 수도 있지만 단순 복사를 위해 임시 바이트를 활용
            opt_doc = fitz.open(stream=self._document.write(), filetype="pdf")
            
            replaced_xrefs = set()
            
            for page in opt_doc:
                images = page.get_images()
                for item in images:
                    xref = item[0]
                    if xref in replaced_xrefs:
                        continue
                        
                    pix = fitz.Pixmap(opt_doc, xref)
                    
                    # Calculate PPI
                    rects = page.get_image_rects(xref)
                    if not rects:
                        continue
                        
                    # 여러 번 쓰인 이미지일 경우 최대 해상도를 기준으로 함
                    max_ppi = 0
                    for r in rects:
                        ppi_x = pix.width / (r.width / 72.0) if r.width > 0 else 0
                        ppi_y = pix.height / (r.height / 72.0) if r.height > 0 else 0
                        max_ppi = max(max_ppi, ppi_x, ppi_y)
                        
                    # Determine image type
                    is_mono = (pix.colorspace and pix.colorspace.n == 1 and pix.bpc == 1)
                    is_gray = (pix.colorspace and pix.colorspace.n == 1 and pix.bpc > 1)
                    is_color = (pix.colorspace and pix.colorspace.n >= 3)
                    
                    if not is_mono and not is_gray and not is_color:
                        is_color = True
                        
                    needs_downsample = False
                    target_ppi = 0
                    compress_format = 'JPEG'
                    quality = 50
                    
                    # 투명도가 있으면 PNG (JPEG는 투명도 지원 X)
                    has_alpha = pix.alpha
                    
                    # 설정 적용 (아크로벳 화면 기준)
                    if is_color:
                        if max_ppi > 225:
                            needs_downsample = True
                            target_ppi = 150
                        compress_format = 'PNG' if has_alpha else 'JPEG'
                        quality = 50 # 중간 (Medium)
                    elif is_gray:
                        if max_ppi > 225:
                            needs_downsample = True
                            target_ppi = 150
                        compress_format = 'PNG' if has_alpha else 'JPEG'
                        quality = 30 # 낮음 (Low)
                    elif is_mono:
                        if max_ppi > 450:
                            needs_downsample = True
                            target_ppi = 300
                        compress_format = 'PNG' if has_alpha else 'TIFF'
                        
                    # 투명도가 있는데 압축해야 하거나 크기를 줄여야 하는 경우 이미지 처리 진행
                    # (단색 TIFF는 투명도 지원 불가)
                    
                    pil_img = get_pil_image_from_pixmap(pix)
                    
                    if needs_downsample:
                        scale = target_ppi / max_ppi
                        new_w = int(pix.width * scale)
                        new_h = int(pix.height * scale)
                        if new_w > 0 and new_h > 0:
                            pil_img = pil_img.resize((new_w, new_h), resample=Image.Resampling.BICUBIC)
                            
                    out_stream = io.BytesIO()
                    
                    if compress_format == 'TIFF' and is_mono:
                        if pil_img.mode != '1':
                            pil_img = pil_img.convert('1')
                        pil_img.save(out_stream, format='TIFF', compression='group4')
                    elif compress_format == 'PNG':
                        pil_img.save(out_stream, format='PNG', optimize=True)
                    else: # JPEG
                        if pil_img.mode in ('RGBA', 'P', 'LA'):
                            pil_img = pil_img.convert('RGB')
                        pil_img.save(out_stream, format='JPEG', quality=quality, optimize=True)
                        
                    # 페이지 내 이미지 교체
                    try:
                        page.replace_image(xref, stream=out_stream.getvalue())
                        replaced_xrefs.add(xref)
                    except Exception as e:
                        # 간혹 손상된 객체로 인해 실패할 수 있음, 이 경우 무시하고 원본 유지
                        print(f"Warning: Failed to replace image xref {xref}: {e}")
            
            # 저장하면서 전체적인 최적화 (가비지 컬렉션 등)
            opt_doc.save(
                output_path, 
                garbage=4, 
                deflate=True, 
                clean=True
            )
            opt_doc.close()
            return True, None
        except Exception as e:
            return False, str(e)

    def save_with_security(self, output_path, user_pw="", owner_pw="", allow_print=True, allow_copy=True, allow_edit=True):
        """현재 PDF 문서를 암호 및 권한 속성을 설정하여 저장합니다."""
        if not self._document:
            return False, "열려있는 PDF 파일이 없습니다."
            
        try:
            # PyMuPDF의 권한 플래그 설정
            # 기본적으로 모든 권한을 막은 상태에서 허용할 권한만 비트 단위 OR 연산으로 추가
            perms = 0
            if allow_print:
                perms |= fitz.PDF_PERM_PRINT
               # 고해상도 인쇄도 허용하는 옵션이 있으면 추가 (fitz.PDF_PERM_PRINT_HQ 로 존재할수도 있음)
            if allow_copy:
                perms |= fitz.PDF_PERM_COPY
            if allow_edit:
                perms |= fitz.PDF_PERM_MODIFY
                perms |= fitz.PDF_PERM_ANNOTATE
                
            # 암호화는 기본적으로 AES 256을 사용
            self._document.save(
                output_path,
                encryption=fitz.PDF_ENCRYPT_AES_256,
                owner_pw=owner_pw,
                user_pw=user_pw,
                permissions=perms
            )
            return True, None
        except Exception as e:
            return False, str(e)

    def add_text_annotation(self, page_number, text, output_path):
        """현재 문서의 특정 페이지 우측 상단에 팝업 텍스트 주석을 추가하고 새 파일로 저장합니다."""
        if not self._document or page_number < 0 or page_number >= len(self._document):
            return False, "유효하지 않은 페이지입니다."
            
        try:
            page = self._document.load_page(page_number)
            rect = page.rect
            
            # 우측 상단 근처에 주석 아이콘 위치 (x: 너비-50, y: 50)
            point = fitz.Point(rect.width - 50, 50)
            
            annot = page.add_text_annot(point, text)
            annot.set_info(title="PDF Manager")
            annot.set_colors(stroke=(1, 1, 0)) # 노란색 아이콘
            annot.update()
            
            self._document.save(output_path)
            return True, None
        except Exception as e:
            return False, str(e)

    def get_annotations(self, page_number):
        """현재 페이지에 등록된 주석 내용들을 리스트로 반환합니다."""
        if not self._document or page_number < 0 or page_number >= len(self._document):
            return []
            
        page = self._document.load_page(page_number)
        annots = []
        for annot in page.annots():
            # 텍스트가 있는 주석 내용 추출
            if annot.info and "content" in annot.info:
                content = annot.info["content"]
                if content:
                    annots.append(content)
        return annots

    def save_edited_pdf(self, output_path, page_edits_map):
        """
        화면에서 수동으로 편집(텍스트 및 이미지 추가)한 내용을 새로운 PDF 파일로 저장합니다.
        page_edits_map: dict mapping page_number to list of edits
        """
        if not self._filepath:
            return False, "열려있는 파일이 없습니다."
        try:
            with fitz.open(self._filepath) as doc:
                # 한국어 지원을 위해 Windows 맑은 고딕 폰트 로드 시도
                fontfile = "C:/Windows/Fonts/malgun.ttf"
                fontname = "ko" if os.path.exists(fontfile) else "helv"
                
                for page_num, edits in page_edits_map.items():
                    page = doc.load_page(page_num)
                    
                    if fontname == "ko":
                        page.insert_font(fontname="ko", fontfile=fontfile)
                        
                    for edit in edits:
                        if edit['type'] == 'text':
                            x, y_start = edit['point']
                            color = (edit['color'][0]/255, edit['color'][1]/255, edit['color'][2]/255)
                            lines = edit['text'].split('\n')
                            
                            # PyMuPDF의 insert_text는 텍스트의 좌측 '하단'을 기준점으로 하므로, 폰트사이즈만큼 Y축을 더해줍니다.
                            y_current = y_start + edit['fontsize']
                            line_height = edit['fontsize'] * 1.2
                            
                            for line in lines:
                                page.insert_text(fitz.Point(x, y_current), line, fontsize=edit['fontsize'], color=color, fontname=fontname)
                                y_current += line_height
                                
                        elif edit['type'] == 'image':
                            rect = fitz.Rect(*edit['rect'])
                            page.insert_image(rect, filename=edit['path'])
                            
                doc.save(output_path)
            return True, None
        except Exception as e:
            return False, str(e)

    def __init__(self):
        self._document = None
        self._filepath = None

    def open_pdf(self, filepath):
        """PDF 파일을 엽니다."""
        try:
            self._document = fitz.open(filepath)
            self._filepath = filepath
            return True, None
        except Exception as e:
            self._document = None
            self._filepath = None
            return False, str(e)

    def close_pdf(self):
        """열려있는 PDF 문서를 닫습니다."""
        if self._document:
            self._document.close()
            self._document = None
            self._filepath = None

    @property
    def is_open(self):
        return self._document is not None

    @property
    def page_count(self):
        """현재 열린 문서의 전체 페이지 수를 반환합니다."""
        if self._document:
            return len(self._document)
        return 0

    def clear_cache(self):
        if hasattr(self, '_image_cache'): self._image_cache.clear()

    def get_page_image(self, page_number, zoom_factor=1.0):
        """
        주어진 페이지 번호(0-indexed)의 이미지를 PIL Image 객체로 반환합니다.
        해상도는 zoom_factor로 조절 가능합니다. (캐시 적용)
        """
        if not hasattr(self, '_image_cache'): self._image_cache = {}
        
        if not self.is_open or page_number < 0 or page_number >= self.page_count:
            return None
            
        cache_key = (page_number, float(zoom_factor))
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]
            
        page = self._document.load_page(page_number)
        mat = fitz.Matrix(zoom_factor, zoom_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        mode = "RGB" if pix.n == 3 else "RGBA"
        img = Image.frombytes(mode, [pix.w, pix.h], pix.samples)
        
        if len(self._image_cache) > 20: 
            self._image_cache.pop(next(iter(self._image_cache)))
            
        self._image_cache[cache_key] = img
        return img

    def get_page_text(self, page_number):
        """
        주어진 페이지 번호(0-indexed)의 텍스트 데이터를 추출하여 문자열로 반환합니다.
        """
        if not self._document or page_number < 0 or page_number >= len(self._document):
            return ""
            
        page = self._document.load_page(page_number)
        return page.get_text()


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


    def highlight_search(self, text):
        if not self.is_open:
            return []
            
        self.clear_cache()
            
        # 1. Remove old search highlights
        for i in range(self._document.page_count):
            page = self._document[i]
            for annot in page.annots():
                if annot.info.get("title") == "SearchHighlight":
                    page.delete_annot(annot)
                    
        # 2. Add new highlights if text is given
        found_pages = []
        if text:
            text = text.lower() # case-insensitive mostly
            for i in range(self._document.page_count):
                page = self._document[i]
                rects = page.search_for(text)
                if rects:
                    if i not in found_pages:
                        found_pages.append(i)
                    for rect in rects:
                        annot = page.add_highlight_annot(rect)
                        info = annot.info
                        info["title"] = "SearchHighlight"
                        annot.set_info(info)
                        annot.update()
        return found_pages

    def save_as_images(self, output_dir_or_file, img_format="png", zoom_factor=2.0):
        """
        문서의 모든 페이지를 이미지로 변환하여 저장합니다.
        
        - img_format이 'tif_multi'일 경우 output_dir_or_file은 대상 파일 경로이며,
          모든 페이지가 하나의 TIF 파일로 묶여 저장됩니다.
        - 그 외(jpg, png, tif 등)일 경우 output_dir_or_file은 대상 폴더 경로이며,
          page_1.png, page_2.png 형식으로 개별 파일로 저장됩니다.
        """
        if not self._document:
            return False, "열려있는 PDF 파일이 없습니다."
            
        try:
            images = []
            for i in range(len(self._document)):
                # 화질을 높이기 위해 기본값으로 zoom_factor 2.0 적용
                img = self.get_page_image(i, zoom_factor=zoom_factor)
                if not img:
                    continue
                images.append(img)
                
            if not images:
                return False, "변환할 이미지 데이터가 없습니다."
                
            if img_format.lower() == "tif_multi":
                # 다중 TIF 저장
                first_img = images[0]
                first_img.save(
                    output_dir_or_file, 
                    save_all=True, 
                    append_images=images[1:], 
                    format="TIFF"
                )
            else:
                # 개별 파일 저장
                fmt = img_format.lower()
                # jpg/jpeg는 명확히 JPEG로 지정
                pil_format = "JPEG" if fmt in ("jpg", "jpeg") else fmt.upper()
                
                if not os.path.exists(output_dir_or_file):
                    os.makedirs(output_dir_or_file)
                    
                for idx, img in enumerate(images):
                    file_name = f"page_{idx + 1}.{fmt}"
                    save_path = os.path.join(output_dir_or_file, file_name)
                    img.save(save_path, format=pil_format)
                    
            return True, None
        except Exception as e:
            return False, str(e)
