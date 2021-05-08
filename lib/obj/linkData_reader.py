"""
表结构:
    20210417123432版本
    旧版兼容接口
    card_linked_pairLi:List[Pair], 以Pair类型为元素的列表
    card_selfdata_dict={
        "menuli":[{"type": "cardinfo", "card_id": "1611035897919" },
        {"type":"groupinfo","groupname":"new group"}]
        "groupinfo":{#groupinfo不做嵌套处理, 因为不需要这么多.
            "new group": [1611035897919]
        }
    }, 表达链接的存储结构
    cardinfo_dict:{"card_id":Pair} 用来查询卡片的具体内容

    新版数据库JSON格式规范
    字段1 : card_id : 123456789
    字段2 : info:
            {   "version": 1,
                "self_data": {"card_id": "1234567", "desc": "334455"},
                "link_list":
                [{"card_id": "1618912345046", "desc": "B", "dir": "→"},
                {"card_id": "1618912351734", "desc": "D", "dir": "→"},
                {"card_id": "1618912346117", "desc": "C", "dir": "→"}],
                "root": [{"card_id": "1618912345046"}, {"nodename": "new_group"}],
                "node":
                {"new_group": [{"card_id": "1618912351734"}, {"card_id": "1618912346117"}],
                "1618912345046": {"card_id": "1618912345046", "desc": "B", "dir": "→"},
                "1618912351734": {"card_id": "1618912351734", "desc": "D", "dir": "→"},
                "1618912346117": {"card_id": "1618912346117", "desc": "C", "dir": "→"}}}


    <!--<script id="hjp_bilink_data">hjp_bilink_data=[{"card_id": "1618912345046", "desc": "B", "dir": "→"}]</script>
<script id="hjp_bilink_selfdata">hjp_bilink_selfdata={"menuli": [], "groupinfo": {}}</script>-->

最新的id 是 hjp_bilink_info_v1
"""

import json, re
from anki.notes import Note
from aqt.utils import showInfo

from .handle_DB import LinkInfoDBmanager
from .languageObj import rosetta as say
from .cardInfo_obj import CardLinkInfo
from .linkData_syncer import DataSyncer
from .utils import BaseInfo, Pair, console, Config
from bs4 import BeautifulSoup, element
from aqt import mw


# class FieldHandler(Config):
# """可能是将来的统一类, 用来操作从field中提取"""

class LinkDataReader(Config):
    """
    用来统一读取链接数据的接口.
    """

    def __init__(self, card_id):
        super().__init__()
        self.card_id = card_id
        self.storageLocation = self.user_cfg["linkInfoStorageLocation"]
        self.consolerName = self.base_cfg["consoler_Name"]
        self.data_version = self.base_cfg["data_version"]
        self.readFuncDict = {
            0: DataDBReader,
            1: DataFieldReader,
            2: DataJSONReader
        }

    def read(self):
        """用来读取链接信息为下一步的按钮渲染做准备, 并且作兼容处理, """
        data = self.readFuncDict[self.storageLocation](self.card_id).read()
        return DataSyncer(data).sync().data


class DataFieldReader(Config):
    """
    从字段中读取的工具
    """

    def __init__(self, card_id):
        super().__init__()
        if type(card_id) == str:
            card_id = int(card_id)
        self.card_id = card_id
        self.consolerName = self.base_cfg["consoler_Name"]
        self.data_version = self.base_cfg["data_version"]
        self.note: Note = mw.col.getCard(card_id).note()
        self.field = self.note.fields[self.user_cfg["appendNoteFieldPosition"]]
        self.domRoot = BeautifulSoup(self.field, "html.parser")
        self.comment_el = self.comment_el_select()
        self.script_el_li = self.script_el_select()
        self.json_data = self.json_data_make()
        self.link_list = self.json_data["link_list"]
        self.root = self.json_data["root"]
        self.node = self.json_data["node"]

    def json_data_make(self):
        """制作JSON数据"""
        json_data = {
            "version": self.data_version,
            "link_list": [],
            "self_data": {
                "card_id": str(self.card_id),
                "desc": ""
            },
            "root": [],
            "node": {}
        }
        old_keywords1 = ["menuli", "groupinfo"]
        if self.script_el_li != [None, None]:
            for el in self.script_el_li:
                el_str = el.string
                try:
                    el_json = json.loads(re.sub(fr"{self.consolerName}\w+=", "", el_str))
                except json.JSONDecodeError as e:
                    print(repr(e))

                # 我们要将最终数据直接保存成json_data变量中的样子,所以下面的写法,要兼容新版和旧版.
                if "version" in el_json:
                    if el_json["version"] == 1:  # 这个版本直接就提取了
                        json_data = el_json
                    else:  # 目前还没有其他版本.
                        pass
                else:  # 连版本字段都不存在,那就是最旧的版本.
                    if "hjp_bilink_data" in el_str:
                        json_data["link_list"] = el_json
                    if "hjp_bilink_selfdata" in el_str:
                        json_data["root"] = el_json["menuli"]
                        json_data["node"] = el_json["groupinfo"]

        return json_data

    def script_el_select(self):
        """读取指定的脚本内容"""
        if self.comment_el is not None:
            comment = BeautifulSoup(self.comment_el.string, "html.parser")
            return comment.find_all(name="script", attrs={"id": re.compile(fr"{self.consolerName}\w+")})
        else:
            return [None, None]

    def comment_el_select(self):
        """读取指定的注释内容"""
        parent_el, dataType = self.domRoot, self.consolerName
        return parent_el.find(text=lambda text: isinstance(text, element.Comment) and dataType in text)

    def read(self):
        """这是从JSON,DB,FIELD读取数据的统一接口"""
        return self.json_data


class DataDBReader(Config):
    """从数据库中读取数据"""
    pass


class DataJSONReader(Config):
    """从JSON文件中读取数据"""
    pass