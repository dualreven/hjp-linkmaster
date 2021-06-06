import sys

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QGraphicsView, QGraphicsScene, QHBoxLayout

from lib.RightSideBar import RightSideBar
from lib.PageInfo import PageInfo


class mainwindow(QMainWindow):
    def __init__(self):
        super().__init__()  # 加载的是文档
        self.init_UI()
        self.init_events()
        # self.init_view()
        # self.showMaximized()
        self.show()

    def init_events(self):
        self.resizeEvent = self.OnResize

    def init_UI(self):
        # 经验：QGraphicsView 必须放置在 QWidget 中， 才能和其他QWidget 保持正常的大小关系
        self.setWindowIcon(QIcon("./resource/icon_window_clipper.png"))
        self.setWindowTitle("PDF clipper")
        self.container0 = QWidget(self)  # 不能删
        self.scene = QGraphicsScene()

        self.pdfview = QGraphicsView(self.scene, parent=self)
        self.rightsidebar = RightSideBar(clipper=self)
        self.h_layout = QHBoxLayout(self)
        self.h_layout.addWidget(self.pdfview)
        self.h_layout.addWidget(self.rightsidebar)
        self.h_layout.setStretch(0, 1)
        rect = QApplication.instance().desktop().availableGeometry(self)
        self.resize(int(rect.width() * 2 / 3), int(rect.height() * 2 / 3))
        self.container0.resize(self.width(), self.height())
        self.container0.setLayout(self.h_layout)

    def OnResize(self, *args):
        self.container0.resize(self.width(), self.height())
        pass

    def scene_pixmap_add(self, pageinfo: 'PageInfo'):
        self.rightsidebar.page_list_add(pageinfo)
        self.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    pageinfo = PageInfo("./resource/徐森林_数学分析_第8章.pdf")
    p = mainwindow()
    p.scene_pixmap_add(pageinfo)
    sys.exit(app.exec_())