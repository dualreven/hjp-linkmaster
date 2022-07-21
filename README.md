# hjp-bilink

# hjp-bilink 是一款anki的链接增强插件

支持 2.1.45开始到最新版anki

## 目前支持的主要功能:

1 文内卡片链接: 

将卡片A以链接形式插入到另一张卡片B的正文中, 

操作: 复制卡片为一段链接代码, 粘贴到其他卡片的上下文中, 浏览该卡片看到相关链接即可点击打开.

2 文外卡片链接: 

将卡片A 以不干涉卡片B 正文的方式插入到卡片B中

操作: 选中多张卡片建立链接, 链接信息保存在外部数据库, 浏览卡片即可看到左上角的对应链接

3 视图: 

在视图中直观地展示不同卡片关系, 可以建立视图中的链接, 不同于以上提到的

操作: 选中多张卡片, 新建一个视图, 在视图中对卡片进行连线, 表示关系.

4 PDF页码链接: 

可点击卡片中的pdf链接跳转到对应的pdf和指定的页码.

操作: 复制PDF文件路径, 在编辑卡片的窗口中右键选择插入PDF, 会弹出修改链接属性的窗口, 可以在其中选择要插入的页码, 颜色, 文字描述等, 确认后即可插入到卡片中

5 群组复习:

根据搜索条件, 建立群组, 复习群组中的任意卡片, 就会将整个群组的卡片都一起复习

6 自动提取卡片描述为链接标题:

以上各类卡片链接, 使用统一的卡片描述作为链接标题, 也叫卡片标题.

默认的卡片描述自动提取方式, 是将卡片主体内容全部提取, 可以在设定中修改这个行为, 比如改成根据指定模板的指定字段来提取, 或者提取任意模板的第一段或第二段, 或者你可以提供正则表达式来提取描述.

在提取描述之后, 还可以在卡片信息中手动修改他, 修正为自己想要的卡片标题

## 常见问题
