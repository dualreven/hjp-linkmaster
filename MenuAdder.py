"""
专门用来加按钮的文件
prefix 必须由consolerName规定
"""
from aqt import gui_hooks

from .mainfunctions import *
from .utils import *


def actionMenuConnector(menu, actionname, action, **kwargs):
    """执行动作链接的一个辅助函数"""
    menu.addAction(actionname).triggered.connect(lambda: action(**kwargs))


@debugWatcher
def func_menuAddBrowserInsert(*args, **kwargs):
    """browser插入类函数集合"""
    param = Params(**kwargs)
    prefix = "" if "prefix" not in param.features else consolerName
    menuNameLi = list(map(lambda x: prefix + say(x), ["清除后选中卡片插入", "将选中卡片插入", "将选中卡片编组插入"]))
    featureli = ["clear", "", "group"]
    if "prefix" in param.features:
        linkmenu = param.menu
    else:
        linkmenu = param.menu.addMenu(say("插入"))
    list(map(lambda i:
             actionMenuConnector(linkmenu, menuNameLi[i], func_browserInsert, parent=param.parent,
                                 features=[featureli[i]])
             , range(len(featureli))))


def func_menuAddSingleInsert(*args, **kwargs):
    """用来添加常规插入按钮组"""
    param = Params(**kwargs)
    actionNameLi = list(map(lambda x: say(x), ["先清除再插入", "直接插入", "插入上一个组", "选中文字更新标签"]))
    featureli = ["clear", "", "last", "tag"]
    prefix = "" if "prefix" not in param.features else consolerName
    papamenu = param.menu.addMenu(prefix + say("插入"))
    list(map(lambda i: actionMenuConnector(papamenu, actionNameLi[i], func_singleInsert, pair=param.pair,
                                           features=[featureli[i]]), range(len(featureli))))


def func_menuAddLink(*args, **kwargs):
    """用来给链接类型的函数加按钮"""
    param = Params(**kwargs)
    menuNameLi = list(map(lambda x: say(x), ["默认链接", "完全图链接", "组到组链接", "按结点取消链接", "按路径取消链接"]))
    prefix = "" if "prefix" not in param.features else consolerName
    linkname = "链接"
    if "selected" in param.features:
        linkname = "选中链接"
    linkmenu = param.menu.addMenu(prefix + say(linkname))
    modeLi = [999, 0, 1, 2, 3]
    list(map(
        lambda x, y: linkmenu.addAction(x).triggered.connect(
            lambda: func_linkStarter(mode=y, parent=param.parent, input=Input(), features=param.features)),
        menuNameLi, modeLi))


def func_menuAddClearOpen(*args, **kwargs):
    """用来给清除和打开input功能加按钮"""
    param = Params(**kwargs)
    prefix = "" if "prefix" not in param.features else consolerName
    menuli = ["打开input", "清空input"]
    funcli = [func_openInput, func_clearInput]
    list(map(lambda x, y: param.menu.addAction(f"{prefix}{say(x)}").triggered.connect(y), menuli, funcli))


def func_menuAddBaseMenu(*args, **kwargs):
    """基础的如,help,config,version"""
    param = Params(**kwargs)
    menuli = ["调整config", "查看版本和新特性", "打开插件页面", "升级旧版锚点", "联系作者", "支持作者"]
    funcli = [func_config, func_version, func_help, func_anchorUpdate, func_contactMe, func_supportMe]
    menu = param.menu.addMenu(say("其他"))
    list(map(lambda x, y: menu.addAction(f"{say(x)}").triggered.connect(y), menuli, funcli))


@debugWatcher
def func_menuAddHelper(*args, **kwargs):
    """提供大部分类似的按钮添加操作帮助"""
    param = Params(**kwargs)
    for action in param.actionTypes:
        func_menuAdderLi[action](**kwargs)


def func_add_browsermenu(browser: Browser = None):
    """给browser的bar添加按钮"""
    if hasattr(browser, "hjp_link"):
        menu: QMenu = browser.hjp_Link
    else:
        menu = browser.hjp_Link = QMenu("hjp_link")
        browser.menuBar().addMenu(browser.hjp_Link)
    '''
    链接:5个,插入:3个,打开,清空,配置,版本,帮助
    '''
    func_menuAddHelper(menu=menu, parent=browser, actionTypes=["link", "browserinsert", "clear_open", "basicMenu"])


@debugWatcher
def fun_add_browsercontextmenu(browser: Browser, menu: QMenu):
    """用来给browser加上下文菜单"""
    func_menuAddHelper(menu=menu, parent=browser, features=["prefix"], actionTypes=["browserinsert"])


def func_add_editorcontextmenu(view: AnkiWebView, menu: QMenu):
    """用来给editor界面加上下文菜单"""
    editor = view.editor
    selected = editor.web.selectedText()
    try:
        card_id = editor.card.id
    except:
        console(say("由于这里无法读取card_id, 链接菜单不在这显示")).talk.end()
        return

    func_menuAddHelper(menu=menu, parent=view, pair=Pair(card_id=str(card_id), desc=selected),
                       features=["prefix"], actionTypes=["insert", "clear_open", ])


def func_add_webviewcontextmenu(view: AnkiWebView, menu: QMenu):
    """正如其名,给webview加右键菜单"""
    selected = view.page().selectedText()
    cid = "0"
    if view.title == "main webview" and mw.state == "review":
        cid = mw.reviewer.card.id
    elif view.title == "previewer" and view.parent() is not None and view.parent().card() is not None:
        cid = view.parent().card().id
    if cid != "0":
        func_menuAddHelper(pair=Pair(desc=selected, card_id=str(cid)), features=["prefix"],
                           parent=view, menu=menu, actionTypes=["link", "insert", "clear_open"])


func_menuAdderLi = {
    "link": func_menuAddLink,
    "browserinsert": func_menuAddBrowserInsert,
    "clear_open": func_menuAddClearOpen,
    "basicMenu": func_menuAddBaseMenu,
    "insert": func_menuAddSingleInsert
}

gui_hooks.browser_menus_did_init.append(func_add_browsermenu)
gui_hooks.browser_will_show_context_menu.append(fun_add_browsercontextmenu)
gui_hooks.profile_will_close.append(func_onProgramClose)
gui_hooks.editor_will_show_context_menu.append(func_add_editorcontextmenu)
gui_hooks.webview_will_show_context_menu.append(func_add_webviewcontextmenu)
