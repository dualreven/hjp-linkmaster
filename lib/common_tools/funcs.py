# -*- coding: utf-8 -*-
"""
__project_ = 'hjp-bilink'
__file_name__ = '$NAME.py'
__author__ = '十五'
__email__ = '564298339@qq.com'
__time__ = '2021/7/30 9:09'
"""
import dataclasses
import logging
import sys, platform, subprocess
import tempfile
from urllib.parse import quote

import uuid
from collections import Sequence
from datetime import datetime
import time
from math import ceil
from typing import Union, Optional, NewType, Callable, List

from PyQt5.QtCore import pyqtSignal, QThread, QUrl, QTimer, Qt, QSettings, QMimeData
import json
import os
import re
from functools import reduce

from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QApplication, QToolButton
from anki import stdmodels, notes
from anki.cards import Card
from anki.notes import Note
from anki.utils import pointVersion, isWin
from aqt import mw, dialogs, AnkiQt
from aqt.browser import Browser
from aqt.browser.previewer import BrowserPreviewer, Previewer
from aqt.operations.card import set_card_deck
from aqt.reviewer import Reviewer, RefreshNeeded
from aqt.utils import showInfo, tooltip, tr
from aqt.webview import AnkiWebView
from bs4 import BeautifulSoup, element
from . import G, compatible_import
from .language import Translate
from .objs import LinkDataPair, LinkDataJSONInfo
from ..bilink.dialogs.custom_cardwindow import SingleCardPreviewerMod
from .interfaces import ConfigInterface, AnswerInfoInterface, AutoReviewDictInterface, GViewData, GraphMode


class GviewOperation:

    @staticmethod
    def save(data:GViewData):
        """"""
        DB=G.DB
        DB.go(DB.table_Gview)
        if DB.exists(DB.EQ(uuid=data.uuid)):
            DB.end()
            GviewOperation.update(data)
        else:
            DB.insert(**(data.to_DB_format())).commit()
            DB.end()
        tooltip("保存成功")

    @staticmethod
    def load(uuid=None,gviewdata:"GViewData"=None,pairli=None):
        """"""
        if uuid is not None:
            DB=G.DB
            DB.go(DB.table_Gview)
            data = DB.select(DB.EQ(uuid=uuid)).return_all().zip_up().to_gview_data()[0]
            return data

    @staticmethod
    def find_by_card(pairli:'list[LinkDataPair]')->'set[GViewData]':
        """找到卡片所属的gview记录 """
        DB = G.DB
        DB.go(DB.table_Gview)

        def pair_to_gview(pair):
            card_id = pair.card_id
            datas = DB.select(DB.LIKE("nodes", f"%\"{card_id}\"%")).return_all().zip_up().to_gview_data()
            return set(map(
                lambda data:GViewData(
                    uuid=data.uuid,name=data.name,nodes=json.loads(data.nodes),edges=json.loads(data.edges)) ,datas))
        all_records = list(map(lambda x: pair_to_gview(x),pairli))
        final_givew = reduce(lambda x,y:x&y,all_records) if len(all_records)>0 else set()
        DB.end()
        return final_givew
        # for pair in pairli:
        #     card_id = pair.card_id
        #     datas = DB.select(DB.LIKE("nodes",f"%\"{card_id}\"%")).return_all().zip_up().to_gview_data()
        #     for data in datas:
        #         data = GViewData(uuid=data.uuid,name=data.name,nodes=json.loads(data.nodes),edges=json.loads(data.edges))
        #         if start==0:
        #             record.add(data)
        #         else:
        #             record&=data
        #     start+=1

        # tooltip("<br>".join([ r.to_html_repr() for r in record]))
        # return record

    @staticmethod
    def update(data:GViewData):
        """"""
        DB = G.DB
        DB.go(DB.table_Gview)
        d = data.to_DB_format()
        d.pop("uuid")
        DB.update(values=DB.VALUEEQ(**d),where=DB.EQ(uuid=data.uuid)).commit(write_to_log_file)
            # name=d["name"],nodes=d["nodes"],edges=d["edges"]
        DB.end()

    @staticmethod
    def delete(uuid:str):
        """"""
        DB = G.DB
        DB.go(DB.table_Gview)
        DB.delete(values=DB.VALUEEQ(uuid=uuid)).commit()


class Utils(object):
    @staticmethod
    def percent_calc(total,count,begin,ratio):
        return ceil(count/total*ratio)+begin

    @staticmethod
    def emptystr(s):
        return re.search(r"\S",s)

    @staticmethod
    def tooltip(s):
        if G.ISDEBUG:
            tooltip(s)


class AutoReview(object):
    """这是一套性能优化方案, AutoReview由于每次回答都要去数据库查询一遍,因此我们想了一招来更新缓存
    1,监听卡片的变化,
    """

    @staticmethod
    def begin():
        """入口,要从配置读东西,保存到某地,现在看来保存到G是最合适的,还需要设计数据结构"""
        if Config.get().auto_review.value==0:
            return
        AutoReview.build()
        G.AutoReview_timer.timeout.connect(AutoReview.update)
        G.AutoReview_timer.start(G.src.autoreview_update_interval)

    @staticmethod
    def build():
        G.AutoReview_dict = AutoReviewDictInterface()
        searchs:"list[str]" = Config.get().auto_review_search_string.value
        for search in searchs:
            if search == "" or not re.search(r"\S",search):
                continue
            cids = mw.col.find_cards(search)
            list(map(lambda cid: G.AutoReview_dict.card_group_insert(cid, search), cids))
            list(map(lambda cid: G.AutoReview_dict.search_group_insert(cid, search), cids))
        G.AutoReview_dict.build_union_search()

    @staticmethod
    def update():
        """从配置表加载查询条件,然后去搜索,组织,并更新到数据库
        这个函数需要定期执行,要给一些优化,
        这里是重点对象, 首先执行一次联合查询, 然后检查原本在的是否消失, 原本不在的是否新增
        https://blog.csdn.net/qq_34130509/article/details/89473503
        """
        if Config.get().auto_review.value==0:
            return
        def search_result_not_changed():
            """在这里,我们检查有没有必要更新"""
            new_cids = set(mw.col.find_cards(G.AutoReview_dict.union_search))
            old_cids = G.AutoReview_dict.card_group.keys()
            need_add_card = new_cids - old_cids
            need_del_card = old_cids - new_cids
            return len(need_add_card)==0 and len(need_del_card)==0
        #临时文件没有变化则退出
        if len(G.AutoReview_tempfile) == 0:
            return
        #临时文件有变化,且临时文件cid不属于集合,则检查原集合是否有改动,无改动则退出
        not_belong_to_card_group = len(G.AutoReview_tempfile & G.AutoReview_dict.card_group.keys())==0
        if not_belong_to_card_group and search_result_not_changed():
            G.AutoReview_tempfile.clear()
            return
        #其他的筛选条件太难选了.到这里就直接建立吧
        AutoReview.build()
        G.AutoReview_tempfile.clear()

    @staticmethod
    def modified_card_record(note:Note):
        """将卡片写到一个全局变量,作为集合"""
        if Config.get().auto_review.value==0:
            return
        G.AutoReview_tempfile|=set(note.card_ids())


    @staticmethod
    def save_search_to_config(browser:Browser):
        """把搜索栏的内容拷贝下来粘贴到配置表"""
        c=Config.get()

        curr_string = browser.form.searchEdit.currentText()
        if curr_string=="" or not re.search(r"\S",curr_string):
            tooltip("不接受空格与空值<br>null string or empty string is not allowed")
            return
        setv = set(c.auto_review_search_string.value)
        setv.add(curr_string)
        c.auto_review_search_string.value = list(setv)
        c.save_to_file(G.src.path.userconfig)



