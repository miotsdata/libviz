# Resource object code (Python 3)
# Created by: object code
# Created by: The Resource Compiler for Qt version 6.10.2
# WARNING! All changes made in this file will be lost!

from PySide6 import QtCore

qt_resource_data = b"\
\x00\x00\x0d\x89\
/\
/ qml/main.qml\x0ai\
mport QtQuick\x0aim\
port QtQuick.Con\
trols\x0aimport QtQ\
uick.Layouts\x0aimp\
ort QtQuick.Dial\
ogs\x0a\x0aimport Libv\
iz.Pages 1.0\x0a\x0aAp\
plicationWindow \
{\x0a    id: window\
\x0a    visible: tr\
ue\x0a    width: 10\
24\x0a    height: 6\
80\x0a    minimumWi\
dth: 800\x0a    min\
imumHeight: 560\x0a\
    title: \x22LibV\
iz\x22\x0a\x0a    // ====\
================\
=====\x0a    // MEN\
U BAR\x0a    // ===\
================\
======\x0a\x0a    menu\
Bar: MenuBar {\x0a\x0a\
        Menu {\x0a \
           title\
: qsTr(\x22Library\x22\
)\x0a\x0a            M\
enuItem {\x0a      \
          text: \
qsTr(\x22Create lib\
rary\x22)\x0a         \
       onTrigger\
ed: { /* TODO */\
 }\x0a            }\
\x0a\x0a            Me\
nuSeparator {}\x0a\x0a\
            Menu\
Item {\x0a         \
       text: qsT\
r(\x22Load from .ms\
p\xe2\x80\xa6\x22)\x0a         \
       onTrigger\
ed: mspFileDialo\
g.open()\x0a       \
     }\x0a\x0a        \
    MenuItem {\x0a \
               t\
ext: qsTr(\x22Load \
from .db\xe2\x80\xa6\x22)\x0a  \
              on\
Triggered: { /* \
TODO */ }\x0a      \
      }\x0a        \
}\x0a\x0a        Menu \
{\x0a            ti\
tle: qsTr(\x22Inser\
t\x22)\x0a\x0a           \
 MenuItem {\x0a    \
            text\
: qsTr(\x22Spectra \
from .mzml\xe2\x80\xa6\x22)\x0a\
                \
enabled: false  \
 // enabled once\
 a library is op\
en\x0a             \
   onTriggered: \
{ /* TODO */ }\x0a \
           }\x0a   \
     }\x0a\x0a        \
Menu {\x0a         \
   title: qsTr(\x22\
Save\x22)\x0a\x0a        \
    MenuItem {\x0a \
               t\
ext: qsTr(\x22Save \
as .db\xe2\x80\xa6\x22)\x0a    \
            enab\
led: false   // \
enabled once a l\
ibrary is open\x0a \
               o\
nTriggered: { /*\
 TODO */ }\x0a     \
       }\x0a       \
 }\x0a    }\x0a\x0a    //\
 ===============\
==========\x0a    /\
/ MAIN CONTENT\x0a \
   // ==========\
===============\x0a\
\x0a    StackView {\
\x0a        id: sta\
ck\x0a        ancho\
rs.fill: parent\x0a\
        initialI\
tem: WelcomePage\
 {}\x0a    }\x0a\x0a\x0a    \
// =============\
============\x0a   \
 // STATUS BAR\x0a \
   // ==========\
===============\x0a\
\x0a    footer: Too\
lBar {\x0a        i\
d: statusBar\x0a   \
     visible: st\
atusText.text !=\
= \x22\x22\x0a        hei\
ght: visible ? i\
mplicitHeight : \
0\x0a\x0a        RowLa\
yout {\x0a         \
   anchors.fill:\
 parent\x0a        \
    anchors.left\
Margin: 12\x0a     \
       anchors.r\
ightMargin: 12\x0a \
           spaci\
ng: 12\x0a\x0a        \
    Text {\x0a     \
           id: s\
tatusText\x0a      \
          Layout\
.fillWidth: true\
\x0a               \
 elide: Text.Eli\
deRight\x0a        \
        vertical\
Alignment: Text.\
AlignVCenter\x0a   \
             fon\
t.pixelSize: 12\x0a\
                \
color: \x22#444444\x22\
\x0a            }\x0a\x0a\
            Busy\
Indicator {\x0a    \
            id: \
busyIndicator\x0a  \
              ru\
nning: statusTex\
t.text !== \x22\x22\x0a  \
              wi\
dth: 20\x0a        \
        height: \
20\x0a            }\
\x0a        }\x0a    }\
\x0a\x0a    Connection\
s {\x0a        targ\
et: libraryManag\
erBridge\x0a\x0a      \
  function onSta\
tusChanged(messa\
ge) {\x0a          \
  statusText.tex\
t = message\x0a    \
    }\x0a\x0a        f\
unction onErrorO\
ccurred(message)\
 {\x0a            e\
rrorDialog.error\
Text = message\x0a \
           error\
Dialog.open()\x0a  \
      }\x0a\x0a       \
 function onLibr\
aryLoaded(path) \
{\x0a            pr\
int(\x22Library loa\
ded:\x22, path)\x0a   \
         var com\
ponent = Qt.crea\
teComponent(\x22qrc\
:/gui/Libviz/Pag\
es/LibraryHomePa\
ge.qml\x22)\x0a       \
     print(\x22Comp\
onent status:\x22, \
component.status\
)\x0a            pr\
int(\x22Component e\
rror:\x22, componen\
t.errorString())\
\x0a            sta\
ck.clear()\x0a     \
       stack.pus\
h(component)\x0a   \
     }\x0a    }\x0a\x0a  \
  Dialog {\x0a     \
   id: errorDial\
og\x0a        prope\
rty alias errorT\
ext: errorLabel.\
text\x0a        tit\
le: \x22Error\x22\x0a    \
    Label { id: \
errorLabel }\x0a   \
     standardBut\
tons: Dialog.Ok\x0a\
    }\x0a\x0a    FileD\
ialog {\x0a        \
id: mspFileDialo\
g\x0a        title:\
 qsTr(\x22Select .m\
sp file\x22)\x0a      \
  nameFilters: [\
\x22MSP files (*.ms\
p)\x22, \x22All files \
(*)\x22]\x0a        on\
Accepted: librar\
yManagerBridge.l\
oadLibraryFromMs\
p(selectedFile)\x0a\
    }\x0a}\x0a\
\x00\x00\x00\x5c\
m\
odule Libviz.Pag\
es\x0a\x0aWelcomePage \
1.0 WelcomePage.\
qml\x0aLibraryHomeP\
age 1.0 LibraryH\
omePage.qml\
\x00\x00\x01\xd3\
\x00\
\x00\x07\xfdx\xda\xd5SQo\xda0\x10~\xcf\xaf\xb0\
\xa8&m{pB\xcb\xd0@\xea\xc3V\x15\xb5R\xa7\
\xad\xb4Z\x9fC8\xc8\xa9\x8e\x9d\x1d\xc7\xe8\x98\xf8\xef\
\xbb$\xc4\x220\xd4M\x83I\xf5\x93\xcf\xf7\xdd\xf9\xbe\
\xcf\xfe\xc2P\xdd\xe0\xe8;.\xc3/\xf1\x14f\xa1\x04\
\x14\xd3\x8f+\x97Aq\xa0\xbfe&\xc0,w\xc4\xea\
\x96o\xe7\x98<n\x85\xfa\xc2Y&gf\xfb\xce\xf5\
\xa7\x98\x8106Ap\xcd\x90\xa9\x9f\x81\x92\x85\xe3\xbe\
\x22\xe78(\xa30T\xe7\xfbV\x0d\x18~~Pm\
\xa5^w\xa2W*\x05\x9c\xa6\xfc\xe6\xf9\xda\x12q\x97\
\x1b\xe4\xaf\x08\x8b\xf5\xdd\xf5\xfd\xec\xf2\xa1[\xf8#G\
\x08\x96cFg\xfb\xc2B_\xc9\xc1RH\xc8\xe45\
$\xb6I\xeah\xb6\xd1\xa7X\xd2\xa7\xaf\xf2\x98\xa4Z\
\xcb\xbe\x9130a\x9f,\x82F\x96\x0a\x1a>]F\
>\xbf\xf2\xbb\x8a\xad\x87U\xa1z\xab\x22\xdd\x09<h\
\x08\x09\xc7vj`k8O^\xe7\x04\x13 \x82\xf1\
\x03\x8e9\xad\xe9\xebE\x11\x95\xdd\xce\xf6\x14fh1\
\x9bg\xeb\xb2v\x145p\x893\x8e\xfa\xaau\xd2\xb9\
\xf80x\x17\xb5\xaa'\x99\x12\x80\x0d\x1a\xc0{x\xe2\
\xad\xe164\xd5\x89p\x03\xba\xb65\xcf\x1d K\xbd\
\xdcs\xefru#B\xb6v\x00\xf5$\x8b\x14\x19v\
\xd3\x13yK\x9d\xe3\x13\x98;\x5c\x82\x10\xe94 \xab\
\x0d\xe5\xffB\xd5\x09\x1aS\x0bJs\xf8\xbd4\xa7\xed\
^wp\xb6\x96fd\x04v,e\x86\xc5\xdf8\xa6\
4\x1b\x02\xfd\xa9kO\xc5\xb5\xdd\x83\xb9v\xe4\x98]\
v8\xe3\xaemP\xb5=\x90w\x8bU5\xf4\x80\xad\
\xfe\xab\x7fq\xae\x97\xe0p\xe6\x1d\x0cz\xef\xa3\xda\xbc\
\x8ed\x9e\xe3\xfc\xd1\x8f\xe5\xe8/\xce\xc0\x97\xbd\xf6e\
\xb76p\x8e\xf6\xf1\x98\xe2\xfc'\x0f\xaf\x82_R|\
\x04\xbf\
\x00\x00\x02v\
/\
/ gui/qml/pages/\
WelcomePage.qml\x0a\
import QtQuick\x0ai\
mport QtQuick.Co\
ntrols\x0aimport Qt\
Quick.Controls.M\
aterial\x0a\x0aItem {\x0a\
\x0a    Column {\x0a  \
      anchors.ce\
nterIn: parent\x0a \
       spacing: \
16\x0a\x0a        Text\
 {\x0a            a\
nchors.horizonta\
lCenter: parent.\
horizontalCenter\
\x0a            tex\
t: \x22LibViz\x22\x0a    \
        font.pix\
elSize: 48\x0a     \
       font.weig\
ht: Font.Light\x0a \
           color\
: Material.foreg\
round\x0a        }\x0a\
\x0a        Text {\x0a\
            anch\
ors.horizontalCe\
nter: parent.hor\
izontalCenter\x0a  \
          text: \
\x22Open or create \
a library to get\
 started\x22\x0a      \
      font.pixel\
Size: 14\x0a       \
     color: Mate\
rial.hintTextCol\
or\x0a        }\x0a   \
 }\x0a}\x0a\
"

