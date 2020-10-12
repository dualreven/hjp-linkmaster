# hjp-bilink使用介绍
- 插件版本:0.2 (请校对你手上获取的版本是否对应)
- [插件地址](https://gitee.com/huangjipan/hjp-bilink)
- 本插件实现在anki上简易的手动双向绑定.
- 依赖的插件代码 1423933177 ,他提供了核心的卡片单向链接功能.
- 本插件将单向链接自动化实现链过去的同时又链回来,并且提供两种链接算法.新增功能(已经实现),可以按两种方式取消卡片之间的链接.
- 讨论QQ群:891730352
- ![0nlpjS.jpg](https://s1.ax1x.com/2020/09/30/0nlpjS.jpg)
## 插件的安装
### `hjp-bilink`的安装
下载克隆这个插件仓库到本地,把文件夹`hjp-bilink`复制到anki的插件文件夹下,这个位置windows上一般是`C:\Users\Administrator\AppData\Roaming\Anki2\addons21`
如果不知道插件文件夹在哪里,打开anki的`工具>附加组件>查看文件`也可以打开
### 依赖插件`link Cards`的安装
到`工具>附加组件>获取插件`输入1423933177  即可安装依赖插件
装完以后记得重启anki
## 使用教程
目前这个工具用起来还是有一点繁琐的,将来会加入对话框功能,简化操作.
1. ### 打开`browser`
- 就是在主界面点击`浏览/browse`弹出的那个窗口
2. ### 选取卡片记录插入`input.json`
- 在`browser`窗口中选中几条你要双链的记录,
- 根据模式不同,有以下两种录入的方式
-  当你需要使用 1 **`linkall`完全链接模式**, 2 **`unlinkNode`按结点取消链接模式** , 3 **`unlinkPath`按路径取消链接模式** 采用如下录入的方式
    - 点击右键,选择`hjpCopyCidAlltoInputJson`,就能把你选的这几条记录的`card_id`插入到`input.json`中
    - 你可以反复执行这个过程,把所有需要的卡片ID都录入到`input.json`中
-  **`linkGroupToGroup` 按组链接模式**  
    - 选择`hjpAsGroupCopytoInputJson`,把所有选中的记录作为一个组录入到`input.json`中,
    - 注意 组链接至少需要两个组才能正常工作
3. ### (如果需要)打开`input.json`编辑卡片ID和描述desc,
- 在你把想双链的卡的id都插入到这个`input.json`中后,你可以点击菜单栏上的`hjp_link>show`打开`input.json`
- `input.json`里面都是你在第二步操作中输入的`card_id`还有程序默认提取的描述`desc`,你这时候可以修改默认的描述内容,你也可以不追加解释,走下一步操作.
![0Rd6yj.png](https://s1.ax1x.com/2020/10/12/0Rd6yj.png)
4. ### 建立双向连接
- 选择`hjp_link>linkDefault`就会根据配置自动建立双向连接 
- 选择`hjp_link>linkAll`调用完全图算法链接每个记录
- 选择`hjp_link>linkGroupToGroup`调用组链接算法链接各个组的记录.
- 选择`hjp_link>unlinkNode`调用取消结点链接算法
- 选择`hjp_link>unlinkPath`调用取消路径链接算法
5. ### (如果需要)清除json中的记录
- 选择`hjp_link`->`clear`就能删掉之前的全部记录.
-  **如果不熟悉json的语法,千万别自己删json的结构,最好用clear清除记录,不容易破坏json结构,否则会频繁报错.** 
- 如果你熟悉json的语法,以上操作也可以打开`input.json`手工完成录入.

## 配置指导
配置文件名为`config.json`,可以在ANKI插件页面做修改,也可以通过`hjp_link->config`打开,可修改的值有
1. ### linkMode
- 链接多张卡片的算法,值为0或1,2,3,默认为0
- 0表示完全链接`linkAll`，在txt中的每一张卡双向连接到每一张卡,比如输入ABC,那么A中有BC,B中有AC,C中有BA的ID链接.
- 1表示按组链接`linkGroupToGroup`，在txt中会分成几个组,前一个组的每一张卡双向连接到后一个组的每一张卡,组与组之间用一个空的`rowSeparator`区分,默认就是空一行表示区分
- 2表示按结点取消链接`unlinknode`，相当于将txt中的每个节点孤立，比如txt中有节点A，那么程序会查询A卡片，并发现A连接到BCD，那么就会解到BCD的除链接，并且反向解除BCD到A的链接。
- 3表示按路径取消链接`unlinkpath`，相当于将txt中的彼此相连的节点按顺序解除绑定，比如输入txt中的ABCD是彼此有链接的节点，那么程序就会从A节点开始，从A到B解除链接，B到C解除链接以此类推，但是不会解除A到其他结点的链接。
两个组.比如`ABC回车DEF`,那么A,B,C都会连接到DEF,但A,B,C彼此不相连,同理DEF也会连接到ABC但彼此不相连.
2. ### rowSeparator（已经废弃）
- 默认为"\n",表示一行一条链接,rowSeparator控制每一条记录的区分
- 也是分组的标识符,此时不能后面跟内容,直到下一个rowSeparator为止
- 标识符不能落到某条记录的内部,必须在外部
3. ### colSeparator（已经废弃）
- colSeparator控制每一条记录中不同字段的区分,在本插件中就是卡ID与描述内容的区分,
4. ### cidPrefix
- 表示每个卡ID的默认前缀,可以为空,但如果装了最后请注意标识符在txt中的含义必须是唯一确定的,不能在插入的正文中使用标识符
5. ### appendNoteFieldPosition
- 这个属性控制双链的标记插入到anki卡片的第几个字段,取值从0开始,所以第一个字段为0,默认为2,也就是第三个字段
6. ### readDescFieldPosition
- 这个属性控制程序默认从卡片的第几个字段提取卡片描述的字符，数据类型为number
7. ### regexForDescContent
- 这个属性控制程序从卡片提取描述字符的方法，默认为0的话，会调用`DEFAULT>regexForDescContent`中的正则表达式来提取描述字符.如果你想按自己的正则表达式提取描述字符,可以改外层的`regexForDescContent`的值.

## 动画指导
单向链接的使用
![0n1jQf.gif](https://s1.ax1x.com/2020/09/30/0n1jQf.gif)
双向链接的设置
![0n3JOO.gif](https://s1.ax1x.com/2020/09/30/0n3JOO.gif)

## 未来计划
### 近期
- [x] 为了方便操作,将来会将卡片ID存储的txt文本改为json数据({id:,desc:})
- [ ] 实现各种方案转为tag(deck路径转tag,卡片内容转tag)
- [x] 实现unlink功能(若选中的卡片存在link关系,则删除这个link)
- [ ] 实现答题日志系统(点击显示答案后的任意一个按钮都会弹出是否记录日志的问号,选择是就会记录当前的文本到指定的位置.)
- [x] 代码转移到gitee
### 长期
- [ ] 实现UI界面(抛弃丑陋的txt文本编辑,减少用户犯错几率)

## 更新记录
0.2
新增unlink取消链接，算法也是两种
txt文本改为JSON数据,增加了易用性

0.1.1
修复了一些bug,比如重复插入卡片id

0.1
为了方便切换不同的链接模式,现在把两个模式直接拿到菜单中可点击了.
实现可修改前缀,网络化发布