class HTMLOperation:

    pass


class Config:

    @staticmethod
    def get() -> ConfigInterface:
        """静态方法,直接调用即可"""
        try:
            cfg = ConfigInterface.json_load(G.src.path.userconfig)
            cfg.save_to_file(G.src.path.userconfig)
            return cfg
        except:
            tooltip("配置文件格式不符合,现已覆盖\n"
                    "format of config file is not correct, now the file has been overwritten")
            template = ConfigInterface()
            Config.save(template)
            return template

    @staticmethod
    def save(config: ConfigInterface=None):
        if config is None:
            config = ConfigInterface()
        config.save_to_file(G.src.path.userconfig)


class GrapherOperation:
    @staticmethod
    def refresh():
        from ..bilink.dialogs.linkdata_grapher import Grapher
        if isinstance(G.mw_grapher, Grapher):
            G.mw_grapher.on_card_updated.emit(None)


class LinkDataOperation:
    """针对链接数据库的操作,
    这里的LinkDataOperation.bind/unbind和LinkPoolOperation中的link/unlink是类似但不同,不冲突.
    因为那是一个link池里的操作,而这不是, 这是一个普通的链接操作
    """
    @staticmethod
    def read(card_id):
        from ..bilink.linkdata_admin import read_card_link_info
        return read_card_link_info(card_id)

    @staticmethod
    def write(card_id, data):
        from ..bilink.linkdata_admin import write_card_link_info
        return write_card_link_info(card_id, data)

    @staticmethod
    def bind(card_idA:'Union[str,LinkDataJSONInfo]', card_idB:'Union[str,LinkDataJSONInfo]', needsave=True):
        """needsave关闭后,需要自己进行save"""
        if isinstance(card_idA,LinkDataJSONInfo) and isinstance(card_idB,LinkDataJSONInfo):
            cardA,cardB = card_idA,card_idB
        else:
            from ..bilink import linkdata_admin
            cardA = linkdata_admin.read_card_link_info(card_idA)
            cardB = linkdata_admin.read_card_link_info(card_idB)
        if cardB.self_data not in cardA.link_list:
            cardA.append_link(cardB.self_data)
            if needsave: cardA.save_to_DB()
        if cardA.self_data not in cardB.link_list:
            cardB.append_link(cardA.self_data)
            if needsave: cardB.save_to_DB()

    @staticmethod
    def unbind(card_idA:'Union[str,LinkDataJSONInfo]', card_idB:'Union[str,LinkDataJSONInfo]', needsave=True):
        """needsave关闭后,需要自己进行save"""
        if isinstance(card_idA,LinkDataJSONInfo) and isinstance(card_idB,LinkDataJSONInfo):
            cardA,cardB = card_idA,card_idB
        else:
            from ..bilink import linkdata_admin
            cardA = linkdata_admin.read_card_link_info(card_idA)
            cardB = linkdata_admin.read_card_link_info(card_idB)
        if cardB.self_data in cardA.link_list:
            cardA.remove_link(cardB.self_data)
            if needsave: cardA.save_to_DB()
        if cardA.self_data in cardB.link_list:
            cardB.remove_link(cardA.self_data)
            if needsave: cardB.save_to_DB()


class Compatible:
    @staticmethod
    def CardId():
        if pointVersion() < 45:
            CardId = NewType("CardId", int)
            return CardId
        else:
            from anki.cards import CardId
            return CardId

    @staticmethod
    def NoteId():
        if pointVersion() < 45:
            NoteId = NewType("NoteId", int)
            return NoteId
        else:
            from anki.notes import NoteId
            return NoteId

    @staticmethod
    def DeckId():
        if pointVersion() < 45:
            DeckId = NewType("DeckId", int)
            return DeckId
        else:
            from anki.decks import DeckId
            return DeckId

    @staticmethod
    def BrowserPreviewer():
        if pointVersion() < 45:
            DeckId = NewType("DeckId", int)
            return DeckId
        else:
            from anki.decks import DeckId
            return DeckId


class BrowserOperation:
    @staticmethod
    def search(s) -> Browser:
        """注意,如果你是自动搜索,需要自己激活窗口"""
        browser: Browser = dialogs._dialogs["Browser"][1]
        # if browser is not None:
        if not isinstance(browser, Browser):
            browser: Browser = dialogs.open("Browser", mw)

        browser.search_for(s)
        return browser

    @staticmethod
    def refresh():
        browser: Browser = dialogs._dialogs["Browser"][1]
        if isinstance(browser, Browser):
            # if dialogs._dialogs["Browser"][1] is not None:
            browser: Browser = dialogs._dialogs["Browser"][1]
            browser.sidebar.refresh()
            browser.model.reset()
            browser.editor.setNote(None)


class CustomProtocol:
    # 自定义url协议,其他的都是固定的,需要获取anki的安装路径

    @staticmethod
    def set():
        root = QSettings("HKEY_CLASSES_ROOT", QSettings.NativeFormat)
        root.beginGroup("ankilink")
        root.setValue("Default", "URL:Ankilink")
        root.setValue("URL Protocol", "")
        root.endGroup()
        command = QSettings(r"HKEY_CLASSES_ROOT\anki.ankiaddon\shell\open\command", QSettings.NativeFormat)
        shell_open_command = QSettings(r"HKEY_CLASSES_ROOT\ankilink\shell\open\command", QSettings.NativeFormat)
        shell_open_command.setValue(r"Default", command.value("Default"))

    @staticmethod
    def exists():
        setting = QSettings(r"HKEY_CLASSES_ROOT\ankilink", QSettings.NativeFormat)
        return len(setting.childGroups()) > 0


