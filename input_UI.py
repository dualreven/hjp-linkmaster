# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'inputdialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.2
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_input(object):
    def setupUi(self, input):
        input.setObjectName("input")
        input.setEnabled(True)
        input.resize(500, 300)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(input.sizePolicy().hasHeightForWidth())
        input.setSizePolicy(sizePolicy)
        input.setMinimumSize(QtCore.QSize(500, 300))
        input.setMaximumSize(QtCore.QSize(600, 99999))
        input.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        input.setMouseTracking(False)
        input.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(input)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.verticalLayout.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout.setSpacing(5)
        self.verticalLayout.setObjectName("verticalLayout")
        self.inputTree = QtWidgets.QTreeView(input)
        self.inputTree.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.inputTree.sizePolicy().hasHeightForWidth())
        self.inputTree.setSizePolicy(sizePolicy)
        self.inputTree.setMouseTracking(False)
        self.inputTree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.inputTree.setAcceptDrops(True)
        self.inputTree.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.inputTree.setTabKeyNavigation(True)
        self.inputTree.setDragEnabled(True)
        self.inputTree.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.inputTree.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.inputTree.setAlternatingRowColors(True)
        self.inputTree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.inputTree.setSortingEnabled(False)
        self.inputTree.setAnimated(True)
        self.inputTree.setObjectName("inputTree")
        self.inputTree.header().setCascadingSectionResizes(True)
        self.inputTree.header().setDefaultSectionSize(210)
        self.inputTree.header().setHighlightSections(True)
        self.inputTree.header().setSortIndicatorShown(False)
        self.verticalLayout.addWidget(self.inputTree)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(8)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.line = QtWidgets.QFrame(input)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.horizontalLayout_2.addWidget(self.line)
        self.label = QtWidgets.QLabel(input)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.tagContent = QtWidgets.QLineEdit(input)
        self.tagContent.setObjectName("tagContent")
        self.horizontalLayout_2.addWidget(self.tagContent)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.info = QtWidgets.QLabel(input)
        self.info.setWordWrap(True)
        self.info.setObjectName("info")
        self.verticalLayout.addWidget(self.info)
        self.verticalLayout.setStretch(0, 1)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(input)
        QtCore.QMetaObject.connectSlotsByName(input)

    def retranslateUi(self, input):
        _translate = QtCore.QCoreApplication.translate
        input.setWindowTitle(_translate("input", "input"))
        self.label.setText(_translate("input", "tag:"))
        self.info.setText(_translate("input", "注:pair可拖拽,可多选,最底层的desc可修改,右键执行连接或关闭窗口会保存数据.有小概率会出bug"))
