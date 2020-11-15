import os, sys, datetime, json, re
# import win32.win32clipboard as clipboard 
# import the main window object (mw) from aqt
from aqt import mw, gui_hooks
from html.parser import HTMLParser
from aqt.browser import Browser
from aqt.reviewer import Reviewer
from aqt.editor import EditorWebView
from aqt.utils import showInfo, tooltip
from aqt.qt import *
from anki.cards import Card
from anki.notes import Note
from anki import hooks
import html

from dataclasses import dataclass
from enum import Enum
from operator import itemgetter
from typing import Callable, List, Optional, Sequence, Tuple, Union

helpSite = "https://gitee.com/huangjipan/hjp-bilink"

inputFileName = "input.json"
configFileName = "config.json"
helpFileName = "README.md"
relyLinkDir = "1423933177"
relyLinkConfigFileName = "config.json"
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
PREV_FOLDER = os.path.dirname(THIS_FOLDER)
RELY_FOLDER = os.path.join(PREV_FOLDER, relyLinkDir)
inputSchema='{"IdDescPairs":[],"addTag":""}'
consolerName="hjp-bilink"
hjp_bilink_VERSION=re.search("(?<=- # hjp-bilink V\")[\w\.]+(?=\")",open(os.path.join(THIS_FOLDER,"readme.md"),"r", encoding="utf-8").read())[0]