qt_resource_name = b"\
\x00\x03\
\x00\x00n\xb9\
\x00g\
\x00u\x00i\
\x00\x06\
\x05/\x9d\x0a\
\x00L\
\x00i\x00b\x00v\x00i\x00z\
\x00\x08\
\x08\x01Z\x5c\
\x00m\
\x00a\x00i\x00n\x00.\x00q\x00m\x00l\
\x00\x05\
\x00V}\xc3\
\x00P\
\x00a\x00g\x00e\x00s\
\x00\x06\
\x07\x84+\x02\
\x00q\
\x00m\x00l\x00d\x00i\x00r\
\x00\x13\
\x07\xc6\x04\x1c\
\x00L\
\x00i\x00b\x00r\x00a\x00r\x00y\x00H\x00o\x00m\x00e\x00P\x00a\x00g\x00e\x00.\x00q\
\x00m\x00l\
\x00\x0f\
\x02\x9dW\xfc\
\x00W\
\x00e\x00l\x00c\x00o\x00m\x00e\x00P\x00a\x00g\x00e\x00.\x00q\x00m\x00l\
"

qt_resource_struct = b"\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x02\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x0c\x00\x02\x00\x00\x00\x01\x00\x00\x00\x04\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x1e\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\
\x00\x00\x01\x9d\x1a\xf9\x96R\
\x00\x00\x004\x00\x02\x00\x00\x00\x03\x00\x00\x00\x05\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00\x82\x00\x00\x00\x00\x00\x01\x00\x00\x0f\xc4\
\x00\x00\x01\x9d\x01<\xd0\x80\
\x00\x00\x00D\x00\x00\x00\x00\x00\x01\x00\x00\x0d\x8d\
\x00\x00\x01\x9d\x1a\xdft'\
\x00\x00\x00V\x00\x01\x00\x00\x00\x01\x00\x00\x0d\xed\
\x00\x00\x01\x9d\x1a\xdec\xb4\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()
