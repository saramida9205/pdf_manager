import fitz
from PIL import Image
import io

def test_optimize():
    doc = fitz.open()
    page = doc.new_page()
    # Create a dummy image
    img = Image.new('RGB', (1000, 1000), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    
    # Insert it to a 200x200 pt rect (PPI = 1000 / (200/72) = 360 ppi)
    rect = fitz.Rect(0, 0, 200, 200)
    page.insert_image(rect, stream=img_byte_arr.getvalue())
    
    # Process images on the page
    for item in page.get_images():
        xref = item[0]
        pix = fitz.Pixmap(doc, xref)
        print(f"XREF: {xref}, W: {pix.width}, H: {pix.height}, CS.n: {pix.colorspace.n if pix.colorspace else 'None'}, alpha: {pix.alpha}")
        
        # Calculate PPI
        rects = page.get_image_rects(xref)
        if rects:
            for r in rects:
                ppi_x = pix.width / (r.width / 72.0)
                ppi_y = pix.height / (r.height / 72.0)
                ppi = max(ppi_x, ppi_y)
                print(f"PPI: {ppi}")
                
        # Replacing the image using update_stream or replace_image
        # But wait, there's no doc.update_image()
        # To replace an image, PyMuPDF provides:
        # doc.update_stream(xref, new_stream) -> Updates ONLY the stream data. The width/height/colorspace parameters in the xref dictionary remain unchanged!!
        # This means if we resize the image, we CANNOT easily use doc.update_stream without also updating the dictionary, which is possible but hard.

    doc.save("test_opt.pdf")
    
if __name__ == '__main__':
    test_optimize()