class Link(object):
    def __init__(self, path, cfgpath, relycfgpath, prefix_cid="prefix_cid", defaultMode=999):
        self.path = path
        self.cfgpath = cfgpath
        self.confg = json.load(open(cfgpath, "r", encoding="utf-8"))
        self.relycfg = json.load(open(relycfgpath, "r", encoding="utf-8"))
        self.tag=""
        if defaultMode == 999:
            self.mode = self.confg["linkMode"]
        else:
            self.mode = defaultMode

        self.prefix = self.confg["cidPrefix"]
        self.fieldPosi = self.confg["appendNoteFieldPosition"]
        self.mapFuncPath = [
            self.completemap,  # mode0
            self.groupBygroup,  # mode1
            self.unlinkNode,  # mode2
            self.unlinkPath,#mode3
        ]
        if self.prefix != self.relycfg[prefix_cid]:
            self.relycfg[prefix_cid] = self.prefix
            json.dump(self.relycfg, open(relycfgpath, "w", encoding="utf-8"))
        self.fdata = {"IdDescPairs":[],"IdDescGroups":[]}
        '''fdata 并不存储原始的json数据,他用来去重,再分装到group和pair,这是对旧函数的兼容'''
        fdata=json.load(open(os.path.join(THIS_FOLDER, inputFileName), "r", encoding="utf-8"))
        same=[]
        for pl in fdata["IdDescPairs"]:
            for p in pl:
                if p["card_id"] in same:
                    continue
                else:
                    same.append(p["card_id"])
                    self.fdata["IdDescPairs"].append(p)
            self.fdata["IdDescGroups"].append(pl)
        self.fdata["addTag"]=fdata["addTag"]

    def start(self):
        if len(self.fdata["IdDescPairs"]) == 0 and len(self.fdata["IdDescGroups"]) == 0:
            showInfo("input.json文件中没有数据！")
            return
        tooltip(f"{consolerName}:mode:" + str(int(self.mode)) + ",链接开始")
        self.mapFuncPath[self.mode]()
        if self.confg["addTagEnable"]==1:
            if self.mode<=2:self.appendTagForAllNote()
        tooltip(f"{consolerName}:链接结束!")
        return self.tag

    # 下面的是工具
    def getCardNoteFromId(self, li: int) -> Note:
        return mw.col.getCard(li).note()

    def appendTagForAllNote(self)-> None:
        """加tag,默认加时间戳,有空自己去改"""
        tagbase = self.confg["addTagRoot"]+"::"
        tagtail = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        cidli = self.fdata["IdDescPairs"]
        if self.fdata["addTag"]!="":
            tagtail=self.fdata["addTag"]
        tag=tagbase+tagtail
        for cidpair in cidli:
            note=self.getCardNoteFromId(cidpair["card_id"])
            note.addTag(tag)
            note.flush()
        self.tag=tag

    def appendIDtoNote(self, note, IdDescPair, dir : str = "→"):
        '''
        note必须是一个cardnote,posi是一个cardnote的位置,Id_DescribePair是卡号、描述的键值对
        '''
        if dir == '→':
            direction=self.confg["linkToSymbol"]
        if dir == '←':
            direction=self.confg["linkFromSymbol"]
        style=self.confg["linkStyle"]
        Id = IdDescPair["card_id"]
        descstr = self.getCardNoteFromId(IdDescPair["card_id"]).fields[self.confg["readDescFieldPosition"]]#这里做了重复操作.和multicopy时的功能一样
        seRegx = self.confg["DEFAULT"]["regexForDescContent"] if self.confg["regexForDescContent"] == 0 else self.confg[
            "regexForDescContent"]
        try:
            Desc = IdDescPair["desc"] if len(IdDescPair["desc"]) >= 1 else re.search(seRegx, descstr)[0]
        except:
            showInfo(f"{consolerName}:正则读取描述字符失败!请检查读取的字段是否为空字段,或请检查正则表达式是否有效")
            return
        note.fields[self.fieldPosi] += f"<div card_id='{Id}' dir = '{dir}' style='{style}'>{direction}{Desc} {self.prefix}{Id}</div>\n"
        note.flush()

    def getCardIDfromNote(self, id : int) -> list:
        note = self.getCardNoteFromId(id)
        content = note.fields[self.fieldPosi]
        return re.findall(f"(?<={self.prefix})" + r"\d{13}", content)

    # 下面的是链接算法
    def AmapB(self, groupA, groupB):
        '''
        A位置的所有ID插入到B中,并作一个B的反向链接回A.
        json格式必须是AmapB起头,然后A位置输完要给一个换行符
        这个以后要大改.改好了
        '''
        fieldPosi = self.fieldPosi
        for idpA in groupA:
            Anote = self.getCardNoteFromId(idpA["card_id"])
            for idpB in groupB:
                Bnote = self.getCardNoteFromId(idpB["card_id"])
                if re.search(str(idpB["card_id"]), Anote.fields[fieldPosi]) is None:
                    self.appendIDtoNote(Anote, idpB)
                if re.search(str(idpA["card_id"]), Bnote.fields[fieldPosi]) is None:
                    self.appendIDtoNote(Bnote, idpA, dir="←")

    def completemap(self):
        '''
        完全图,没什么说的
        '''
        cidli = self.fdata["IdDescPairs"]
        fieldPosi = self.fieldPosi
        for cidP in cidli:
            if cidP["card_id"] == 0:
                continue
            # 笔记是一个对象
            note = self.getCardNoteFromId(cidP["card_id"])
            for linkcid in cidli:
                # 怎样才能访问到fields,需要用数字下标,访问到的是HTML模式
                IdA = cidP["card_id"]
                IdB = linkcid["card_id"]
                if IdA != IdB and (re.search(str(IdB), note.fields[fieldPosi]) is None):
                    self.appendIDtoNote(note, linkcid)
        tooltip(f"{consolerName}:已按完全图完成链接")

    def groupBygroup(self):
        '''
        将其首尾分段相连A-B-C
        '''
        cidli = self.fdata["IdDescGroups"]
        placeholder = {"card_id": 0, "desc": ""}
        if len(cidli) < 2:
            showInfo("链接失败,组连接至少需要两个组!")
            return
        else:  # 说明groupSeperIdx 至少2个
            for i in range(0, len(cidli) - 1):  # 0,1,2起步
                liA = cidli[i]
                liB = cidli[i + 1]
                self.AmapB(liA, liB)
        tooltip(f"{consolerName}:已按组完成链接")

    def unlinkNode(self):
        idpli = self.fdata["IdDescPairs"]
        for idp in idpli:
            id = str(idp["card_id"])
            linkli = self.getCardIDfromNote(int(id))

            for link in linkli:

                note = self.getCardNoteFromId(int(link))  # 链到的卡片上找自己

                content = re.sub(f'''<div card_id=["']{id}["'][\\s\\S]+?{id}</div>''', "", note.fields[self.fieldPosi])
                note.fields[self.fieldPosi] = content
                note.flush()
                note = self.getCardNoteFromId(idp["card_id"])
                #<div card_id="1578352706361" dir="→" style=""><br></div>
                content = re.sub(f'''<div card_id=["']{link}["'][\\s\\S]+?{link}</div>''', "",
                                 note.fields[self.fieldPosi])

                note.fields[self.fieldPosi] = content
                note.flush()
        tooltip(f"{consolerName}:已按节点取消彼此链接")

    def unlinkPath(self):
        idpli = self.fdata["IdDescPairs"]
        for i in range(0, len(idpli) - 1):
            idA = idpli[i]["card_id"]
            idB = idpli[i + 1]["card_id"]
            noteA = self.getCardNoteFromId(idA)
            noteB = self.getCardNoteFromId(idB)
            content = re.sub(f'''<div card_id=["']{str(idA)}["'][\\s\\S]+?{str(idA)}</div>''', "",
                             noteB.fields[self.fieldPosi])
            noteB.fields[self.fieldPosi] = content
            noteB.flush()
            content = re.sub(f'''<div card_id=["']{str(idB)}["'][\\s\\S]+?{str(idB)}</div>''', "",
                             noteA.fields[self.fieldPosi])
            noteA.fields[self.fieldPosi] = content
            noteA.flush()
        tooltip(f"{consolerName}:已按路径取消路径节点上的彼此链接")


