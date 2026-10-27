"""A single, stable glossy heart mesh drawn as layered vector surfaces."""
import math
from PySide6.QtCore import Qt,QRectF,QPointF
from PySide6.QtGui import QPainterPath,QColor,QLinearGradient,QRadialGradient,QPen,QFont

TEXT='Вам хотят напомнить как сильно вас любят и ценят'
DURATION=25.0
SIZE=(300,285)  # 1.5 times the bear's 200 x 190 animation cell.

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

class LoveHeart:
    def __init__(self,font):
        self.font=QFont(font);self.font.setPixelSize(17)
        self.shape=QPainterPath(QPointF(0,-89))
        self.shape.cubicTo(-49,-151,-147,-126,-145,-48)
        self.shape.cubicTo(-143,12,-59,76,0,131)
        self.shape.cubicTo(59,76,143,12,145,-48)
        self.shape.cubicTo(147,-126,49,-151,0,-89)
        self.shape.closeSubpath()
    def paint(self,p,t,width,height):
        if t<=0 or t>=DURATION:return
        entry=smooth(t/1.35);leave=smooth((t-(DURATION-1.4))/1.4)
        # Gentle settling, not a repeated zoom: lettering stays still enough to read.
        scale=(.82+.18*entry)*(1-.07*leave)
        p.save();p.setOpacity(entry*(1-leave))
        p.translate(width/2,height/2+22*(1-entry)+18*leave+2*math.sin(t*1.1)*entry)
        p.rotate(1.1*math.sin(t*.8)*entry);p.scale(scale,scale)
        p.setPen(Qt.NoPen)
        for depth in range(10,0,-1):
            p.save();p.translate(depth*.5,depth)
            p.setBrush(QColor('#81233f' if depth>5 else '#b63758'));p.drawPath(self.shape);p.restore()
        body=QLinearGradient(-95,-125,100,130)
        for pos,color in [(0,'#ffadc3'),(.25,'#f8779d'),(.55,'#e54c7b'),(.8,'#c53161'),(1,'#922544')]:body.setColorAt(pos,QColor(color))
        p.setBrush(body);p.setPen(QPen(QColor('#a32d50'),1.4));p.drawPath(self.shape)
        p.save();p.setClipPath(self.shape)
        glow=QRadialGradient(QPointF(-72,-83),94)
        glow.setColorAt(0,QColor(255,239,246,125));glow.setColorAt(1,QColor(255,225,239,0))
        p.setBrush(glow);p.setPen(Qt.NoPen);p.drawEllipse(QRectF(-166,-177,188,188))
        shine=QPainterPath(QPointF(-115,-65));shine.cubicTo(-115,-104,-87,-118,-63,-108)
        p.setPen(QPen(QColor(255,238,245,180),5,Qt.SolidLine,Qt.RoundCap));p.drawPath(shine)
        p.restore()
        p.setFont(self.font)
        lines=['Вам хотят','напомнить как','сильно вас','любят и ценят']
        for index,line in enumerate(lines):
            rect=QRectF(-119,-48+index*27,238,26)
            p.setPen(QColor('#942d4d'));p.drawText(rect.translated(0,1.5),Qt.AlignCenter,line)
            p.setPen(QColor('#fff6ed'));p.drawText(rect,Qt.AlignCenter,line)
        p.restore()
