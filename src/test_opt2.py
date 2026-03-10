import fitz
from PIL import Image
import io
import math

def get_pil_image_from_pixmap(pix):
    if pix.n - pix.alpha < 4:       # this is GRAY or RGB
        fmt = "RGBA" if pix.alpha else "RGB"
    else:                           # CMYK: need to convert first
        fmt = "RGBA" if pix.alpha else "RGB"
        pix = fitz.Pixmap(fitz.csRGB, pix)
    return Image.frombytes(fmt, [pix.width, pix.height], pix.samples)

def test_optimize2():
    doc = fitz.open("test_opt.pdf")
    page = doc[0]
    
    # Keep track of replaced xrefs to avoid replacing the same image multiple times
    replaced = set()
    
    images = page.get_images()
    for item in images:
        xref = item[0]
        if xref in replaced:
            continue
            
        pix = fitz.Pixmap(doc, xref)
        
        # Calculate PPI
        rects = page.get_image_rects(xref)
        if not rects:
            continue
            
        # Get maximum PPI across all uses of this image on this page
        max_ppi = 0
        for r in rects:
            ppi_x = pix.width / (r.width / 72.0)
            ppi_y = pix.height / (r.height / 72.0)
            max_ppi = max(max_ppi, ppi_x, ppi_y)
            
        # Determine image type
        is_mono = (pix.colorspace and pix.colorspace.n == 1 and pix.bpc == 1)
        is_gray = (pix.colorspace and pix.colorspace.n == 1 and pix.bpc > 1)
        is_color = (pix.colorspace and pix.colorspace.n >= 3)
        
        if not is_mono and not is_gray and not is_color:
            is_color = True # default
            
        print(f"XREF {xref}: Type -> Mono:{is_mono}, Gray:{is_gray}, Color:{is_color}, PPI:{max_ppi:.1f}")
        
        # Determine target parameters
        needs_downsample = False
        target_ppi = 0
        compress_format = 'JPEG'
        quality = 50
        
        if is_color:
            if max_ppi > 225:
                needs_downsample = True
                target_ppi = 150
            compress_format = 'JPEG'
            quality = 50 # 중간 (Medium)
        elif is_gray:
            if max_ppi > 225:
                needs_downsample = True
                target_ppi = 150
            compress_format = 'JPEG'
            quality = 30 # 낮음 (Low)
        elif is_mono:
            if max_ppi > 450:
                needs_downsample = True
                target_ppi = 300
            compress_format = 'TIFF'
            # Quality argument ignored for TIFF, we use CCITT group 4
            
        pil_img = get_pil_image_from_pixmap(pix)
        
        if needs_downsample:
            scale = target_ppi / max_ppi
            new_w = int(pix.width * scale)
            new_h = int(pix.height * scale)
            if new_w > 0 and new_h > 0:
                print(f"Downsampling {pix.width}x{pix.height} -> {new_w}x{new_h}")
                pil_img = pil_img.resize((new_w, new_h), resample=Image.Resampling.BICUBIC)
                
        out_stream = io.BytesIO()
        if is_mono:
            # CCITT Group 4 compression in TIFF
            # Ensure it's 1-bit format
            if pil_img.mode != '1':
                pil_img = pil_img.convert('1')
            pil_img.save(out_stream, format='TIFF', compression='group4')
        else:
            # JPEG needs RGB mode (no alpha)
            if pil_img.mode in ('RGBA', 'P', 'LA'):
                pil_img = pil_img.convert('RGB')
            pil_img.save(out_stream, format='JPEG', quality=quality, optimize=True)
            
        # Replace the image
        page.replace_image(xref, stream=out_stream.getvalue())
        replaced.add(xref)
        
    doc.save("test_opt_out.pdf", garbage=4, deflate=True)
    print("Saved test_opt_out.pdf")
    
if __name__ == '__main__':
    test_optimize2()