def setupFunction(browser:Browser,mode=999):
    input = os.path.join(THIS_FOLDER, inputFileName)
    cfg = os.path.join(THIS_FOLDER, configFileName)
    relycfg = os.path.join(RELY_FOLDER, relyLinkConfigFileName)
    browser.model.search("1 -1")
    browser.close()
    Linker = Link(input, cfg, relycfg, defaultMode=mode)
    tag=Linker.start()
    showInfo("")
    tooltip(f"{consolerName}:链接工作结束,浏览界面重新启动,tag={tag}")
    mw.onBrowse()


def destroyFuntion():
    fdata = open(os.path.join(THIS_FOLDER, inputFileName), "w", encoding="utf-8")
    fdata.write(inputSchema)
    fdata.close()
    tooltip(f"{consolerName}:{inputFileName} 文件初始化完毕")


def getCardDesc(card_id:int,confg:object)->str:
    """根据预设参数读取卡片的内容作为链接的描述字符串,如果读取失败,返回 读取描述字符失败"""
    note = mw.col.getCard(card_id).note()
    content = note.fields[confg["readDescFieldPosition"]]
    seRegx = confg["DEFAULT"]["regexForDescContent"] if confg["regexForDescContent"] == 0 else confg[
        "regexForDescContent"]
    try:
        Desc = re.search(seRegx, content)[0]#if desc == "" else desc  # 综上读取描述文字
    except:
        showInfo(f"{consolerName}:正则读取描述字符失败!请检查读取的字段是否为空字段,或请检查正则表达式是否有效")
        return "读取描述字符失败"
    return Desc[0:confg['descMaxLength'] if len(Desc)>confg['descMaxLength'] and confg['descMaxLength']!=0  else len(Desc)]

#multicopyFunction 和  singlecopyFunction 代码高度重叠,以后要统一 TODO
def multicopyFunction(self, groupCopy :bool = False,desc : str ="",clearInput :bool = False) -> None:
    if clearInput: destroyFuntion()
    cfgpath = os.path.join(THIS_FOLDER, configFileName)
    confg = json.load(open(cfgpath, "r", encoding="utf-8"))
    s = json.load(open(os.path.join(THIS_FOLDER, inputFileName), "r", encoding="utf-8"))
    group = []
    browser = self
    if len(browser.selectedCards()) == 0:
        showInfo("没有选中任何卡片!")
        return
    for card_id in browser.selectedCards():
        pair = {"card_id": card_id, "desc": getCardDesc(card_id,confg) }
        if groupCopy:
            group.append(pair)
        else:
            s["IdDescPairs"].append([pair])
    if len(group) > 0:
        s["IdDescPairs"].append(group)
    json.dump(s, open(os.path.join(THIS_FOLDER, inputFileName), "w", encoding="utf-8"), indent=4, ensure_ascii=False)
    tooltip(f"{consolerName}:"+str(len(browser.selectedCards())) + " 张卡被加入到input.json文件中")


def singlecopyFunction(card_id : int,groupCopy :bool = False,desc : str = "",clearInput : bool = False) -> None:
    if clearInput:destroyFuntion()
    cfgpath = os.path.join(THIS_FOLDER, configFileName)
    confg = json.load(open(cfgpath, "r", encoding="utf-8"))
    s = json.load(open(os.path.join(THIS_FOLDER, inputFileName), "r", encoding="utf-8"))
    desc=desc if desc !="" else getCardDesc(card_id,confg)
    pair = {"card_id": card_id, "desc":desc}
    tooltip(f"{consolerName}:card=" + str(card_id) + ",desc=" + desc)
    if groupCopy:
        try:
            s["IdDescPairs"][-1].append(pair)
        except:
            s["IdDescPairs"].append([pair])
        tooltip(f"{consolerName}: {json.dumps(pair, ensure_ascii=False)} 已经被插入到上一个组")
    else:
        s["IdDescPairs"].append([pair])
        tooltip(f"{consolerName}:"+json.dumps(pair, ensure_ascii=False) + " 已经被插入到input.json文件")
    json.dump(s, open(os.path.join(THIS_FOLDER, inputFileName), "w", encoding="utf-8"), indent=4, ensure_ascii=False)


def copyTagFromSelected(tag):
    s = json.load(open(os.path.join(THIS_FOLDER, inputFileName), "r", encoding="utf-8"))
    s["addTag"]=tag
    tooltip(f"{consolerName}:标签"+ "{"+f'"tag":"{tag}"' + "} 已经更新到input.json文件")
    json.dump(s, open(os.path.join(THIS_FOLDER, inputFileName), "w", encoding="utf-8"), indent=4, ensure_ascii=False)


