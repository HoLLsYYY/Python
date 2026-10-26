"""A hand-delivered letter and a persistent, folded-paper note in the screen corner."""
import math,time
from dataclasses import dataclass
from PySide6.QtCore import Qt,QTimer,QPointF,QRectF,Signal
from PySide6.QtGui import (QColor,QPen,QPainter,QPainterPath,QPixmap,QFont,QFontMetricsF,
                          QTextLayout,QTextOption,QTransform,QPolygonF,QRegion)
from PySide6.QtWidgets import (QWidget,QApplication,QDialog,QVBoxLayout,QHBoxLayout,
                              QLabel,QPlainTextEdit,QPushButton)
from protocol import LETTER_LIMIT,canonical_letter,validate_letter

INK=QColor('#59342c')
PAPER=QColor('#fff9ef')
CREAM=QColor('#ffeddf')
PINK=QColor('#e887a1')
VISIT_ACTION_DURATION=4.1
HANDOFF_TIME=3.0
CARD_DURATION=4.85
READ_SECONDS=22.0
DISMISS_DURATION=.32
CARD_ANGLE=-20.0
LETTER_WIDTH=82.0
HANDOFF_WIDTH=LETTER_WIDTH*1.15
HANDOFF_Y=143.0
NOTE_RECT=QRectF(-105,-92.5,210,185)
BODY_RECT=QRectF(-88,-45,176,119)
CLOSE_RECT=QRectF(85,-84,15,15)
READ_RECT=QRectF(-65,102.5,130,25)

def clamp(value):return max(0.,min(1.,value))
def ease(value):value=clamp(value);return value*value*(3-2*value)
def mix(a,b,u):return a+(b-a)*u

def heart(p,center,size=12,opacity=1):
    p.save();p.setOpacity(p.opacity()*opacity);p.translate(center);p.scale(size/12,size/12)
    shape=QPainterPath(QPointF(0,11));shape.cubicTo(-3,7,-16,-1,-11,-8);shape.cubicTo(-8,-13,-2,-12,0,-6);shape.cubicTo(2,-12,8,-13,11,-8);shape.cubicTo(16,-1,3,7,0,11)
    p.setPen(QPen(QColor('#bd5b78'),1.4));p.setBrush(PINK);p.drawPath(shape)
    p.setPen(QPen(QColor('#ffc5d4'),1.5,Qt.SolidLine,Qt.RoundCap));p.drawLine(QPointF(-7,-6),QPointF(-5,-8));p.restore()

