"""
这个是input 对话窗口 DONE,还没做完.
"""

from ..obj import MenuAdder
from ...lib.dialogs.UIdialog_Input import Ui_input
from ...lib.obj.inputObj import *
from .DialogCardPrev import external_card_dialog

class InputDialog(QDialog, Ui_input):
    """INPUT对话窗口类"""
    model: Union[QStandardItemModel, QStandardItemModel]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.input: Input = Input()
        self.baseinfo = BaseInfo()
        self.config = self.baseinfo.config_obj
        self.signup()
        self.model_dataSelected: List[List[Pair]] = []
        self.model_data: List[List[Pair]] = []
        self.UI_init()
        self.model_init()
        self.events_init()
        self.show()
        console("初始化完成!").log.end()

    def signup(self):
        """注册到主窗口"""
        addonName = self.baseinfo.dialogName
        dialog = self.__class__.__name__
        mw.__dict__[addonName][dialog] = self

    def signout(self):
        """注销"""
        addonName = self.baseinfo.dialogName
        dialog = self.__class__.__name__
        mw.__dict__[addonName][dialog] = None

    # @debugWatcher
    def UI_init(self, *args, **kwargs):
        """初始化UI"""
        self.setupUi(self)
        self.inputTree.parent = self
        iconDir = os.path.join(THIS_FOLDER, self.baseinfo.baseinfo["iconFile_input"])
        self.setWindowIcon(QIcon(iconDir))
        # self.setWindowIcon(QIcon(":/" + self.baseinfo.baseinfo["iconFile_input"]))
        self.inputTree.customContextMenuRequested.connect(self.onInputTree_contextMenu)

    # noinspection PyAttributeOutsideInit
    # @debugWatcher
    def events_init(self, *args, **kwargs):
        """事件的初始化"""
        # self.closeEvent = self.onClose
        self.inputTree.doubleClicked.connect(self.onDoubleClick)
        self.inputTree.dropEvent = self.onDrop
        self.inputTree.dragEnterEvent = self.onDragEnter
        self.closeEvent = self.onClose
        self.fileWatcher = QFileSystemWatcher()
        self.fileWatcher.addPath(self.baseinfo.inputDir)
        self.fileWatcher.fileChanged.connect(self.model_dataobj_load)
        self.model.dataChanged.connect(self.file_model_save)
        self.tagContent.textChanged.connect(self.file_tag_save)

    # @debugWatcher
    def model_init(self, *args, **kwargs):
        """模型数据的初始化"""
        self.model = QStandardItemModel()
        self.model_rootNode = self.model.invisibleRootItem()
        self.model_rootNode.setDropEnabled(False)
        self.model_rootNode.setEditable(False)
        self.model_rootNode.setSelectable(False)
        self.model_rootNode.setDragEnabled(False)
        self.model.setHorizontalHeaderLabels(["card_id", "desc"])
        self.inputTree.setModel(self.model)
        self.model_dataobj_load()

    def onDragEnter(self, e):
        """移入事件"""
        e.acceptProposedAction()

    # @debugWatcher
    def onInputTree_contextMenu(self, *args, **kwargs):
        """初始化右键菜单"""
        menu = self.inputTree.contextMenu = QMenu()
        prefix = BaseInfo().consolerName
        menu.addAction(prefix + say("全部展开/折叠")).triggered.connect(self.view_expandCollapse_toggle)
        if len(self.inputTree.selectedIndexes()) > 0:
            self.pairli_selected_load()
            menu.addAction(prefix + say("选中删除")).triggered.connect(self.view_selected_delete)
            param = Params(menu=menu, parent=self.inputTree, features=["prefix", "selected"], actionTypes=["link"])
            MenuAdder.func_menuAddHelper(**param.__dict__)
        param = Params(menu=menu, parent=self.inputTree, features=["prefix"], actionTypes=["link", "clear_open"])
        MenuAdder.func_menuAddHelper(**param.__dict__)
        menu.popup(QCursor.pos())
        menu.show()

    def itemChild_row_insert(self, parent, item_after, item_insertLi):
        """自己实现了一个插入"""
        templi, r = [], item_after.row()
        item_after_row = [parent.child(r, 0), parent.child(r, 1)]
        while parent.rowCount() > 0:
            row0 = parent.takeRow(0)
            # if item_after == row0[0]:
            # showInfo(f"item_after={item_after.text()}  row0[0]={row0[0].text()}")
            templi.append(row0)
        [templi.remove(i) if i in templi else None for i in item_insertLi]
        # showInfo("item_after="+item_after.text()+"item_after_row="+item_after_row.__str__())
        if item_after_row[0] != None:
            index = templi.index(item_after_row)
        else:
            index = len(templi)
        templi = templi[0:index + 1] + item_insertLi + templi[index + 1:]
        for i in templi:
            parent.appendRow(i)

    def itemChild_row_remove(self, item):
        """不需要parent,自己能产生parent, item = list[item,item]"""
        parent = item[0].parent() if item[0].parent() is not None else self.model_rootNode
        return parent.takeRow(item[0].row())

    def itemGroup_create(self, parent=None):
        """创建group"""
        if parent:
            root = parent
        else:
            root = self.model_rootNode
        item_group = QStandardItem("group")
        item_group.self_attrs = {"character": "group", "level": 0, "primData": item_group}
        item_group.setFlags(item_group.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsSelectable)
        item_empty = QStandardItem("")
        item_empty.setFlags(item_empty.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsDropEnabled & ~Qt.ItemIsDragEnabled)
        item_group.self_attrs = {"character": "empty", "level": 0, "primData": item_group}
        root.appendRow([item_group, item_empty])
        return item_group

    # @debugWatcher
    def onDrop(self, *args, **kwargs):
        """掉落事件响应"""
        e = args[0]
        mimeData = e.mimeData()
        root = self.model_rootNode
        drop_row = self.inputTree.indexAt(e.pos())
        item_target = self.model.itemFromIndex(drop_row)

        selectedIndexesLi = self.inputTree.selectedIndexes()
        selectedItemLi_ = list(map(self.model.itemFromIndex, selectedIndexesLi))
        selectedItemLi = []
        for i in range(int(len(selectedItemLi_) / 2)):
            selectedItemLi.append([selectedItemLi_[2 * i], selectedItemLi_[2 * i + 1]])
        item_finalLi = [self.itemChild_row_remove(i) for i in selectedItemLi]
        if item_target is None:
            item_target = self.itemGroup_create()
        target_parent = item_target.parent() if item_target.parent() is not None else root
        if item_target.column() > 0:
            item_target = target_parent.child(item_target.row(), 0)
        if item_target.self_attrs["level"] == 0:
            list(map(lambda x: item_target.appendRow(x), item_finalLi))
        if item_target.self_attrs["level"] == 1:
            self.itemChild_row_insert(item_target.parent(), item_target, item_finalLi)
        j = 0
        for i in range(root.rowCount()):
            if root.child(j, 0).rowCount() == 0:
                root.takeRow(j)
            else:
                j += 1
            if j == root.rowCount(): break
        self.file_model_save()

    # @debugWatcher
    def onDoubleClick(self, index, *args, **kwargs):
        """双击事件响应"""
        item = self.model.itemFromIndex(index)
        if item.column() == 0 and item.self_attrs["level"] == 1 and item.self_attrs["character"] == "card_id":
            card = self.input.model.col.getCard(int(item.text()))
            external_card_dialog(card)

    # @debugWatcher
    def onRowRemoved(self, *args, **kwargs):
        """移除行时响应"""
        self.file_model_save()

    # @debugWatcher
    def onClose(self, QCloseEvent):
        """关闭时要保存数据,QCloseEvent是有用的参数,不能删掉,否则会报错"""
        self.signout()
        if len(self.model_data) > 0:
            self.file_model_save()
        else:
            self.input.dataReset().dataSave().end()

    # @debugWatcher
    def view_selected_delete(self, *args, **kwargs):
        """选中的部分删除"""
        selectedIndexesLi = self.inputTree.selectedIndexes()
        selectedItemLi_ = list(map(self.model.itemFromIndex, selectedIndexesLi))
        selectedItemLi = []
        for i in range(int(len(selectedItemLi_) / 2)):
            selectedItemLi.append([selectedItemLi_[2 * i], selectedItemLi_[2 * i + 1]])
        item_finalLi = [self.itemChild_row_remove(i) for i in selectedItemLi]
        self.file_model_save()
        console(say("已删除选中卡片")).talk.end()

    # @debugWatcher
    def view_expandCollapse_toggle(self, *args, **kwargs):
        """切换input对话框的折叠和展开状态"""
        if self.treeIsExpanded:
            root = self.model_rootNode
            tree = self.inputTree
            list(map(lambda i: tree.collapse(root.child(i).index()), list(range(root.rowCount()))))
            self.treeIsExpanded = False
        else:
            self.inputTree.expandAll()
            self.treeIsExpanded = True

    # @debugWatcher
    def file_model_save(self, *args, **kwargs):
        """保存文件"""
        self.JSON_model_load()
        self.input.data = self.model_data if self.model_data != [] else self.input.initDict
        self.input.dataSave().end()

    # @debugWatcher
    def model_tag_load(self, *args, **kwargs):
        """load tag to model"""
        self.tagContent.setText(self.input.dataLoad().tag)

    # @debugWatcher
    def model_dataobj_load(self, *args, **kwargs):
        """从JSON读取到模型"""
        self.model_data: List[List[Pair]] = self.input.dataLoad().val()
        self.model_rootNode.clearData()
        self.model.removeRows(0, self.model.rowCount())
        root = self.model_rootNode

        for group in self.model_data:
            parent = self.itemGroup_create()
            for info in group:
                self.carditem_make(info, level=1, parent=parent)
        self.lastrowcount = self.model_rootNode.rowCount()
        self.inputTree.expandAll()
        self.treeIsExpanded = True
        self.model_tag_load()

    def carditem_make(self, pair, level=0, parent=None):
        """一个简便的函数"""
        if parent is None: parent = self.model_rootNode
        item_id, item_desc = QStandardItem(pair.card_id), QStandardItem(pair.desc)
        item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable & ~Qt.ItemIsDropEnabled)
        item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsDropEnabled & ~Qt.ItemIsDragEnabled)
        item_id.self_attrs = {"character": "card_id", "level": level, "primData": pair}
        item_desc.self_attrs = {"character": "desc", "level": level, "primData": pair}
        parent.appendRow([item_id, item_desc])

    # @debugWatcher
    def JSON_model_load(self, *args, **kwargs):
        """从树中读取json"""

        self.model_data: List[List[Pair]] = self.input.dataReset().dataObj().val()
        self.input.tag = self.tagContent.text()
        self.JSON_model_load_sub()

    # @debugWatcher
    def JSON_model_load_sub(self, *args, **kwargs):
        """是一个子函数"""
        for i in range(self.model_rootNode.rowCount()):
            # console("model_data=" + self.model_data.__str__()).log.end()
            # console(f"self.model_rootNode.child({i.__str__()}).rowCount()=" + self.model_rootNode.child(
            #     i).rowCount().__str__()).log.end()
            if self.model_rootNode.child(i).rowCount() == 0:
                continue
            else:
                self.model_data.append([])
                group = self.model_rootNode.child(i)
                for j in range(group.rowCount()):
                    pair = Pair(card_id=group.child(j, 0).text(), desc=group.child(j, 1).text())
                    self.model_data[-1].append(pair)

    # @debugWatcher
    def pairli_selected_load(self):
        """从选中的项目中读取出JSON列表,保存在InputObj的data中,他只要不存到本地就没事情"""
        selectedItemLi_ = list(map(self.model.itemFromIndex, self.inputTree.selectedIndexes()))
        selectedItemLi = []
        for i in range(int(len(selectedItemLi_) / 2)):
            selectedItemLi.append([selectedItemLi_[2 * i], selectedItemLi_[2 * i + 1]])
        selectedItemLi.sort(key=lambda x: x[0].parent().row())
        pairLi = [[Pair(card_id=selectedItemLi[0][0].text(), desc=selectedItemLi[0][1].text())]]

        def areducer(x, y):
            """用来做事情"""
            if x is None or y is None:
                return None
            p = Pair(card_id=y[0].text(), desc=y[1].text())
            pairLi[-1].append(p) if x[0].parent().row() == y[0].parent().row() else pairLi.append([p])
            return y

        reduce(lambda x, y: areducer(x, y), selectedItemLi)
        # showInfo(pairLi.__str__())
        self.input.data = pairLi
        self.input.tag = self.tagContent.text()

    # @debugWatcher
    def file_tag_save(self, *args, **kwargs):
        """将json保存到文件"""
        self.input.tag = self.tagContent.text()
        self.input.dataSave().end()