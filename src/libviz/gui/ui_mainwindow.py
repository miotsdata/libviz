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
    QStatusBar, QToolBar, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(770, 694)
        self.actionLoad_library = QAction(MainWindow)
        self.actionLoad_library.setObjectName(u"actionLoad_library")
        self.actionCreate_library = QAction(MainWindow)
        self.actionCreate_library.setObjectName(u"actionCreate_library")
        self.actionCreate_library_toolbar = QAction(MainWindow)
        self.actionCreate_library_toolbar.setObjectName(u"actionCreate_library_toolbar")
        icon = QIcon(QIcon.fromTheme(u"document-new"))
        self.actionCreate_library_toolbar.setIcon(icon)
        self.actionCreate_library_toolbar.setMenuRole(QAction.MenuRole.NoRole)
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

        self.horizontalSpacer_3 = QSpacerItem(20, 20, QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)

        self.createLibraryBrowse_btn = QPushButton(self.frame)
        self.createLibraryBrowse_btn.setObjectName(u"createLibraryBrowse_btn")

        self.horizontalLayout_3.addWidget(self.createLibraryBrowse_btn)


        self.verticalLayout.addWidget(self.frame)

        self.createLibraryError_frame = QFrame(self.CreateLibrary_page)
        self.createLibraryError_frame.setObjectName(u"createLibraryError_frame")
        self.createLibraryError_frame.setEnabled(True)
        self.createLibraryError_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.createLibraryError_frame.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.createLibraryError_frame)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.createLibraryError_label = QLabel(self.createLibraryError_frame)
        self.createLibraryError_label.setObjectName(u"createLibraryError_label")
        self.createLibraryError_label.setEnabled(True)
        self.createLibraryError_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.createLibraryError_label)


        self.verticalLayout.addWidget(self.createLibraryError_frame)

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
        self.Library_page = QWidget()
        self.Library_page.setObjectName(u"Library_page")
        self.verticalLayout_4 = QVBoxLayout(self.Library_page)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.frame_6 = QFrame(self.Library_page)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Shadow.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.libraryName_label = QLabel(self.frame_6)
        self.libraryName_label.setObjectName(u"libraryName_label")

        self.horizontalLayout_5.addWidget(self.libraryName_label)

        self.libraryNumberCompounds_label = QLabel(self.frame_6)
        self.libraryNumberCompounds_label.setObjectName(u"libraryNumberCompounds_label")

        self.horizontalLayout_5.addWidget(self.libraryNumberCompounds_label)

        self.libraryNumberSpectra_label = QLabel(self.frame_6)
        self.libraryNumberSpectra_label.setObjectName(u"libraryNumberSpectra_label")

        self.horizontalLayout_5.addWidget(self.libraryNumberSpectra_label)


        self.verticalLayout_4.addWidget(self.frame_6)

        self.frame_5 = QFrame(self.Library_page)
        self.frame_5.setObjectName(u"frame_5")
        self.frame_5.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout_4.addWidget(self.frame_5)

        self.frame_4 = QFrame(self.Library_page)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout_4.addWidget(self.frame_4)

        self.frame_3 = QFrame(self.Library_page)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Shadow.Raised)

        self.verticalLayout_4.addWidget(self.frame_3)

        self.stackedWidget.addWidget(self.Library_page)
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
        self.toolBar = QToolBar(MainWindow)
        self.toolBar.setObjectName(u"toolBar")
        MainWindow.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolBar)

        self.menubar.addAction(self.menuLibrary.menuAction())
        self.menuLibrary.addAction(self.actionLoad_library)
        self.menuLibrary.addAction(self.actionCreate_library)
        self.toolBar.addAction(self.actionCreate_library_toolbar)

        self.retranslateUi(MainWindow)

        self.stackedWidget.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionLoad_library.setText(QCoreApplication.translate("MainWindow", u"Load library", None))
        self.actionCreate_library.setText(QCoreApplication.translate("MainWindow", u"Create library", None))
        self.actionCreate_library_toolbar.setText(QCoreApplication.translate("MainWindow", u"Create library", None))
#if QT_CONFIG(tooltip)
        self.actionCreate_library_toolbar.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Create library</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(shortcut)
        self.actionCreate_library_toolbar.setShortcut(QCoreApplication.translate("MainWindow", u"Backspace", None))
#endif // QT_CONFIG(shortcut)
        self.label.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.createLibraryBrowse_btn.setText(QCoreApplication.translate("MainWindow", u"Save as", None))
        self.createLibraryError_label.setText(QCoreApplication.translate("MainWindow", u"A file with this name already exists.", None))
        self.createLibraryCancel_btn.setText(QCoreApplication.translate("MainWindow", u"Cancel", None))
        self.createLibrarySave_btn.setText(QCoreApplication.translate("MainWindow", u"Next", None))
        self.libraryName_label.setText(QCoreApplication.translate("MainWindow", u"Name: ", None))
        self.libraryNumberCompounds_label.setText(QCoreApplication.translate("MainWindow", u"Number of compounds:", None))
        self.libraryNumberSpectra_label.setText(QCoreApplication.translate("MainWindow", u"Number of spectra:", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Welcome", None))
        self.menuLibrary.setTitle(QCoreApplication.translate("MainWindow", u"Library", None))
        self.toolBar.setWindowTitle(QCoreApplication.translate("MainWindow", u"toolBar", None))
    # retranslateUi

