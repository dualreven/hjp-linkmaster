# PDF卡片的导入,合并与分割
## 导入:
导入是插入页码,浏览时通过pypdf提取图片,加载为html,之后慢慢调整, 默认放在第一个字段

每个页码彼此链接,可以点击翻到上一页或下一页,

文内内的链接格式:(`[[pdf:name:page:beginindex,endindex]]`) 默认情况下都是(0,0),(1,1),百分比.

卡片的合并分割都不会消减原来对应的页面卡片,也就是新增出来.

## 最能提高效率的地方是cliper工具, 

点击打开cliper, 默认读取当前卡片下的那一页, 可以加载其他PDF的其他页, 书页内容会以图片形式显示在正中央

移动到图像上显示为框选, 拉动鼠标记录方框对角坐标, 整个方框可拖拽, 红色框表示问题, 蓝色框表示答案

方框还有数字角标,刚开始是0 ,表示存到第一张卡片, 如果点击了新增,那么就会切换到第二章卡片 

设计插入截图的用法:比起一般的截图方法,这个优势是批量.




## 合并:
合并比较简单, 直接合并卡片内容即可,

卡片链接也会合并为1个, 用户留下的笔记根据对应字段进行合并

## 分割:
分割会复杂一点,

分割时会弹出一个对话框,让你选择分割的方式, 通过绘制矩形,进行分割.

矩形的内容会保存为数据.

### 分割的方式