class CardOperation:

    @staticmethod
    def auto_review(answer:AnswerInfoInterface):
        """用来同步复习卡片"""

        if Config.get().auto_review.value==0:
            return
        searchs = G.AutoReview_dict.card_group[answer.card_id]

        sched = compatible_import.mw.col.sched
        reportstring = ""
        for search in searchs:
            cids = G.AutoReview_dict.search_group[search]
            for cid in cids:
                card = mw.col.get_card(CardId(cid))
                button_num = sched.answerButtons(card)
                ease = answer.option_num if button_num>=answer.option_num else button_num
                if card.timer_started is None: card.timer_started = time.time() - 60
                CardOperation.answer_card(card,ease)
                reportstring += str(cid) + ":" + CardOperation.desc_extract(cid) + "<br>"
        mw.col.reset()
        reportstring+="以上卡片已经同步复习<br>cards above has beend sync reviewed"
        tooltip(reportstring,period=5000)


    @staticmethod
    def answer_card(card,ease):
        sched = mw.col.sched
        while True:
            try:
                sched.answerCard(card, ease)
                break
            except:
                time.sleep(0.2)
                continue


    @staticmethod
    def create(model_id: "int" = None, deck_id: "int" = None, failed_callback: "Callable" = None):
        if model_id is not None and not (type(model_id)) == int:
            model_id = int(model_id)
        if deck_id is not None and not (type(deck_id)) == int:
            deck_id = int(deck_id)

        if model_id is None:
            if not "Basic" in mw.col.models.allNames():
                # mw.col.models.add(stdmodels.addBasicModel(mw.col))
                material = json.load(open(G.src.path.card_model_template, "r", encoding="utf-8"))
                new_model = mw.col.models.new("Basic")
                new_model["flds"] = material["flds"]
                new_model["tmpls"] = material["tmpls"]
                mw.col.models.add(new_model)
            model = mw.col.models.by_name("Basic")
        else:
            if mw.col.models.have(model_id):
                model = mw.col.models.get(model_id)
            else:
                tooltip(f"modelId don't exist:{model_id}")
                if failed_callback:
                    failed_callback()

        note = notes.Note(mw.col, model=model)
        if deck_id is None:
            deck_id = mw.col.decks.current()["id"]
        else:
            if not mw.col.decks.have(deck_id):
                tooltip(f"deck_id don't exist:{deck_id}")
        mw.col.add_note(note, deck_id=deck_id)
        note.flush()
        return str(note.card_ids()[0])

    @staticmethod
    def clipbox_insert_field(clipuuid, timestamp=None):
        """用于插入clipbox到指定的卡片字段,如果这个字段存在这个clipbox则不做操作"""
        if platform.system() in {"Darwin", "Linux"}:
            tooltip("当前系统暂时不支持该功能\n current os not supports the feature")
            return
        else:
            from ..clipper2.exports import fitz

        def bookmark_to_tag(bookmark: "list[list[int,str,int]]"):
            tag_dict = {}
            if len(bookmark) == 0:
                return tag_dict
            level, content, pagenum = bookmark[0][0], bookmark[0][1], bookmark[0][2]
            tag_dict[pagenum] = re.sub(r"\s|\r|\n", "-", content)
            level_stack = []
            level_stack.append([level, content, pagenum])
            for item in bookmark[1:]:
                level, content, pagenum = item[0], re.sub(r"\s|\r|\n", "-", item[1]), item[2]
                if level == 1:
                    tag_dict[pagenum] = content
                else:
                    while len(level_stack) != 0 and level_stack[-1][0] >= level:
                        level_stack.pop()
                    content = f"{level_stack[-1][1]}::{content}"
                    tag_dict[pagenum] = content
                level_stack.append([level, content, pagenum])
            return tag_dict

        DB = G.DB
        DB.go(DB.table_clipbox)
        clipbox_ = DB.select(uuid=clipuuid).return_all().zip_up()[0]
        clipbox = G.objs.ClipboxRecord(**clipbox_)
        DB.end()
        DB.go(DB.table_pdfinfo)
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        card_id_li = clipbox.card_id.split(",")
        for card_id in card_id_li:
            if not card_id.isdigit():
                continue
            pdfinfo_ = DB.select(uuid=clipbox.pdfuuid).return_all().zip_up()[0]
            pdfinfo = G.objs.PDFinfoRecord(**pdfinfo_)
            pdfname = os.path.basename(pdfinfo.pdf_path)
            pdfname_in_tag = re.sub(r"\s|\r|\n", "-", pdfname[0:-4])
            note = mw.col.getCard(CardId(int(card_id))).note()
            html = reduce(lambda x, y: x + "\n" + y, note.fields)
            if clipbox.uuid not in html:
                note.fields[clipbox.QA] += \
                    f"""<img class="hjp_clipper_clipbox" src="hjp_clipper_{clipbox.uuid}_.png"><br>\n"""
            if clipbox.comment != "" and clipbox.uuid not in html:
                note.fields[clipbox.commentQA] += \
                    f"""<p class="hjp_clipper_clipbox text" id="{clipbox.uuid}">{clipbox.comment}</p>\n"""

            note.addTag(f"""hjp-bilink::timestamp::{timestamp}""")
            # print(f"in the loop, timestamp={timestamp}")
            note.addTag(f"""hjp-bilink::books::{pdfname_in_tag}::page::{clipbox.pagenum}""")
            doc: "fitz.Document" = fitz.open(pdfinfo.pdf_path)
            toc = doc.get_toc()
            if len(toc) > 0:
                # 读取缓存的书签
                jsonfilename = os.path.join(tempfile.gettempdir(),
                                            UUID.by_hash(pdfinfo.pdf_path) + ".json")
                if os.path.exists(jsonfilename):  # 存在直接读
                    bookdict = json.loads(open(jsonfilename, "r", encoding="utf-8").read())
                else:  # 不存在则新建
                    bookdict = bookmark_to_tag(toc)
                    json.dump(bookdict, open(jsonfilename, "w", encoding="utf-8"), indent=4, ensure_ascii=False)
                pagelist = sorted(list(bookdict.keys()), key=lambda x: int(x))  # 根据bookdict的键名(页码)进行排序

                atbookmark = -1
                for idx in range(len(pagelist)):
                    # 这里是在选择card所在的页码插入到合适的标签之间的位置,比如标签A在36页,标签B在38页, card指向37页,那么保存在标签A中.
                    #
                    if int(pagelist[idx]) > clipbox.pagenum:
                        if idx > 0:
                            atbookmark = pagelist[idx - 1]
                        break
                if atbookmark != -1:
                    note.addTag(f"""hjp-bilink::books::{pdfname_in_tag}::bookmark::{bookdict[atbookmark]}""")
            note.flush()
        DB.end()

    @staticmethod
    def refresh():
        def prev_refresh(p: Previewer):
            # return False
            """在被包裹的函数执行完后刷新"""
            _last_state = p._last_state
            _card_changed = p._card_changed
            p._last_state = None
            p._card_changed = True
            p._render_scheduled()
            p._last_state = _last_state
            p._card_changed = _card_changed

        browser: Browser = dialogs._dialogs["Browser"][1]
        if browser is not None and browser._previewer is not None:
            prev_refresh(browser._previewer)
        if mw.state == "review":
            mw.reviewer._refresh_needed = RefreshNeeded.NOTE_TEXT
            mw.reviewer.refresh_if_needed()  # 这个功能时好时坏,没法判断.
        for k, v in G.mw_card_window.items():
            if v is not None:
                prev_refresh(v)
        QTimer.singleShot(2000, lambda: tooltip("anki的自动刷新功能还存在问题,如果出现显示空白,请手动重新加载卡片"))

    @staticmethod
    def exists(id):
        return card_exists(id)

    @staticmethod
    def note_get(id):
        return note_get(id)

    @staticmethod
    def desc_extract(card_id, fromField=False):
        return desc_extract(card_id, fromField)

    @staticmethod
    def get_correct_id(card_id):
        from . import objs
        if isinstance(card_id, objs.LinkDataPair):  # 有可能把pair传进来的
            cid = card_id.int_card_id
        elif isinstance(card_id,Card):
            cid=card_id.id
        elif isinstance(card_id, str):
            cid = int(card_id)
        elif type(card_id) == int:
            cid = card_id
        else:
            raise TypeError("参数类型不支持:" + card_id.__str__())
        return cid

