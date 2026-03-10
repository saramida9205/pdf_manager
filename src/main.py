import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from main_window import MainWindow

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def main():
    # PyQt 애플리케이션 실행
    app = QApplication(sys.argv)
    
    # 앱 및 윈도우 기본 아이콘 설정
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 프로젝트 스크립트 위치 기준으로 상위 폴더의 pdfs 디렉토리 경로 지정
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_dir = os.path.join(base_dir, 'pdfs')
    
    # pdfs 폴더가 없으면 생성
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)
        print(f"작업용 '{pdf_dir}' 폴더가 생성되었습니다.")
    
    # 세련된 QSS 스타일 디자인 적용 (모던 라이트/블루 포인트 테마)
    style_sheet = """
    QMainWindow {
        background-color: #f5f6fa;
    }
    QMenuBar {
        background-color: #ffffff;
        border-bottom: 1px solid #dcdde1;
        padding: 4px;
        font-weight: bold;
    }
    QMenuBar::item {
        spacing: 3px;
        padding: 4px 10px;
        background: transparent;
        border-radius: 4px;
    }
    QMenuBar::item:selected {
        background-color: #e1b12c;
        color: white;
    }
    QMenu {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        padding: 5px;
    }
    QMenu::item:selected {
        background-color: #f5f6fa;
        color: #2f3640;
    }
    QListWidget {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        border-radius: 5px;
        padding: 5px;
        font-size: 14px;
        color: #2f3640;
    }
    QListWidget::item {
        padding: 8px;
        border-bottom: 1px solid #f5f6fa;
    }
    QListWidget::item:selected {
        background-color: #e1b12c;
        color: white;
        border-radius: 4px;
    }
    QPushButton {
        background-color: #0097e6;
        color: white;
        border: none;
        padding: 8px 16px;
        text-align: center;
        text-decoration: none;
        font-size: 13px;
        font-weight: bold;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #00a8ff;
    }
    QPushButton:pressed {
        background-color: #0082c8;
    }
    QLineEdit, QTextEdit, QComboBox, QSpinBox {
        border: 1px solid #dcdde1;
        border-radius: 4px;
        padding: 4px 8px;
        background-color: #ffffff;
        color: #2f3640;
    }
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
        border: 1px solid #0097e6;
    }
    QLabel {
        color: #2f3640;
        font-weight: bold;
    }
    QGraphicsView {
        background-color: #e84118;
        background-color: #dcdde1; /* 뷰어 바깥 배경은 살짝 어둡게 */
        border: 1px solid #dcdde1;
        border-radius: 5px;
    }
    QSplitter::handle {
        background-color: #dcdde1;
    }
    """
    app.setStyleSheet(style_sheet)
    
    # 명령행 인수(sys.argv)를 통해 전달받은 외부 파일 경로 탐색
    initial_file = None
    if len(sys.argv) > 1:
        potential_path = sys.argv[1]
        if os.path.exists(potential_path) and potential_path.lower().endswith(".pdf"):
            initial_file = potential_path
            
    window = MainWindow(initial_file)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
