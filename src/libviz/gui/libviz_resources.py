# Resource object code (Python 3)
# Created by: object code
# Created by: The Resource Compiler for Qt version 6.10.2
# WARNING! All changes made in this file will be lost!

from PySide6 import QtCore

qt_resource_data = b"\
\x00\x00\x0cm\
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
er\x0a\x0a        func\
tion onStatusCha\
nged(message) {\x0a\
            stat\
usText.text = me\
ssage\x0a        }\x0a\
\x0a        functio\
n onErrorOccurre\
d(message) {\x0a   \
         errorDi\
alog.errorText =\
 message\x0a       \
     errorDialog\
.open()\x0a        \
}\x0a\x0a        funct\
ion onLibraryLoa\
ded(path) {\x0a    \
        print(\x22L\
ibrary loaded:\x22,\
 path)\x0a        }\
\x0a    }\x0a\x0a    Dial\
og {\x0a        id:\
 errorDialog\x0a   \
     property al\
ias errorText: e\
rrorLabel.text\x0a \
       title: \x22E\
rror\x22\x0a        La\
bel { id: errorL\
abel }\x0a        s\
tandardButtons: \
Dialog.Ok\x0a    }\x0a\
\x0a    FileDialog \
{\x0a        id: ms\
pFileDialog\x0a    \
    title: qsTr(\
\x22Select .msp fil\
e\x22)\x0a        name\
Filters: [\x22MSP f\
iles (*.msp)\x22, \x22\
All files (*)\x22]\x0a\
        onAccept\
ed: libraryManag\
er.loadLibraryFr\
omMsp(selectedFi\
le)\x0a    }\x0a}\x0a\
\x00\x00\x005\
m\
odule Libviz.Pag\
es\x0a\x0aWelcomePage \
1.0 WelcomePage.\
qml\x0a\
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
\x00\x00\x01\x9d\x01\xb9=\xe6\
\x00\x00\x004\x00\x02\x00\x00\x00\x02\x00\x00\x00\x05\
\x00\x00\x00\x00\x00\x00\x00\x00\
\x00\x00\x00V\x00\x00\x00\x00\x00\x01\x00\x00\x0c\xaa\
\x00\x00\x01\x9d\x01<\xd0\x80\
\x00\x00\x00D\x00\x00\x00\x00\x00\x01\x00\x00\x0cq\
\x00\x00\x01\x9d\x01<\xd0\x80\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x03, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()