class Media:
    @staticmethod
    def clipbox_png_save(clipuuid):
        if platform.system() in {"Darwin", "Linux"}:
            tooltip("当前系统暂时不支持该功能")
            return
        else:
            from ..clipper2.exports import fitz
        mediafolder = os.path.join(mw.pm.profileFolder(), "collection.media")
        DB = G.DB
        clipbox_ = DB.go(DB.table_clipbox).select(uuid=clipuuid).return_all().zip_up()[0]
        clipbox = G.objs.ClipboxRecord(**clipbox_)
        DB.end()
        pdfinfo_ = DB.go(DB.table_pdfinfo).select(uuid=clipbox.pdfuuid).return_all().zip_up()[0]
        pdfinfo = G.objs.PDFinfoRecord(**pdfinfo_)
        DB.end()
        doc: "fitz.Document" = fitz.open(pdfinfo.pdf_path)
        # 0.144295302 0.567695962 0.5033557047 0.1187648456
        page = doc.load_page(clipbox.pagenum)
        pagerect: "fitz.rect_like" = page.rect
        x0, y0 = clipbox.x * pagerect.width, clipbox.y * pagerect.height
        x1, y1 = x0 + clipbox.w * pagerect.width, y0 + clipbox.h * pagerect.height
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2),
                                 clip=fitz.Rect(x0, y0, x1, y1))
        pngdir = os.path.join(mediafolder, f"""hjp_clipper_{clipbox.uuid}_.png""")
        write_to_log_file(pngdir + "\n" + f"w={pixmap.width} h={pixmap.height}")
        if os.path.exists(pngdir):
            # showInfo("截图已更新")
            os.remove(pngdir)
        pixmap.save(pngdir)


class LinkPoolOperation:
    """针对链接池设计"""
    class M:
        """各种状态选择"""
        before_clean = 0
        directly = 1
        by_group = 2
        complete_map = 3
        group_by_group = 4
        unlink_by_path = 5
        unlink_by_node = 6

    @staticmethod
    def both_refresh(*args):
        o = [CardOperation, BrowserOperation, GrapherOperation]
        if len(args) > 0:
            for i in args:
                o[i].refresh()
        else:
            for Op in o:
                Op.refresh()

    @staticmethod
    def get_template():
        d = {"IdDescPairs": [], "addTag": ""}
        return d

    @staticmethod
    def read():
        d = json.load(open(G.src.path.linkpool_file, "r", encoding="utf-8"))
        x = G.objs.LinkPoolModel(fromjson=d)
        return x

    @staticmethod
    def insert(pair_li: "list[G.objs.LinkDataPair]", mode=1, need_show=True):
        L = LinkPoolOperation
        if mode == L.M.before_clean:
            L.clear()
            d = L.read()
            d.IdDescPairs = [[pair] for pair in pair_li]
        elif mode == L.M.directly:
            d = L.read()
            d.IdDescPairs += [[pair] for pair in pair_li]
        elif mode == L.M.by_group:
            d = L.read()
            d.IdDescPairs += [[pair for pair in pair_li]]
        else:
            raise TypeError("不支持的操作")
        L.write(d.todict())
        from ..bilink.dialogs.linkpool import LinkPoolDialog
        if need_show:
            if isinstance(G.mw_linkpool_window, LinkPoolDialog):
                G.mw_linkpool_window.activateWindow()
            else:
                G.mw_linkpool_window = LinkPoolDialog()
                G.mw_linkpool_window.show()

    @staticmethod
    def clear():
        d = LinkPoolOperation.get_template()
        LinkPoolOperation.write(d)
        return LinkPoolOperation

    @staticmethod
    def write(d: "dict"):
        json.dump(d, open(G.src.path.linkpool_file, "w", encoding="utf-8"))
        return LinkPoolOperation

    @staticmethod
    def exists():
        return os.path.exists(G.src.path.linkpool_file)

    @staticmethod
    def link(mode=4, pair_li: "Optional[list[G.objs.LinkDataPair]]" = None):
        def on_quit_handle(timestamp):
            cfg = Config.get()
            if cfg.open_browser_after_link.value==1:
                if cfg.add_link_tag.value==1:
                    BrowserOperation.search(f"""tag:hjp-bilink::timestamp::{timestamp}""").activateWindow()
                else:
                    s=""
                    for pair in pair_li:
                        s+=f"cid:{pair.card_id} or "
                    BrowserOperation.search(s[0:-4]).activateWindow()
            G.mw_progresser.close()
            G.mw_universal_worker.allevent.unbind()
            LinkPoolOperation.both_refresh()

        from . import widgets
        if pair_li is not None:
            LinkPoolOperation.insert(pair_li, mode=LinkPoolOperation.M.before_clean, need_show=False)
        G.mw_progresser = widgets.UniversalProgresser() #实例化一个进度条
        G.mw_universal_worker = LinkPoolOperation.LinkWorker(mode=mode) #实例化一个子线程
        G.mw_universal_worker.allevent = G.objs.AllEventAdmin([ #给子线程的不同情况提供回调函数
            [G.mw_universal_worker.on_quit, on_quit_handle], #完成时回调
            [G.mw_universal_worker.on_progress, G.mw_progresser.value_set], #进度回调
        ]).bind()
        G.mw_universal_worker.start()

    @staticmethod
    def unlink(mode=6, pair_li: "Optional[list[G.objs.LinkDataPair]]" = None):
        LinkPoolOperation.link(mode=mode, pair_li=pair_li)

    class LinkWorker(QThread):
        on_progress = pyqtSignal(object)
        on_quit = pyqtSignal(object)

        def __init__(self, mode=3):
            super().__init__()

            self.waitting = False
            self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.allevent: 'Optional[G.objs.AllEventAdmin]' = None
            self.timegap = 0.1
            self.mode = mode

        def run(self):
            from ..bilink import linkdata_admin
            L = LinkPoolOperation
            d = L.read()
            cfg = Config.get()
            flatten = d.flatten()
            total,count = len(flatten),0
            linkinfoLi = []
            #先加tag

            for pair in flatten:
                linkinfo = linkdata_admin.read_card_link_info(pair.card_id)
                linkinfo.add_tag(d.addTag)
                if cfg.add_link_tag.value == 1:
                    linkinfo.add_timestamp_tag(self.timestamp)
                linkinfoLi.append(linkinfo)
                count+=1
                self.on_progress.emit(Utils.percent_calc(total,count,0,25))

            #根据不同的模式进行不同的操作
            if self.mode in {L.M.complete_map,L.M.unlink_by_node}:
                total, count = len(flatten), 0
                for linkinfoA in linkinfoLi:
                    total2, count2 = len(flatten), 0
                    for linkinfoB in linkinfoLi:
                        if linkinfoB.self_data.card_id!=linkinfoA.self_data.card_id:
                            if self.mode == L.M.complete_map:
                                LinkDataOperation.bind(linkinfoA,linkinfoB,needsave=False)
                            elif self.mode == L.M.unlink_by_node:
                                LinkDataOperation.unbind(linkinfoA,linkinfoB,needsave=False)
                        count2 += 1
                        self.on_progress.emit(25+ceil((count2 / total2 + count) / total * 50))
                    count += 1
            elif self.mode in (L.M.group_by_group, L.M.unlink_by_path):
                li = d.IdDescPairs
                total, count = len(li), 0
                r = self.reducer(count, total, self, d)
                reduce(r.reduce_link, li)

            total, count,DB = len(flatten), 0,G.DB
            DB.go(DB.table_linkinfo)
            for linkinfo in linkinfoLi:
                linkdata_admin.LinkInfoDB.single_write(linkinfo,autocommit=False,fromDB=DB)
                count+=1
                self.on_progress.emit(Utils.percent_calc(total,count,75,25))
            DB.commit()

            self.on_quit.emit(self.timestamp)

        class reducer:
            def __init__(self, count, total, worker: "LinkPoolOperation.LinkWorker", d):
                from ..bilink import linkdata_admin
                self.count = count
                self.total = total
                self.worker = worker
                self.d = d
                self.linkdata_admin: "" = linkdata_admin
            def reduce_link(self, groupA: "list[G.objs.LinkDataPair]", groupB: "list[G.objs.LinkDataPair]"):
                self.worker.on_progress.emit(ceil(self.count / self.total * 100))
                L = LinkPoolOperation
                for pairA in groupA:
                    linkinfoA = self.linkdata_admin.read_card_link_info(pairA.card_id)
                    for pairB in groupB:
                        linkinfoB = self.linkdata_admin.read_card_link_info(pairB.card_id)
                        if self.worker.mode == L.M.group_by_group:
                            LinkDataOperation.bind(linkinfoA,linkinfoB,needsave=False)
                        elif self.worker.mode == L.M.unlink_by_path:
                            LinkDataOperation.unbind(linkinfoA,linkinfoB,needsave=False)

                return groupB


