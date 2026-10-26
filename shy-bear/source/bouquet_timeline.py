"""User-provided bouquet clip, transparent 60 fps frames, handover and nearest-edge exit."""
import json,math
from dataclasses import dataclass
from PySide6.QtCore import QRectF,QPointF,Qt
from PySide6.QtGui import QPixmap,QPainterPath,QColor,QPen

def clamp(value):return max(0.,min(1.,value))
def ease(value):value=clamp(value);return value*value*(3-2*value)
def mix(a,b,u):return a+(b-a)*u

CLIP_DURATION=6.6
OFFER_DURATION=2.8
EXIT_DURATION=2.4
DURATION=CLIP_DURATION+OFFER_DURATION+EXIT_DURATION
@dataclass(frozen=True)
class Stage:
    name:str
    start:float
    duration:float
STAGES=(Stage('video',0,CLIP_DURATION),Stage('offer',CLIP_DURATION,OFFER_DURATION),Stage('exit',CLIP_DURATION+OFFER_DURATION,EXIT_DURATION))

def sample(t,width,height,anchor_fraction=.36):
    stage=next((s for s in STAGES if t<s.start+s.duration),STAGES[-1])
    local=max(0,t-stage.start);u=clamp(local/stage.duration);anchor=width*anchor_fraction
    direction=-1 if anchor<width/2 else 1
    x=anchor
    if stage.name=='exit':
        # Accelerate into a run; decelerating off screen would make the exit feel sticky.
        progress=(u*u/(2*.16) if u<.16 else (u-.08))/(1-.08)
        x=mix(anchor,-230 if direction<0 else width+230,clamp(progress))
    return dict(stage=stage.name,local=local,u=u,x=x,anchor_x=anchor,floor=height-6,direction=direction)

class BouquetAnimation:
    def __init__(self,assets,motion=None,meta=None):
        self.meta=json.loads((assets/'bouquet-video.json').read_text(encoding='utf-8'))
        self.pages=[QPixmap(str(assets/name)) for name in self.meta['pages']]
        self.head=QPixmap(str(assets/'bouquet-video-head.png'))
        self.flowers=QPixmap(str(assets/'bouquet-video-gift.png'))
        assert all(not page.isNull() for page in self.pages) and not self.head.isNull() and not self.flowers.isNull()
        self.outline=QColor('#3e1a11');self.white=QColor('#f3f9fb')
    def frame_rect(self,index):
        index=max(0,min(self.meta['count']-1,index));page,cell=divmod(index,self.meta['per_page'])
        return page,QRectF((cell%self.meta['columns'])*384,(cell//self.meta['columns'])*216,384,216)
    def clip(self,p,t,anchor,floor,opacity=1):
        index=min(self.meta['count']-1,max(0,int(t*60)))
        page,rect=self.frame_rect(index);ground=self.meta['ground'][index]
        p.save();p.setOpacity(p.opacity()*opacity)
        p.drawPixmap(QRectF(anchor-180,floor-ground,384,216),self.pages[page],rect);p.restore()
    def path(self,p,shape):
        p.setPen(QPen(self.outline,3.5,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(self.white);p.drawPath(shape)
    def rig(self,p,phase=0,running=False,direction=-1,amount=1):
        p.save()
        if direction>0 and running:phase=-phase
        bob=1.8*math.sin(phase*2)*amount if running else 0
        # Arms sit behind the torso. Short rigid feet swing around covered hip joints.
        for left in [True,False]:
            x=149 if left else 216
            p.save();p.translate(x,137);p.rotate((8*math.sin(phase+(0 if left else math.pi))*amount) if running else 0)
            arm=QPainterPath(QPointF(0,0));arm.cubicTo(-9 if left else 9,7,-12 if left else 12,20,-4 if left else 4,27);arm.quadTo(3 if left else -3,28,5 if left else -5,16);arm.closeSubpath();self.path(p,arm);p.restore()
        for left in [True,False]:
            q=phase+(0 if left else math.pi);lift=5*max(0,math.sin(q))*amount if running else 0
            shift=3.5*math.cos(q)*amount if running else 0;x=148 if left else 184
            p.save();p.translate(x+shift,176-lift);p.rotate(4*math.cos(q)*amount if running else 0)
            foot=QPainterPath(QPointF(0,4));foot.lineTo(0,22);foot.cubicTo(0,31,8,31,15,30);foot.cubicTo(23,32,30,29,30,23);foot.lineTo(30,4);foot.cubicTo(30,-6,0,-6,0,4);foot.closeSubpath();self.path(p,foot)
            p.setPen(QPen(self.outline,1.8,Qt.SolidLine,Qt.RoundCap));p.drawLine(QPointF(11,26),QPointF(11,30));p.drawLine(QPointF(21,26),QPointF(21,30));p.restore()
        p.save();p.translate(0,bob)
        torso=QPainterPath(QPointF(158,122));torso.cubicTo(147,133,145,153,147,179);torso.cubicTo(154,184,163,184,180,183);torso.cubicTo(197,184,207,184,216,179);torso.cubicTo(220,152,217,133,205,122);torso.closeSubpath()
        # Open side contours merge into the feet, without a horizontal hip seam.
        p.fillPath(torso,self.white);p.setPen(QPen(self.outline,3.5,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
        sides=QPainterPath(QPointF(158,122));sides.cubicTo(147,133,145,153,147,179);sides.moveTo(205,122);sides.cubicTo(217,133,220,152,216,179);p.drawPath(sides)
        bridge=QPainterPath(QPointF(176,180));bridge.lineTo(186,180);bridge.lineTo(186,189);bridge.lineTo(184,189);bridge.lineTo(184,187);bridge.cubicTo(184,183,178,183,178,187);bridge.lineTo(178,189);bridge.lineTo(176,189);bridge.closeSubpath();p.fillPath(bridge,self.white)
        arch=QPainterPath(QPointF(178,189));arch.lineTo(178,187);arch.cubicTo(178,183,184,183,184,187);arch.lineTo(184,189);p.drawPath(arch)
        p.save();p.translate(180+(direction*3*amount if running else 0),126);p.rotate(direction*5*amount if running else .65*math.sin(phase)*amount);p.translate(-180,-126)
        p.drawPixmap(0,0,self.head)
        p.restore();p.restore();p.restore()
    def paint(self,p,t,width,height,anchor_fraction):
        s=sample(t,width,height,anchor_fraction);floor=s['floor'];anchor=s['anchor_x']
        if s['stage']=='video':
            self.clip(p,t,anchor,floor);return s
        local=s['local']
        if s['stage']=='offer':
            blend=ease(local/.35)
            if blend<1:self.clip(p,CLIP_DURATION,anchor,floor,1-blend)
            p.save();p.setOpacity(blend);p.translate(anchor-180,floor-207)
            self.rig(p,local*3,amount=ease(local/.25)*ease((OFFER_DURATION-local)/.25))
            reach=ease((local-.4)/1.1);drop=ease((local-1.5)/1.15)
            # Original video bouquet and hands follow one continuous rigid trajectory.
            p.translate(182,145+drop*260);p.scale(1+.55*reach,1+.55*reach);p.translate(-182,-145)
            p.drawPixmap(0,0,self.flowers);p.restore()
        else:
            p.save();p.translate(s['x']-180,floor-207)
            self.rig(p,local*2*math.pi*3.2,running=True,direction=s['direction'],amount=ease(local/.28));p.restore()
        return s


