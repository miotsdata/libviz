# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mainwindow.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(770, 694)
        self.actionLoad_library = QAction(MainWindow)
        self.actionLoad_library.setObjectName(u"actionLoad_library")
        self.actionCreate_library = QAction(MainWindow)
        self.actionCreate_library.setObjectName(u"actionCreate_library")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.stackedWidget = QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.CreateLibrary_page = QWidget()
        self.CreateLibrary_page.setObjectName(u"CreateLibrary_page")
        self.verticalLayout = QVBoxLayout(self.CreateLibrary_page)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.CreateLibrary_page)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.horizontalSpacer_2 = QSpacerItem(20, 20, QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.createLibraryName_lineEdit = QLineEdit(self.CreateLibrary_page)
        self.createLibraryName_lineEdit.setObjectName(u"createLibraryName_lineEdit")

        self.horizontalLayout.addWidget(self.createLibraryName_lineEdit)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.frame = QFrame(self.CreateLibrary_page)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.createLibraryPath_lineEdit = QLineEdit(self.frame)
        self.createLibraryPath_lineEdit.setObjectName(u"createLibraryPath_lineEdit")

        self.horizontalLayout_3.addWidget(self.createLibraryPath_lineEdit)

        self.createLibraryBrowse_btn = QPushButton(self.frame)
        self.createLibraryBrowse_btn.setObjectName(u"createLibraryBrowse_btn")

        self.horizontalLayout_3.addWidget(self.createLibraryBrowse_btn)


        self.verticalLayout.addWidget(self.frame)

        self.frame_2 = QFrame(self.CreateLibrary_page)
        self.frame_2.setObjectName(u"frame_2")
        self.frame_2.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.createLibraryCancel_btn = QPushButton(self.frame_2)
        self.createLibraryCancel_btn.setObjectName(u"createLibraryCancel_btn")

        self.horizontalLayout_4.addWidget(self.createLibraryCancel_btn)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.createLibrarySave_btn = QPushButton(self.frame_2)
        self.createLibrarySave_btn.setObjectName(u"createLibrarySave_btn")
        self.createLibrarySave_btn.setEnabled(False)

        self.horizontalLayout_4.addWidget(self.createLibrarySave_btn)


        self.verticalLayout.addWidget(self.frame_2)

        self.stackedWidget.addWidget(self.CreateLibrary_page)
        self.Home_page = QWidget()
        self.Home_page.setObjectName(u"Home_page")
        self.horizontalLayout_2 = QHBoxLayout(self.Home_page)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(self.Home_page)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.horizontalLayout_2.addWidget(self.label_2)

        self.stackedWidget.addWidget(self.Home_page)

        self.verticalLayout_2.addWidget(self.stackedWidget)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 770, 24))
        self.menuLibrary = QMenu(self.menubar)
        self.menuLibrary.setObjectName(u"menuLibrary")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuLibrary.menuAction())
        self.menuLibrary.addAction(self.actionLoad_library)
        self.menuLibrary.addAction(self.actionCreate_library)

        self.retranslateUi(MainWindow)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionLoad_library.setText(QCoreApplication.translate("MainWindow", u"Load library", None))
        self.actionCreate_library.setText(QCoreApplication.translate("MainWindow", u"Create library", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.createLibraryBrowse_btn.setText(QCoreApplication.translate("MainWindow", u"Save as", None))
        self.createLibraryCancel_btn.setText(QCoreApplication.translate("MainWindow", u"Cancel", None))
        self.createLibrarySave_btn.setText(QCoreApplication.translate("MainWindow", u"Next", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Welcome", None))
        self.menuLibrary.setTitle(QCoreApplication.translate("MainWindow", u"Library", None))
    # retranslateUi