class ModelOperation:
    @staticmethod
    def get_all():
        data = []
        model = mw.col.models.all_names_and_ids()
        for i in model:
            data.append({"id": i.id, "name": i.name})
        return data


class DeckOperation:
    @staticmethod
    def get_all():
        data = []
        deck = mw.col.decks.all_names_and_ids()
        for i in deck:
            data.append({"id": i.id, "name": i.name})
        return data


class MonkeyPatch:
    @staticmethod
    def onAppMsgWrapper(self: AnkiQt):
        # self.app.appMsg.connect(self.onAppMsg)
        def handle_AnkiLink(buf):
            # buf加了绝对路径,所以要去掉
            # 有时候需要判断一下

            def handle_opencard(id):
                if CardOperation.exists(id):
                    Dialogs.open_custom_cardwindow(id).activateWindow()
                pass

            def handle_openbrowser(search):
                BrowserOperation.search(search).activateWindow()
                pass

            from .objs import CmdArgs
            cmd_dict = {"opencard_id": handle_opencard, "openbrowser_search": handle_openbrowser}

            if buf.startswith("ankilink://"):  # 此时说明刚打开就进来了,没有经过包装,格式取buf[11:-1]
                # showInfo(buf[11:-1])
                cmd = CmdArgs(buf[11:-1].split("="))
            else:
                cmd = CmdArgs(os.path.split(buf)[-1].split("="))
            if cmd.type in cmd_dict:
                cmd_dict[cmd.type](cmd.args)
            else:
                showInfo("未知指令错误/unknown command:" + cmd.type)
            pass

        def onAppMsg(buf: str):
            is_addon = self._isAddon(buf)
            is_link = "ANKILINK:" in buf.upper()
            if self.state == "startup":
                # try again in a second
                self.progress.timer(
                    1000, lambda: self.onAppMsg(buf), False, requiresCollection=False
                )
                return
            elif self.state == "profileManager":
                # can't raise window while in profile manager
                if buf == "raise":
                    return None
                self.pendingImport = buf
                if is_addon:
                    msg = tr.qt_misc_addon_will_be_installed_when_a()
                elif is_link:
                    msg = "在profile窗口下,ankilink功能无法正常使用"
                else:
                    msg = tr.qt_misc_deck_will_be_imported_when_a()
                tooltip(msg)
                return
            if not self.interactiveState() or self.progress.busy():
                # we can't raise the main window while in profile dialog, syncing, etc
                if buf != "raise":
                    showInfo(
                        tr.qt_misc_please_ensure_a_profile_is_open(),
                        parent=None,
                    )
                return None
            # raise window
            if isWin:
                # on windows we can raise the window by minimizing and restoring
                self.showMinimized()
                self.setWindowState(Qt.WindowActive)
                self.showNormal()
            else:
                # on osx we can raise the window. on unity the icon in the tray will just flash.
                self.activateWindow()
                self.raise_()
            if buf == "raise":
                return None

            # import / add-on installation
            if is_addon:
                self.installAddon(buf)
            elif is_link:
                handle_AnkiLink(buf)
            else:
                self.handleImport(buf)

            return None

        return onAppMsg


