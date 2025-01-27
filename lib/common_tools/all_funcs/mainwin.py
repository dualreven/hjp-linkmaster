import types

from anki.scheduler.v3 import QueuedCards

from .basic_funcs import  *
from aqt.main import MainWindowState
from aqt.reviewer import V3Scheduler
from anki.cards import Card

class MainWinOperation:
    @staticmethod
    def 当_窗口状态改变(当前状态:MainWindowState,上个状态:MainWindowState):
        if 当前状态 == "overview" and 上个状态!= "overview":
            插件全局变量:G.插件全局变量=mw.__dict__[G.src.addon_name]
            插件全局变量["复习队列"] = mw.col.sched.get_queued_cards(fetch_limit=3000)
            # tooltip("开始review")
        elif 当前状态 != "review" and 当前状态 != "overview"  and 上个状态== "review":
            插件全局变量: G.插件全局变量 = mw.__dict__[G.src.addon_name]
            插件全局变量["复习队列"] = None
            # tooltip("review结束")
            # showInfo("review结束")


    @staticmethod
    def 当_reviewer加载完成(reviewer:"Reviewer"):
        from ..funcs import CardOperation
        ankilink = G.src.ankilink
        def Reviewer_answerCard(self, ease: Literal[1, 2, 3, 4]) -> None:
            "Reschedule card and show next."
            if self.mw.state != "review":
                # showing resetRequired screen; ignore key
                return
            if self.state != "answer":
                return
            proceed, ease = gui_hooks.reviewer_will_answer_card(
                (True, ease), self, self.card
            )
            if not proceed:
                return

            sched = cast(V3Scheduler, self.mw.col.sched)
            answer = sched.build_answer(
                card=self.card,
                states=self._v3.states,
                rating=self._v3.rating_from_ease(ease),
            )

            def after_answer(changes: "OpChanges") -> None:
                if gui_hooks.reviewer_did_answer_card.count() > 0:
                    self.card.load()
                self._after_answering(ease)
                if sched.state_is_leech(answer.new_state):
                    self.onLeech()

            self.state = "transition"
            CardOperation.answer_card(self.card, ease, answer)
            after_answer(None)
            # answer_card(parent=self.mw, answer=answer).success(
            #     after_answer
            # ).run_in_background(initiator=self)

        def Reviewer_get_next_v3_card(self: "Reviewer"):

            插件全局变量: G.插件全局变量 = mw.__dict__[G.src.addon_name]
            复习队列:QueuedCards = 插件全局变量["复习队列"]
            # showInfo(f"{复习队列=}")
            if 复习队列 is None or len(复习队列.cards)==0:
                # tooltip("复习队列为空")
                return
            self._v3 = V3CardInfo.from_queue(复习队列)
            self.card = Card(self.mw.col, backend_card=self._v3.top_card().card)
            self.card.start_timer()
            # tooltip(f"next_v3_card,{len(复习队列.cards)=}")

        def Reviewer_showAnswerButton(self: "Reviewer"):
            推迟按钮名 = "移到队尾"
            推迟按钮 = f'''
                        <td align="center">
                            <button title="{推迟按钮名}" onclick="javascript:pycmd('{ankilink.protocol}://{ankilink.Cmd.moveToEnd}?{ankilink.Key.card}={self.card.id}')">{推迟按钮名}</button>
                        </td>
                        '''
            # card_id = self.card.id
            推迟按钮_bs对象 = BeautifulSoup(推迟按钮, "html.parser")


            middle = """
            <button title="{}" id="ansbut" onclick='pycmd("ans");'>{}<span class=stattxt>{}</span></button>""".format(
                tr.actions_shortcut_key(val=tr.studying_space()),
                tr.studying_show_answer(),
                self._remaining(),
            )
            # wrap it in a table so it has the same top margin as the ease buttons
            middle = (
                    "<table cellpadding=0><tr><td class=stat2 align=center>%s</td></tr></table>"
                    % middle
            )
            回答按钮_bs对象 = BeautifulSoup(middle, "html.parser")
            first_td = 回答按钮_bs对象.find('tr')
            first_td.append(推迟按钮_bs对象.td)
            middle = str(回答按钮_bs对象)
            if self.card.should_show_timer():
                maxTime = self.card.time_limit() / 1000
            else:
                maxTime = 0
            self.bottom.web.eval("showQuestion(%s,%d);" % (json.dumps(middle), maxTime))

        reviewer._get_next_v3_card = types.MethodType(Reviewer_get_next_v3_card, reviewer)
        reviewer._answerCard = types.MethodType(Reviewer_answerCard, reviewer)
        reviewer._showAnswerButton= types.MethodType(Reviewer_showAnswerButton, reviewer)
        pass