def envelope_back(p,opening=0,stroke=2.4):
    p.setPen(QPen(INK,stroke,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(CREAM)
    p.drawRoundedRect(QRectF(-120,-80,240,160),5,5)
    if opening>.5:
        flap=QPainterPath(QPointF(-120,-80));flap.lineTo(0,-80+100*math.cos(math.pi*opening));flap.lineTo(120,-80);flap.closeSubpath()
        p.setBrush(QColor('#f8dce0'));p.drawPath(flap)
        p.setPen(QPen(QColor('#d9aaac'),1));p.drawLine(QPointF(-116,-78),QPointF(116,-78))

def envelope_front(p,opening=0,seal=1,stroke=2.4):
    front=QPainterPath(QPointF(-120,-80));front.lineTo(0,16);front.lineTo(120,-80);front.lineTo(120,80);front.lineTo(-120,80);front.closeSubpath()
    p.setPen(QPen(INK,stroke,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(QColor('#ffe5da'));p.drawPath(front)
    p.setPen(QPen(QColor('#c9948b'),1.2,Qt.SolidLine,Qt.RoundCap));p.drawLine(QPointF(-117,77),QPointF(-18,2));p.drawLine(QPointF(117,77),QPointF(18,2))
    if opening<=.5:
        flap=QPainterPath(QPointF(-120,-80));flap.lineTo(0,-80+100*math.cos(math.pi*opening));flap.lineTo(120,-80);flap.closeSubpath()
        p.setPen(QPen(INK,stroke,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(QColor('#f8d3dc'));p.drawPath(flap)
    if seal>0:heart(p,QPointF(0,15-(1-seal)*35),13*(1+.08*math.sin((1-seal)*math.pi)),seal)

def sealed_envelope(p,width=LETTER_WIDTH):
    p.save();p.scale(width/240,width/240);stroke=max(2.4,1.8/(width/240));envelope_back(p,stroke=stroke);envelope_front(p,stroke=stroke);p.restore()

@dataclass(frozen=True)
class HeldPose:
    y:float
    scale:float
    tilt:float
    opacity:float
    hand_release:float

def held_pose(t):
    if t<.6:return HeldPose(mix(161,138,ease(t/.6)),mix(.8,1,ease(t/.6)),0,ease(t/.18),0)
    if t<1.9:
        u=(t-.6)/1.3;return HeldPose(138+math.sin(u*2*math.pi)*.4,1,1.1*math.sin(u*2*math.pi)*math.sin(u*math.pi),1,0)
    if t<2.15:
        wind=math.sin(math.pi*(t-1.9)/.25)**2;return HeldPose(138-2*wind,1-.025*wind,0,1,0)
    if t<HANDOFF_TIME:
        u=ease((t-2.15)/.85);return HeldPose(mix(138,HANDOFF_Y,u),mix(1,1.15,u),0,1,0)
    return HeldPose(HANDOFF_Y,1.15,0,0,ease((t-HANDOFF_TIME)/.55))

class LetterPose:
    """Original fixed bear artwork with a separate envelope and articulated arms."""
    def __init__(self,assets):
        self.body=QPixmap(str(assets/'canonical-reference.png'))
        self.head=self.body.copy(0,0,200,116)
        p=QPainter(self.body);p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_Clear);p.fillRect(QRectF(45,115,110,40),Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        torso=QPainterPath(QPointF(80,110));torso.quadTo(73,128,75,155);torso.lineTo(126,155);torso.quadTo(128,128,120,110);torso.closeSubpath();p.fillPath(torso,QColor('#fffefe'))
        p.setPen(QPen(QColor('#48251f'),4.2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        sides=QPainterPath(QPointF(80,114));sides.quadTo(73,131,75,155);sides.moveTo(120,114);sides.quadTo(128,131,126,155);p.drawPath(sides)
        p.setCompositionMode(QPainter.CompositionMode_Clear);p.fillRect(QRectF(0,0,200,110),Qt.transparent);p.end()
    @staticmethod
    def arm(p,shoulder,wrist,left,t):
        # A curved, tapered silhouette: a soft shoulder narrows toward the paw.
        bend=QPointF(shoulder.x()+(-7 if left else 7),mix(shoulder.y(),wrist.y(),.7)+2+math.sin(t*3+(0 if left else .6))*.5)
        edges=[[],[]]
        for i in range(13):
            u=i/12;v=1-u;point=shoulder*(v*v)+bend*(2*v*u)+wrist*(u*u)
            tangent=(bend-shoulder)*(2*v)+(wrist-bend)*(2*u);length=max(.01,math.hypot(tangent.x(),tangent.y()))
            normal=QPointF(-tangent.y()/length,tangent.x()/length);radius=(mix(13,7.5,u)+1.2*math.sin(math.pi*u))/2
            edges[0].append(point+normal*radius);edges[1].append(point-normal*radius)
        shape=QPainterPath(edges[0][0])
        for point in edges[0][1:]:shape.lineTo(point)
        for point in reversed(edges[1]):shape.lineTo(point)
        shape.closeSubpath();p.setPen(QPen(QColor('#48251f'),3.2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(QColor('#fffefe'));p.drawPath(shape)
    def paint(self,p,t,x=60,y=70):
        state=held_pose(t);p.save();p.translate(x,y)
        lean=1.1*math.sin(math.pi*clamp((t-2.15)/.85)) if 2.15<t<HANDOFF_TIME else 0
        p.translate(100,186);p.rotate(lean);p.translate(-100,-186)
        spread=mix(34,36,clamp((state.scale-1)/.15));hands=[]
        for left in [True,False]:
            delay=0 if left else .055
            if t<.7:grip=1-ease((t-delay)/.6)
            elif t>=HANDOFF_TIME:grip=ease((t-HANDOFF_TIME-delay)/(.52 if left else .59))
            else:grip=0
            sign=-1 if left else 1;target_y=min(144.5,state.y+sign*1.5)
            hand=QPointF(mix(100+sign*spread,71 if left else 131,grip),mix(target_y,144,grip));hands.append(hand)
            self.arm(p,QPointF(80 if left else 122,123),hand,left,t)
        p.drawPixmap(0,0,self.body)
        nod=ease(t/.5)*(1-ease((t-2.15)/.85));p.save();p.translate(100,111+nod*.8);p.rotate(-1.1*nod);p.translate(-100,-111);p.drawPixmap(0,0,self.head)
        if 1.03<t<1.22:
            blink=math.sin(math.pi*(t-1.03)/.19)**2
            for rect in [QRectF(60,78,15,15),QRectF(108,78,16,16)]:
                p.save();clip=QPainterPath();clip.addEllipse(rect.adjusted(-.4,-.4,.4,.4));p.setClipPath(clip);p.setPen(Qt.NoPen);p.setBrush(QColor('#fffefe'));p.drawEllipse(rect.adjusted(-.4,-.4,.4,.4))
                target=QRectF(rect.left(),rect.center().y()-rect.height()*(1-.94*blink)/2,rect.width(),rect.height()*(1-.94*blink));p.drawPixmap(target,self.head,rect);p.restore()
        p.restore()
        if state.opacity:
            p.save();p.setOpacity(state.opacity);p.translate(100,state.y);p.rotate(state.tilt);sealed_envelope(p,LETTER_WIDTH*state.scale);p.restore()
        for hand in hands:
            radius=mix(10*min(1.08,state.scale),7,state.hand_release)
            p.setPen(QPen(QColor('#48251f'),3));p.setBrush(QColor('#fffefe'));p.drawEllipse(hand,radius,radius)
        p.restore();return state

@dataclass(frozen=True)
class CardPose:
    x:float
    y:float
    scale:float
    angle:float
    opening:float
    seal:float
    note_y:float
    note_scale:float
    note_opacity:float
    note_front:bool
    ready:bool

def card_pose(t,width,height,origin=None,origin_width=HANDOFF_WIDTH):
    fit=min(1.,max(.2,(width-24)/500),max(.2,(height-24)/540))
    tx,ty=width-190*fit,height-145*fit;final_scale=280/240*fit
    ox,oy=origin if origin is not None else (width*.5,height+50)
    u=ease(t/.85);x=mix(ox,tx,u);y=mix(oy,ty,u)-75*fit*math.sin(math.pi*u)
    scale=mix(origin_width/240,final_scale,u);angle=CARD_ANGLE*u
    if .85<t<1.1:
        settle=(t-.85)/.25;y-=3*fit*math.sin(settle*math.pi)**2
    opening=ease((t-1.55)/.7);seal=1-ease((t-1.1)/.65)
    extract=ease((t-2.15)/1.6);lay=ease((t-3.95)/.9)
    note_y=mix(75,-195,extract) if t<3.95 else mix(-195,-65,lay)
    return CardPose(x,y,scale,angle,opening,seal,note_y,1+.02*math.sin(math.pi*lay),ease((t-1.9)/.2),t>=3.95,t>=CARD_DURATION)

class NoteContent:
    def __init__(self,text,pixel_font):
        self.text=validate_letter(text);self.font=QFont(pixel_font);self.font.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
        pieces=[];self.hearts=[];units=0
        for char in self.text:
            if char=='\ufe0f' and pieces and pieces[-1]=='  ':continue
            if char in '♥❤♡':self.hearts.append(units);piece='  '
            else:piece='\u2028' if char=='\n' else char
            pieces.append(piece);units+=len(piece.encode('utf-16-le'))//2
        self.layout_text=''.join(pieces);self.unit_indices={};units=0
        for i,char in enumerate(self.layout_text):self.unit_indices[units]=i;units+=len(char.encode('utf-16-le'))//2
        self.unit_indices[units]=len(self.layout_text)
        for size in (12,11,10):
            self.font.setPixelSize(size);self.layout=QTextLayout(self.layout_text,self.font)
            option=QTextOption();option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere);self.layout.setTextOption(option)
            self.layout.beginLayout();y=BODY_RECT.top();self.lines=[]
            while True:
                line=self.layout.createLine()
                if not line.isValid():break
                line.setLineWidth(BODY_RECT.width());line.setPosition(QPointF(BODY_RECT.left(),y));self.lines.append(line)
                y+=max(line.height()+2,size+3)
            self.layout.endLayout()
            self.height=(self.lines[-1].y()+self.lines[-1].height()-BODY_RECT.top()) if self.lines else 0
            if self.height<=BODY_RECT.height():break
        self.max_scroll=max(0,self.height-BODY_RECT.height());self.scroll=0
    def paint(self,p,ready=False,hover=False,pressed=False,controls=None):
        p.save();p.setPen(Qt.NoPen);p.setBrush(QColor(70,38,34,28));p.drawRoundedRect(NOTE_RECT.translated(3,5),3,3)
        p.setPen(QPen(INK,1.5));p.setBrush(PAPER);p.drawRoundedRect(NOTE_RECT,3,3)
        fold=QPainterPath(QPointF(-104,-91.5));fold.lineTo(-91,-91.5);fold.lineTo(-104,-78.5);fold.closeSubpath();p.fillPath(fold,QColor('#f7dfd1'))
        header=QFont(self.font);header.setPixelSize(14);p.setFont(header);p.setPen(INK)
        p.drawText(QRectF(-70,-80,140,22),Qt.AlignCenter,'Для тебя')
        rows=['0110110','1111111','1111111','0111110','0011100','0001000']
        p.setPen(Qt.NoPen);p.setBrush(PINK)
        for row,line in enumerate(rows):
            for col,bit in enumerate(line):
                if bit=='1':p.drawRect(QRectF(-88+col*1.6,-75+row*1.6,1.6,1.6))
        p.setPen(QPen(QColor('#edd0c4'),.8));p.drawLine(QPointF(-88,-51),QPointF(88,-51))
        p.save();p.setClipRect(BODY_RECT,Qt.IntersectClip);p.setPen(INK);p.setRenderHint(QPainter.TextAntialiasing,False);self.layout.draw(p,QPointF(0,-self.scroll))
        p.setPen(Qt.NoPen);p.setBrush(PINK);metrics=QFontMetricsF(self.font);pixel=self.font.pixelSize()/12
        for index in self.hearts:
            line=next((line for line in self.lines if line.textStart()<=index<line.textStart()+line.textLength()),None)
            if line is None:continue
            start=self.unit_indices.get(line.textStart(),0);end=self.unit_indices[index]
            x=BODY_RECT.left()+metrics.horizontalAdvance(self.layout_text[start:end]);y=line.y()+max(0,(line.height()-6*pixel)/2)-self.scroll
            for row,bits in enumerate(rows):
                for col,bit in enumerate(bits):
                    if bit=='1':p.drawRect(QRectF(x+col*pixel,y+row*pixel,pixel,pixel))
        p.restore()
        if self.max_scroll>0:
            p.setPen(Qt.NoPen);p.setBrush(QColor('#e9c1c5'));p.drawRoundedRect(QRectF(94,-43,2,112),1,1)
            thumb=max(12,112*BODY_RECT.height()/self.height);offset=(112-thumb)*self.scroll/self.max_scroll
            p.setBrush(QColor('#b97888'));p.drawRoundedRect(QRectF(94,-43+offset,2,thumb),1,1)
        controls=(1 if ready else 0) if controls is None else controls
        if controls>0:
            p.save();p.setOpacity(p.opacity()*controls)
            if hover=='close':p.setPen(Qt.NoPen);p.setBrush(QColor('#f6d9df'));p.drawEllipse(CLOSE_RECT.adjusted(-2,-2,2,2))
            p.setPen(QPen(QColor('#8b5961'),1.3,Qt.SolidLine,Qt.RoundCap));p.drawLine(CLOSE_RECT.topLeft()+QPointF(4,4),CLOSE_RECT.bottomRight()-QPointF(4,4));p.drawLine(CLOSE_RECT.topRight()+QPointF(-4,4),CLOSE_RECT.bottomLeft()+QPointF(4,-4))
            button=READ_RECT.translated(0,1 if pressed else 0)
            p.setPen(Qt.NoPen);p.setBrush(QColor(70,38,34,28));p.drawRoundedRect(button.translated(1,3),4,4)
            p.setPen(QPen(INK,1.5));p.setBrush(QColor('#f4c6d4' if hover=='read' else '#f8dbe3'));p.drawRoundedRect(button,4,4)
            button_font=QFont(self.font);button_font.setPixelSize(12);p.setFont(button_font);p.setPen(INK);p.drawText(button,Qt.AlignCenter,'Прочитано')
            p.restore()
        p.restore()

class LetterCard(QWidget):
    closed=Signal(object)
    def __init__(self,text,pixel_font,origin=None,origin_width=HANDOFF_WIDTH):
        flags=Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool|Qt.WindowDoesNotAcceptFocus|Qt.WindowTransparentForInput
        super().__init__(None,flags);self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating);self.setAttribute(Qt.WA_DeleteOnClose)
        area=QApplication.primaryScreen().availableGeometry();self.setGeometry(area)
        self.origin=(origin.x()-area.left(),origin.y()-area.top()) if origin is not None else None;self.origin_width=origin_width
        self.content=NoteContent(text,pixel_font);self.started=time.monotonic();self.finished=False;self.hover=False;self.pressed=False;self.note_transform=QTransform();self.closing_started=None;self.read_started=None
        self.setMouseTracking(True);self.setWindowTitle('Письмо от мишки')
        self.timer=QTimer(self);self.timer.setTimerType(Qt.PreciseTimer);self.timer.setSingleShot(True);self.timer.timeout.connect(self.tick);self.next_frame=self.started
        self.read_timer=QTimer(self);self.read_timer.setTimerType(Qt.PreciseTimer);self.read_timer.setSingleShot(True);self.read_timer.timeout.connect(self.dismiss)
        self.show();self.raise_();self.timer.start(0)
    def tick(self):
        now=time.monotonic();self.update()
        if self.closing_started is not None:
            if now-self.closing_started>=DISMISS_DURATION:self.close();return
        elif now-self.started>=CARD_DURATION:
            self.finished=True;self.read_started=now;self.timer.stop();self.read_timer.start(round(READ_SECONDS*1000));self.setWindowFlag(Qt.WindowTransparentForInput,False);self.show();self.raise_();return
        if self.next_frame<now-.1:self.next_frame=now
        self.next_frame+=1/60;self.timer.start(max(1,round((self.next_frame-time.monotonic())*1000)))
    def paintEvent(self,event):
        t=CARD_DURATION if self.finished else time.monotonic()-self.started
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
        fade=ease((time.monotonic()-self.closing_started)/DISMISS_DURATION) if self.closing_started is not None else 0
        p.setOpacity(1-fade);p.translate(0,8*fade)
        state=self.paint_scene(p,t,self.width(),self.height());p.end()
        transform=QTransform();transform.translate(state.x,state.y+8*fade);transform.rotate(state.angle);transform.scale(state.scale,state.scale)
        area=QPolygonF([QPointF(-123,-83),QPointF(123,-83),QPointF(123,83),QPointF(-123,83)])
        region=QRegion(transform.map(area).toPolygon())
        if state.opening>.5:
            flap=QPolygonF([QPointF(-123,-78),QPointF(0,-83+100*math.cos(math.pi*state.opening)),QPointF(123,-78)])
            region=region.united(QRegion(transform.map(flap).toPolygon()))
        if state.note_opacity:
            note=QTransform(transform);note.translate(0,state.note_y);note.scale(state.note_scale,state.note_scale);self.note_transform=note
            poly=QPolygonF([NOTE_RECT.topLeft()+QPointF(-2,-2),NOTE_RECT.topRight()+QPointF(8,-2),NOTE_RECT.bottomRight()+QPointF(8,9),NOTE_RECT.bottomLeft()+QPointF(-2,9)])
            region=region.united(QRegion(note.map(poly).toPolygon()))
            if state.ready:
                button=READ_RECT.adjusted(-3,-3,4,6)
                region=region.united(QRegion(note.map(QPolygonF([button.topLeft(),button.topRight(),button.bottomRight(),button.bottomLeft()])).toPolygon()))
        if region!=self.mask():self.setMask(region)
    def paint_scene(self,p,t,width,height):
        s=card_pose(t,width,height,self.origin,self.origin_width);p.save();p.translate(s.x,s.y);p.rotate(s.angle);p.scale(s.scale,s.scale)
        envelope_back(p,s.opening)
        def note():
            if s.note_opacity:
                p.save();p.setOpacity(p.opacity()*s.note_opacity)
                if not s.note_front:p.setClipRect(QRectF(-118,-500,236,580))
                p.translate(0,s.note_y);p.scale(s.note_scale,s.note_scale);self.content.paint(p,s.ready,self.hover,getattr(self,'pressed',False),ease((t-(CARD_DURATION-.25))/.25));p.restore()
        if not s.note_front:note()
        envelope_front(p,s.opening,s.seal)
        if s.note_front:note()
        p.restore();return s
    def local_note(self,position):
        inverse,ok=self.note_transform.inverted();return inverse.map(position) if ok else QPointF(-10000,-10000)
    def mouseMoveEvent(self,event):
        point=self.local_note(event.position());hover='close' if CLOSE_RECT.adjusted(-3,-3,3,3).contains(point) else 'read' if READ_RECT.contains(point) else False
        if hover!=self.hover:self.hover=hover;self.setCursor(Qt.PointingHandCursor if hover else Qt.ArrowCursor);self.update()
    def mousePressEvent(self,event):
        if self.closing_started is not None:return
        if event.button()==Qt.LeftButton and self.finished:
            point=self.local_note(event.position())
            if CLOSE_RECT.adjusted(-3,-3,3,3).contains(point):self.dismiss()
            elif READ_RECT.contains(point):self.pressed=True;self.update()
    def mouseReleaseEvent(self,event):
        if self.pressed:
            self.pressed=False;self.update()
            if READ_RECT.contains(self.local_note(event.position())):self.dismiss()
    def dismiss(self):
        if self.closing_started is not None:return
        self.read_timer.stop();self.closing_started=time.monotonic();self.next_frame=self.closing_started;self.timer.start(0)
    def wheelEvent(self,event):
        if self.finished and NOTE_RECT.contains(self.local_note(event.position())):
            self.content.scroll=max(0,min(self.content.max_scroll,self.content.scroll-event.angleDelta().y()/120*45));self.update();event.accept()
            self.read_timer.start(round(READ_SECONDS*1000))
        else:event.ignore()
    def closeEvent(self,event):
        self.timer.stop();self.read_timer.stop();self.closed.emit(self);super().closeEvent(event)

class LetterComposer(QDialog):
    preview_requested=Signal(str)
    def __init__(self,pixel_font,send,parent=None):
        super().__init__(parent);self.send_callback=send;self.setWindowTitle('Письмо для тебя');self.resize(500,350);self.setAttribute(Qt.WA_DeleteOnClose)
        layout=QVBoxLayout(self);title=QLabel('Маленькое письмо от мишки');title.setStyleSheet('font-size:20px;font-weight:bold');layout.addWidget(title)
        label=QLabel('Мишка принесёт конверт с сердечком. До 200 символов.');label.setWordWrap(True);layout.addWidget(label)
        self.editor=QPlainTextEdit();font=QFont(pixel_font);font.setPixelSize(18);self.editor.setFont(font);self.editor.setPlaceholderText('Что ты хочешь сказать?');self.editor.setMinimumHeight(170);layout.addWidget(self.editor)
        self.counter=QLabel('0 / 200');layout.addWidget(self.counter)
        buttons=QHBoxLayout();self.preview=QPushButton('Предпросмотр у меня');self.send=QPushButton('Отправить письмо');buttons.addWidget(self.preview);buttons.addWidget(self.send);layout.addLayout(buttons)
        self.preview.clicked.connect(lambda:self.preview_requested.emit(validate_letter(self.editor.toPlainText())))
        self.send.clicked.connect(self.submit);self.editor.textChanged.connect(self.changed);self.changed()
    def changed(self):
        raw=self.editor.toPlainText();count=len(canonical_letter(raw));valid=False
        try:validate_letter(raw);valid=True
        except ValueError:pass
        self.counter.setText(f'{count} / {LETTER_LIMIT}');self.counter.setStyleSheet('color:#a94462' if count>LETTER_LIMIT else 'color:#8d6871')
        self.send.setEnabled(valid);self.preview.setEnabled(valid)
    def submit(self):
        if self.send_callback(validate_letter(self.editor.toPlainText())):self.accept()