class Dialogs:
    @staticmethod
    def open_anchor(card_id):
        card_id = str(card_id)
        from ..bilink.dialogs.anchor import AnchorDialog
        from . import G
        if card_id not in G.mw_anchor_window:
            G.mw_anchor_window[card_id] = None
        if G.mw_anchor_window[card_id] is None:
            G.mw_anchor_window[card_id] = AnchorDialog(card_id)
            G.mw_anchor_window[card_id].show()
        else:
            G.mw_anchor_window[card_id].activateWindow()

    @staticmethod
    def open_clipper(pairs_li=None, clipboxlist=None, **kwargs):
        if platform.system() in {"Darwin", "Linux"}:
            tooltip("当前系统暂时不支持PDFprev")
            return
        else:
            from . import G
            from ..clipper2.lib.Clipper import Clipper
        # log.debug(G.mw_win_clipper.__str__())
        if not isinstance(G.mw_win_clipper, Clipper):
            G.mw_win_clipper = Clipper()
            G.mw_win_clipper.start(pairs_li=pairs_li, clipboxlist=clipboxlist)
            G.mw_win_clipper.show()
        else:
            G.mw_win_clipper.start(pairs_li=pairs_li, clipboxlist=clipboxlist)
            # all_objs.mw_win_clipper.show()
            G.mw_win_clipper.activateWindow()
            # print("just activate")

    @staticmethod
    def open_linkpool():
        from . import G
        from ..bilink.dialogs.linkpool import LinkPoolDialog
        if G.mw_linkpool_window is None:
            G.mw_linkpool_window = LinkPoolDialog()
            G.mw_linkpool_window.show()
        else:
            G.mw_linkpool_window.activateWindow()
        pass

    @staticmethod
    def open_PDFprev(pdfuuid, pagenum, FROM):
        if platform.system() in {"Darwin", "Linux"}:
            tooltip("当前系统暂时不支持PDFprev")
            return
        else:
            from ..clipper2.lib.PDFprev import PDFPrevDialog
        # print(FROM)
        if isinstance(FROM, Reviewer):
            card_id = FROM.card.id
            pass
        elif isinstance(FROM, BrowserPreviewer):
            card_id = FROM.card().id
            pass
        elif isinstance(FROM, SingleCardPreviewerMod):
            card_id = FROM.card().id
        else:
            TypeError("未能找到card_id")
        card_id = str(card_id)

        DB = G.DB
        result = DB.go(DB.table_pdfinfo).select(uuid=pdfuuid).return_all().zip_up()[0]
        DB.end()
        pdfname = result.to_pdfinfo_data().pdf_path
        pdfpageuuid = UUID.by_hash(pdfname + str(pagenum))
        if card_id not in G.mw_pdf_prev:
            G.mw_pdf_prev[card_id] = {}
        if pdfpageuuid not in G.mw_pdf_prev[card_id]:
            G.mw_pdf_prev[card_id][pdfpageuuid] = None
        if isinstance(G.mw_pdf_prev[card_id][pdfpageuuid], PDFPrevDialog):
            G.mw_pdf_prev[card_id][pdfpageuuid].activateWindow()
        else:
            ratio = 1
            G.mw_pdf_prev[card_id][pdfpageuuid] = \
                PDFPrevDialog(pdfuuid=pdfuuid, pdfname=pdfname, pagenum=pagenum, pageratio=ratio, card_id=card_id)
            G.mw_pdf_prev[card_id][pdfpageuuid].show()

        pass

    @staticmethod
    def open_custom_cardwindow(card: Union[Card, str, int]) -> 'Optional[SingleCardPreviewerMod]':
        """请注意需要你自己激活窗口 请自己做好卡片存在性检查,这一层不检查 """
        from ..bilink.dialogs.custom_cardwindow import external_card_dialog
        if not isinstance(card, Card):
            card = mw.col.get_card(CardId(int(card)))
        return external_card_dialog(card)
        pass

    @staticmethod
    def open_support():
        from .widgets import SupportDialog
        p = SupportDialog()
        p.exec()

    @staticmethod
    def open_contact():
        QDesktopServices.openUrl(QUrl(G.src.path.groupSite))

    @staticmethod
    def open_link_storage_folder():
        open_file(G.src.path.user)

    @staticmethod
    def open_repository():
        QDesktopServices.openUrl(QUrl(G.src.path.helpSite))

    @staticmethod
    def open_version():
        from ..bilink import dialogs
        p = dialogs.version.VersionDialog()
        p.exec()

    @staticmethod
    def open_tag_chooser(pair_li: "list[G.objs.LinkDataPair]"):
        from . import widgets
        p = widgets.tag_chooser(pair_li)
        p.exec()
        pass

    @staticmethod
    def open_deck_chooser(pair_li: "list[G.objs.LinkDataPair]", view=None):
        from . import widgets

        p = widgets.deck_chooser(pair_li, view)
        p.exec()
        tooltip("完成")

        pass

    @staticmethod
    def open_grapher(pair_li: "list[G.objs.LinkDataPair]", need_activate=True, gviewdata:"GViewData"=None,
                     selected_as_center=True,mode=GraphMode.normal, ):
        from ..bilink.dialogs.linkdata_grapher import Grapher
        if mode == GraphMode.normal:
            if isinstance(G.mw_grapher, Grapher):
                G.mw_grapher.load_node(pair_li, selected_as_center=selected_as_center)
                if need_activate:
                    G.mw_grapher.activateWindow()
            else:
                G.mw_grapher = Grapher(pair_li)
                G.mw_grapher.show()
        elif mode == GraphMode.view_mode:
            if (gviewdata.uuid not in G.mw_gview) or (not isinstance(G.mw_gview[gviewdata.uuid],Grapher)):
                G.mw_gview[gviewdata.uuid]=Grapher(pair_li=pair_li,mode=mode,gviewdata=gviewdata)
                G.mw_gview[gviewdata.uuid].show()
            else:
                G.mw_gview[gviewdata.uuid].view_node(pair_li)
                tooltip(f"here G.mw_gview[{gviewdata.uuid}]")
                if need_activate:
                    G.mw_gview[gviewdata.uuid].show()
                    G.mw_gview[gviewdata.uuid].activateWindow()
class UUID:
    @staticmethod
    def by_random(length=8):
        myid = str(uuid.uuid4())[0:length]
        return myid

    @staticmethod
    def by_hash(s):
        return str(uuid.uuid3(uuid.NAMESPACE_URL, s))


def button_icon_clicked_switch(button: QToolButton, old: list, new: list, callback: "callable" = None):
    if button.text() == old[0]:
        button.setText(new[0])
        button.setIcon(QIcon(new[1]))
    else:
        button.setText(old[0])
        button.setIcon(QIcon(old[1]))
    if callback:
        callback(button.text())


def logger(logname=None, level=None, allhandler=None):
    if G.ISDEBUG:
        if logname is None:
            logname = "hjp_clipper"
        if level is None:
            level = logging.DEBUG
        printer = logging.getLogger(logname)
        printer.setLevel(level)
        log_dir = G.src.path.logtext

        fmt = "%(asctime)s %(levelname)s %(threadName)s  %(pathname)s\n%(filename)s " \
              "%(lineno)d\n%(funcName)s:\n %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)

        filehandle = logging.FileHandler(log_dir)
        filehandle.setLevel(level)
        filehandle.setFormatter(formatter)

        consolehandle = logging.StreamHandler()
        consolehandle.setLevel(level)
        consolehandle.setFormatter(formatter)
        printer.addHandler(consolehandle)
        printer.addHandler(filehandle)
        return printer
    else:
        return do_nothing


def do_nothing(*args, **kwargs):
    pass


def write_to_log_file(s):
    f = open(G.src.path.logtext, "a", encoding="utf-8")
    f.write("\n" + s)
    f.close()


def str_shorten(string, length=30) -> str:
    if len(string) <= length:
        return string
    else:
        return string[0:int(length / 2) - 3] + "..." + string[-int(length / 2):]


def HTML_injecttoweb(htmltext, card, kind):
    """在web渲染前,注入html代码,"""
    if kind in [
        "previewQuestion",
        "previewAnswer",
        "reviewQuestion",
        "reviewAnswer"
    ]:
        from .HTMLbutton_render import HTMLbutton_make
        html_string = HTMLbutton_make(htmltext, card)
        # console(html_string).log.end()
        return html_string
    else:
        return htmltext


def HTML_clipbox_sync_check(card_id, root):
    # 用于保持同步
    assert type(root) == BeautifulSoup
    assert type(card_id) == str
    DB = G.DB
    clipbox_from_DB_ = DB.go(DB.table_clipbox).select(DB.LIKE("card_id", f"%{card_id}%")).return_all().zip_up()
    clipbox_from_DB = set([clipbox["uuid"] for clipbox in clipbox_from_DB_])
    # 选取 clipbox from field
    fields = "\n".join(mw.col.getCard(CardId(int(card_id))).note().fields)
    clipbox_from_field = set(HTML_clipbox_uuid_get(fields))
    # 多退少补,
    DBadd = clipbox_from_field - clipbox_from_DB
    DBdel = clipbox_from_DB - clipbox_from_field
    # print(
    #     f"card_id={card_id},clipbox_from_DB={clipbox_from_DB}, clipbox_from_field={clipbox_from_field}, DBADD={DBadd}.  DBdel={DBdel}")
    if len(DBadd) > 0:
        # DB.add_card_id(DB.where_maker(IN=True, colname="uuid", vals=DBadd), card_id)
        DB.add_card_id(DB.IN("uuid", *DBadd), card_id)
    if len(DBdel) > 0:
        # DB.del_card_id(DB.where_maker(IN=True, colname="uuid", vals=DBdel), card_id)
        DB.del_card_id(DB.IN("uuid", *DBdel), card_id)
    DB.end()
    pass