def displayFunction():
    Url = QUrl.fromLocalFile("" + os.path.join(THIS_FOLDER, inputFileName))
    QDesktopServices.openUrl(Url)


def configFunction():
    Url = QUrl.fromLocalFile("" + os.path.join(THIS_FOLDER, configFileName))
    QDesktopServices.openUrl(Url)


def helpFunction():
    Url = QUrl(helpSite)
    QDesktopServices.openUrl(Url)

def testFunction(browser: Browser):
    browser.model.search("1 -1")
    browser.editor.setNote(None)
def versionFunction():
    showInfo(hjp_bilink_VERSION)

def setUpBrowserMenuShortcut(browser):
    # 将参数命名为browser
    # browser = self
    '''
    #如果browser存在,直接让m读取menulinking属性,如果不存在,我们就自己创建一个
    函数用的是QMenu
    然后访问menubar也就是菜单栏,插入一个菜单.方法是insertmenu,参数是self.mw.form.menuTools.menuAction表示表单动作,
    menulinking就是刚建立的表单按钮,也就是Qmenu.
    '''
    try:
        m = browser.hjp_Link
    except:
        browser.hjp_Link = QMenu("hjp_link")
        browser.menuBar().insertMenu(browser.mw.form.menuTools.menuAction(), browser.hjp_Link)
        m = browser.hjp_Link
    m.addAction('默认连接').triggered.connect(lambda _: setupFunction(browser,mode=999))
    m.addAction('完全图连接').triggered.connect(lambda _: setupFunction(browser,mode=0))
    m.addAction('组到组连接').triggered.connect(lambda _: setupFunction(browser,mode=1))
    m.addAction('按结点取消连接').triggered.connect(lambda _: setupFunction(browser,mode=2))
    m.addAction('按路径取消连接').triggered.connect(lambda _: setupFunction(browser,mode=3))
    m.addAction('初始化input').triggered.connect(destroyFuntion)
    m.addAction('显示input').triggered.connect(displayFunction)
    m.addAction('调整config').triggered.connect(configFunction)
    m.addAction("查看版本").triggered.connect(versionFunction)
    m.addAction('打开插件页面').triggered.connect(helpFunction)
   # m.addAction("test").triggered.connect(lambda _: testFunction(browser))


def AddToTableContextMenu(browser, menu):
    actionCopyCidAllWithClear = QAction("hjp|先清除input再将选中卡片插入",browser)
    actionCopyCidAllWithClear.triggered.connect(lambda _, b=browser: multicopyFunction(b,clearInput=True))
    menu.addAction(actionCopyCidAllWithClear)
    actionCopyCidAll = QAction("hjp|将选中的卡片插入input", browser)
    actionCopyCidAll.triggered.connect(lambda _, b=browser: multicopyFunction(b))
    menu.addAction(actionCopyCidAll)
    actionGroupCopy = QAction("hjp|将选中的卡片编组插入input", browser)
    actionGroupCopy.triggered.connect(lambda _, b=browser: multicopyFunction(b, groupCopy=True))
    menu.addAction(actionGroupCopy)
# def testfunction(card):
#     tooltip("hello"+str(card.id))

def AddToEditorContextMenu(view,menu):
    editor=view.editor
    try:
        card_id=editor.card.id
        #tooltip(f"cardid={str(card_id)}")
    except:
        tooltip(f"{consolerName}:由于这里无法读取card_id,链接菜单不在这显示")
        return
    selected=editor.web.selectedText()
    singlecopyWithClear = menu.addAction("hjp|先清除input再将卡片插入")
    singlecopyWithClear.triggered.connect(lambda _:singlecopyFunction(card_id,selected,clearInput=True))
    singlecopy= menu.addAction("hjp|将卡片插入input")
    singlecopy.triggered.connect(lambda _:singlecopyFunction(card_id,selected))
    groupcopy = menu.addAction("hjp|将卡片插入上一个组")
    groupcopy.triggered.connect(lambda _:singlecopyFunction(card_id,selected,groupCopy=True))
    tagcopy = menu.addAction('hjp|用选中文字更新input中的标签')
    tagcopy.triggered.connect(lambda _:copyTagFromSelected(selected))

gui_hooks.browser_menus_did_init.append(setUpBrowserMenuShortcut)
gui_hooks.browser_will_show_context_menu.append(AddToTableContextMenu)
gui_hooks.profile_will_close.append(destroyFuntion)
gui_hooks.editor_will_show_context_menu.append(AddToEditorContextMenu)
#gui_hooks.reviewer_will_show_context_menu.append(testReviewer)
#gui_hooks.reviewer_did_show_question.append(testfunction)
#gui_hooks.reviewer_will_show_context_menu
#linkActToMainMenu()
