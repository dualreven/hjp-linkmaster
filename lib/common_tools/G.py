# -*- coding: utf-8 -*-
"""
__project_ = 'hjp-bilink'
__file_name__ = 'G.py'
__author__ = '十五'
__email__ = '564298339@qq.com'
__time__ = '2021/7/30 9:47'
G.py 就是GLOBAL.py, 存放一些持续不变的常量
"""
from typing import *
from anki.scheduler.v3 import QueuedCards
from . import signals, src_admin, objs, widgets, language
# from .src_admin import SrcAdmin
# from .signals import CustomSignals
# from .objs import DB_admin

from typing import TYPE_CHECKING
from .compatible_import import *
import os


class 插件全局变量(TypedDict):
    复习队列: "Optional[QueuedCards]"

class installAs:
    local = 0
    ankiweb = 1


if TYPE_CHECKING:
    from .configsModel import GroupReviewDictInterface, ConfigModel


class MW: pass


isQt6 = Anki.isQt6

if mw is None:
    mw = MW()


class SAFE:
    @property
    def funcs(self):
        from . import funcs
        return funcs
    @property
    def graphical_bilinker(self):
        from . import graphical_bilinker
        return graphical_bilinker
    @property
    def linkdata_grapher(self):
        from ..bilink.dialogs import linkdata_grapher
        return linkdata_grapher
    @property
    def bilinkDialogs(self):
        from ..bilink import dialogs
        return dialogs

    @property
    def linkdata_admin(self):
        from ..bilink import linkdata_admin
        return linkdata_admin

    @property
    def in_text_admin(self):
        from ..bilink import in_text_admin
        return in_text_admin
    @property
    def objs(self):
        from .import objs
        return objs
    @property
    def models(self):
        from . import models
        return models

    @property
    def hookers(self):
        from .import hookers
        return hookers
    @property
    def widgets(self):
        from .import widgets
        return widgets
    @property
    def funcs2(self):
        from . import funcs2
        return funcs2
    @property
    def configsModel(self):
        from . import configsModel
        return configsModel

    @property
    def baseClass(self):
        from . import baseClass
        return baseClass



safe = SAFE()

QTMAXINT = 2147483647
QTMININT = -2147483647

addonId = 1420819673
say = language.rosetta
ISDEBUG = ISDEBUG

DB = objs.DB_admin()  # 这个是通用DB,如果要用linkdata请用linkdata_admin里的DB
signals = signals.CustomSignals.start()
src = src_admin.src
addonName = src.dialog_name
CONFIG: "Optional[ConfigModel]" = None
# hjp-todo 把插件全局变量建设好
mw.__dict__[addonName]:插件全局变量 = {}
mw.__dict__[addonName]["复习队列"] = None
mw.__dict__[addonName]["progresser"] = None
mw.__dict__[addonName]["card_window"] = {}
mw.__dict__[addonName]["clipper"] = {}
mw.__dict__[addonName]["pdf_prev"] = {}  #
mw.__dict__[addonName]["anchor_window"] = {}
mw.__dict__[addonName]["input_window"] = None
mw.__dict__[addonName]["VersionDialog"] = None
mw.__dict__[addonName]["grapher"] = None
# w.__dict__[addonName][""]:None=None
mw_addonName = mw.__dict__[addonName]
mw_current_card_id = None
mw_card_window: "dict" = mw_addonName["card_window"]  # anchor第一个链接出来的窗口
mw_win_clipper = None
mw_pdf_prev = mw_addonName["pdf_prev"]  # mw_pdf_prev[pdfname][pdfpagenum]
mw_anchor_window = mw_addonName["anchor_window"]  # anchor本身的窗口
mw_linkpool_window = mw_addonName["input_window"]  # input窗口
mw_VersionDialog = mw_addonName["VersionDialog"]
mw_progresser = mw.__dict__[addonName]["progresser"]
mw_universal_worker = None
mw_grapher = mw.__dict__[addonName]["grapher"]  # grapher是临时视图, 也叫链接池视图
mw_gview = {}  # 当前运行的视图存放所在地
GViewAdmin_window = None
GViewAutoShow_window = None
mw_addcard_to_grapher_on = False
browser_addon_menu = None
# GroupReview_dict: "Optional[GroupReviewDictInterface]" = None  # 卡片ID映射到searchString
# GroupReview_tempfile: "set" = set()  # 只保存卡片id
# GroupReview_timer = QTimer()
# GroupReview_version: "float" = 0
nextCard_interval: "list[int]" = []  # 用来记录连续过快复习
cardChangedTime = -1
customPreviewerBothSide = False
常量_当前等待新增卡片的视图索引: "None|str" = None