def HTML_clipbox_PDF_info_dict_read(root):
    """ 从所给的HTML 中读取 每个clipbox对应的 PDFuuid,以及其名字,和所包含的页码"""
    assert type(root) == BeautifulSoup
    clipbox_from_field = set(HTML_clipbox_uuid_get(root))
    DB = G.DB
    DB.go(DB.table_clipbox).select(DB.IN("uuid", *clipbox_from_field))

    # DB.go(DB.table_clipbox).select(where=DB.where_maker(IN=True, vals=clipbox_from_field, colname="uuid"))
    # print(DB.excute_queue[-1])
    record_li = DB.return_all().zip_up().to_clipbox_data()
    PDF_info_dict = {}  # {uuid:{pagenum:{},pdfname:""}}
    for record in record_li:
        PDFinfo = DB.go(DB.table_pdfinfo).select(uuid=record.pdfuuid).return_all().zip_up()[0].to_pdfinfo_data()
        if PDFinfo.uuid not in PDF_info_dict:
            PDF_info_dict[PDFinfo.uuid] = {"pagenum": set(),  # 页码唯一化
                                           "info": PDFinfo}  # 只提取页码, 大小重新再设定.偏移量也重新设定.
        PDF_info_dict[PDFinfo.uuid]["pagenum"].add(record.pagenum)
    DB.end()
    return PDF_info_dict


def HTML_LeftTopContainer_detail_el_make(root: "BeautifulSoup", summaryname, attr: "dict" = None):
    """这是一个公共的步骤,设计一个details, root 传进来无所谓的, 不会基于他做操作,只是引用了他的基本功能
    details.hjp_bilink .details
        summary
        div
    """
    if attr is None:
        attr = {}
    attrs = {"class": "hjp_bilink details", **(attr.copy())}
    # print(attrs)
    details = root.new_tag("details", attrs=attrs)
    summary = root.new_tag("summary")
    summary.string = summaryname
    div = root.new_tag("div")
    details.append(summary)
    details.append(div)
    return details, div


def HTML_clipbox_uuid_get(html):
    if type(html) == str:
        root = BeautifulSoup(html, "html.parser")
    elif type(html) == BeautifulSoup:
        root = html
    else:
        raise TypeError("无法处理参数类型: {}".format(type(html)))
    imgli = root.find_all("img", src=re.compile("hjp_clipper_\w{8}_.png"))
    clipbox_uuid_li = [re.sub("hjp_clipper_(\w+)_.png", lambda x: x.group(1), img.attrs["src"]) for img in imgli]
    return clipbox_uuid_li


def HTML_clipbox_exists(html, card_id=None):
    """任务:
    1检查clipbox的uuid是否在数据库中存在,如果存在,返回True,不存在返回False,
    2当存在时,检查卡片id是否是clipbox对应card_id,如果不是,则要添加,此卡片
    3搜索本卡片,得到clipbox的uuid,如果有搜到 uuid 但是又不在html解析出的uuid中, 则将数据库中的uuid的card_id删去本卡片的id
    """
    clipbox_uuid_li = HTML_clipbox_uuid_get(html)
    DB = G.DB
    DB.go(DB.table_clipbox)
    # print(clipbox_uuid_li)
    true_or_false_li = [DB.exists(DB.EQ(uuid=uuid)) for uuid in clipbox_uuid_li]
    DB.end()
    return (reduce(lambda x, y: x or y, true_or_false_li, False))


def HTML_LeftTopContainer_make(root: "BeautifulSoup"):
    """
    注意在这一层已经完成了,CSS注入
    传入的是从html文本解析成的beautifulSoup对象
    设计的是webview页面的左上角按钮,包括的内容有:
    anchorname            ->一切的开始
        style             ->样式设计
        div.container_L0  ->按钮所在地
            div.header_L1 ->就是 hjp_bilink 这个名字所在的地方
            div.body_L1   ->就是按钮和折叠栏所在的地方
    一开始会先检查这个anchorname元素是不是已经存在,如果存在则直接读取
    """
    # 寻找 anchorname ,建立 anchor_el,作为总的锚点.
    ID = G.addonName
    # ID = ""
    anchorname = ID if ID != "" else "anchor_container"
    resultli = root.select(f"#{anchorname}")
    if len(resultli) > 0:  # 如果已经存在,就直接取得并返回
        anchor_el: "element.Tag" = resultli[0]
    else:
        anchor_el: "element.Tag" = root.new_tag("div", attrs={"id": anchorname})
        root.insert(1, anchor_el)
        # 设计 style
        style_str = open(G.src.path.anchor_CSS_file, "r", encoding="utf-8").read()
        style = root.new_tag("style")
        style.string = style_str
        anchor_el.append(style)
        # 设计 容器 div.container_L0, div.header_L1和div.body_L1
        L0 = root.new_tag("div", attrs={"class": "container_L0"})
        header_L1 = root.new_tag("div", attrs={"class": "container_header_L1"})
        header_L1.string = G.addonName
        body_L1 = root.new_tag("div", attrs={"class": "container_body_L1"})
        L0.append(header_L1)
        L0.append(body_L1)
        anchor_el.append(L0)
    return anchor_el  # 已经传入了root,因此不必传出.


class AnkiLinks:
    class Type:
        html = 0
        markdown = 1
        orgmode = 2

    @staticmethod
    def copy_card_as(linktype: int, pairs_li: 'list[G.objs.LinkDataPair]'):
        tooltip(pairs_li.__str__())
        clipboard = QApplication.clipboard()
        header = "ankilink://opencard_id="

        def as_html(pairs_li: 'list[G.objs.LinkDataPair]'):
            total = ""
            puretext = ""
            for pair in pairs_li:
                total += f"""<a href="{header}{pair.card_id}">{pair.desc}<a><br>""" + "\n"
                puretext += f"""{header}{pair.card_id}\n"""
            mmdata = QMimeData()
            mmdata.setHtml(total)
            mmdata.setText(puretext)
            clipboard.setMimeData(mmdata)
            # clipboard.setText(total)
            pass

        def as_markdown(pairs_li: 'list[G.objs.LinkDataPair]'):
            total = ""
            for pair in pairs_li:
                total += f"""[{pair.desc}]({header}{pair.card_id})\n"""
            clipboard.setText(total)
            pass

        def as_orgmode(pairs_li: 'list[G.objs.LinkDataPair]'):
            total = ""
            for pair in pairs_li:
                total += f"""[[{header}{pair.card_id}][{pair.desc}]]\n"""
            clipboard.setText(total)
            pass

        typ = AnkiLinks.Type
        func_dict = {typ.html: as_html,
                     typ.orgmode: as_orgmode,
                     typ.markdown: as_markdown}
        func_dict[linktype](pairs_li)

    @staticmethod
    def copy_search_as(linktype: int, browser: "Browser"):
        searchstring = browser.form.searchEdit.currentText()
        tooltip(searchstring)
        clipboard = QApplication.clipboard()
        header = "ankilink://openbrowser_search="
        href = header + quote(searchstring)

        def as_html():
            total = f"""<a href="{href}">Anki搜索:{searchstring}</a>"""
            mmdata = QMimeData()
            mmdata.setHtml(total)
            clipboard.setMimeData(mmdata)
            pass

        def as_markdown():
            total = f"[Anki搜索:{searchstring}]({href})"
            clipboard.setText(total)
            pass

        def as_orgmode():
            total = f"[[{href}][Anki搜索:{searchstring}]]"
            clipboard.setText(total)
            pass

        typ = AnkiLinks.Type
        func_dict = {typ.html: as_html,
                     typ.orgmode: as_orgmode,
                     typ.markdown: as_markdown}
        func_dict[linktype]()
        pass


def copy_intext_links(pairs_li: 'list[G.objs.LinkDataPair]'):
    from .objs import LinkDataPair
    from .language import rosetta as say
    def linkformat(card_id, desc):
        return f"""[[link:{card_id}_{desc}_]]"""

    copylinkLi = [linkformat(pair.card_id, pair.desc) for pair in pairs_li]
    clipstring = "\n".join(copylinkLi)
    if clipstring == "":
        tooltip(f"""{say("未选择卡片")}""")
    else:
        clipboard = QApplication.clipboard()
        clipboard.setText(clipstring)
        tooltip(f"""{say("已复制到剪贴板")}：{clipstring}""")
    pass


def PDFprev_close(card_id, pdfpageuuid=None, all=False):
    if platform.system() in {"Darwin", "Linux"}:
        # tooltip("当前系统暂时不支持PDFprev")
        return
    else:
        from . import G
        from ..clipper2.lib.PDFprev import PDFPrevDialog
    if isinstance(card_id, int):
        card_id = str(card_id)
    if card_id not in G.mw_pdf_prev:
        return
    reviewer_still = mw.reviewer.card is not None and mw.reviewer.card.id == int(card_id)
    browser = dialogs._dialogs["Browser"][1]  # aqt.mw = self
    previewer_still = browser is not None and browser._previewer is not None \
                      and browser._previewer.card() is not None and browser._previewer.card().id == int(card_id)
    card_window_still = card_id in G.mw_card_window and G.mw_card_window[card_id] is not None
    if reviewer_still or previewer_still or card_window_still:
        return
    if all:
        for pdfpageuuid in G.mw_pdf_prev[card_id].keys():
            if isinstance(G.mw_pdf_prev[card_id][pdfpageuuid], PDFPrevDialog):
                p = G.mw_pdf_prev[card_id][pdfpageuuid]
                p.close()
                # all_objs.mw_pdf_prev[card_id][pdfpageuuid]=None
    else:
        if pdfpageuuid in G.mw_pdf_prev[card_id]:
            p = G.mw_pdf_prev[card_id][pdfpageuuid]
            p.close()
            # all_objs.mw_pdf_prev[card_id][pdfpageuuid] = None


def on_clipper_closed_handle():
    from . import G
    G.mw_win_clipper = None


def event_handle_connect(event_dict):
    for event, handle in event_dict:
        event.connect(handle)
    return event_dict


def event_handle_disconnect(event_dict: "list[list[pyqtSignal,callable]]"):
    for event, handle in event_dict:
        try:
            # print(event.signal)
            event.disconnect(handle)
            # print(f"""{event.__str__()} still has {}  connects""")
        except Exception:
            # print(f"{event.__str__()} do not connect to {handle.__str__()}")
            pass


def open_file(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def version_cmpkey(path):
    from . import objs
    filename = os.path.basename(path)
    v_tuple = re.search(r"(\d+)\.(\d+)\.(\d+)", filename).groups()
    return objs.AddonVersion(v_tuple)


def note_get(card_id):
    from . import objs
    cid = CardOperation.get_correct_id(card_id)
    if card_exists(cid):
        note = mw.col.getCard(cid).note()
    else:
        showInfo(f"{cid} 卡片不存在/card don't exist")
        return None
    return note


def desc_extract(card_id=None, fromField=False):
    """读取卡片的描述,需要卡片id, fromField就是为了避免循环递归, fromField 意思是从卡片的Field提取描述"""
    from . import objs
    from ..bilink import linkdata_admin

    def get_desc_from_field(_note: Note) -> str:
        content = reduce(lambda x, y: x + y, _note.fields)
        _desc = HTML_txtContent_read(content)
        _desc = re.sub(r"\n+", "", _desc)
        _desc = _desc if cfg.length_of_desc.value == 0 else _desc[0:min(cfg.length_of_desc.value, len(_desc))]
        return _desc
    cid = CardOperation.get_correct_id(card_id)
    cfg = Config.get()
    note = note_get(cid)
    desc = ""
    if note is not None:
        if fromField or cfg.desc_sync.value == 1:  # 分成这两段, 是因为一个循环引用.
            desc = get_desc_from_field(note)
        else:
            desc = linkdata_admin.read_card_link_info(str(cid)).self_data.desc
            if desc == "":
                desc = get_desc_from_field(note)
    return desc


def card_exists(card_id):
    from . import objs
    cid = CardOperation.get_correct_id(card_id)
    txt = f"cid:{cid}"
    card_ids = mw.col.find_cards(txt)

    if len(card_ids) == 1:
        return True
    else:
        tooltip("卡片不存在/card not exists:\n"
                "id=" + str(cid))
        return False


def HTML_txtContent_read(html):
    """HTML文本内容的读取,如果没有就尝试找img的src文本"""

    from ..bilink.in_text_admin.backlink_reader import BackLinkReader

    cfg = ConfigInterface()
    root = BeautifulSoup(html, "html.parser")
    text = root.getText()
    if cfg.delete_intext_link_when_extract_desc.value == 1:
        newtext = text
        replace_str = ""
        intextlinks = BackLinkReader(html_str=text).backlink_get()
        for link in intextlinks:
            span = link["span"]
            replace_str += re.sub("(\])|(\[)", lambda x: "\]" if x.group(0) == "]" else "\[",
                                  text[span[0]:span[1]]) + "|"
        replace_str = replace_str[0:-1]
        text = re.sub(replace_str, "", newtext)
    if not re.search("\S", text):
        a = root.find("img")
        if a is not None:
            text = a.attrs["src"]

    return text


def pair_li_make(card_li: "list[str]"):
    from .objs import LinkDataPair
    d = [LinkDataPair(card_id=card_id, desc=desc_extract(card_id)) for card_id in card_li]
    return d


def data_crashed_report(data):
    from . import G
    path = G.src.path.data_crash_log
    showInfo(f"你的卡片链接信息读取失败,相关的失败数据已经保存到{path},请联系作者\n"
             f"Your card link information failed to read, the related failure data has been saved to{path}, please contact the author")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    caller = sys._getframe(1).f_code.co_name
    filename = sys._getframe(1).f_code.co_filename
    line_number = sys._getframe(1).f_lineno
    data_string = data.__str__()
    info = f"""\n{filename}\n{timestamp} {caller} {line_number}\n{data_string}"""
    if not os.path.exists(path):
        f = open(path, "w", encoding="utf-8")
    else:
        f = open(path, "a", encoding="utf-8")
    f.write(info)


CardId = Compatible.CardId()
log = logger(__name__)


class LOG:
    logger = logger(__name__)
    file_write = write_to_log_file

    @staticmethod
    def file_clear():
        f = open(G.src.path.logtext, "w", encoding="utf-8")
        f.write("")

    @staticmethod
    def exists():
        return os.path.exists(G.src.path.logtext)
