"""Seven sequential, deterministic stages for the bouquet visit."""
import math,json,sys
from pathlib import Path
from dataclasses import dataclass
from PySide6.QtCore import QRectF,QPointF,Qt
from PySide6.QtGui import QPixmap,QPainter,QPainterPath,QColor,QPen


def clamp(x):return max(0.,min(1.,x))
def ease(x):x=clamp(x);return x*x*(3-2*x)
def mix(a,b,u):return a+(b-a)*u

def rotate(x,y,angle):
    a=math.radians(angle);return x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)

_support=json.loads((Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))/'assets'/'bouquet-support.json').read_text())

def bottom(angle,sy=1):
    index=(angle%360)*4;left=int(index);fraction=index-left
    return mix(_support[left],_support[(left+1)%1440],fraction)*sy

@dataclass(frozen=True)
class Stage:
    name:str
    start:float
    duration:float

STAGES=(Stage('peeking',0,1.8),Stage('slip',1.8,.65),Stage('flip_hang',2.45,3.1),Stage('fall',5.55,1.25),Stage('get_up',6.8,1.65),Stage('offer',8.45,3.6),Stage('exit',12.05,2.6))
DURATION=14.65

def sample(t,width,height,anchor_fraction=.36):
    stage=next((s for s in STAGES if t<s.start+s.duration),STAGES[-1])
    local=max(0,t-stage.start);u=clamp(local/stage.duration)
    ax=width*anchor_fraction;floor=height-6
    x,y,angle,sy=ax,112.,0.,1.
    left,right=1.,1.;flower=0.;bare=1.;dust=0.;offer=0.;walk=0.
    sx=1.
    if stage.name=='peeking':
        left=right=ease(local/.18)
        if local<.65:
            q=ease(local/.65);y=mix(-110,20,q);angle=180
        elif local<.95:
            q=(local-.65)/.3;y=20;angle=180+1.5*math.sin(q*2*math.pi)*math.sin(q*math.pi)
        else:
            q=ease((local-.95)/.85);y=mix(20,112,q);angle=mix(180,0,q)
    elif stage.name=='slip':
        if local<.1:angle=-4*math.sin(math.pi*local/.1)
        else:
            q=clamp((local-.1)/.55);left=1-ease(q/.25)
            angle=22*(q/.68)**3 if q<.68 else 22+5*math.sin((q-.68)/.32*2*math.pi)*math.exp(-5*(q-.68)/.32)
        dx,dy=rotate(-65,103,angle);x=ax+65+dx;y=9+dy
    elif stage.name=='flip_hang':
        left=0.;flower=ease((local-.1)/.35)
        start_x,start_y=rotate(-65,103,22)
        if local<.1:
            angle=22-4*math.sin(math.pi*local/.1)
            dx,dy=rotate(-65,103,angle);x=ax+65+dx;y=9+dy
        elif local<.9:
            q=ease((local-.1)/.8);x=mix(ax+65+start_x,ax,q);y=mix(9+start_y,145,q);angle=mix(22,180,q)
        else:
            q=(local-.9)/2.2;swing=11*math.sin(q*5*math.pi)*math.exp(-2.2*q)
            dx,dy=rotate(-65,136,swing);x=ax+65+dx;y=9+dy;angle=180+swing
    elif stage.name=='fall':
        release=clamp((local-.12)/.18)
        left=0.;right=1-ease(release);flower=1.;bare=1-ease(release)
        if local<.12:
            q=local/.12;y=145-3*math.sin(math.pi*q);angle=180-2*math.sin(math.pi*q)
        elif local<=1.05:
            q=clamp((local-.12)/.93);angle=mix(180,270,ease(q))
            sy=1+.12*math.sin(math.pi*q)*math.sqrt(q);sx=1/math.sqrt(sy)
            y=mix(145,floor-bottom(270),q**3)
        else:
            angle=270;impact=(local-1.05)/.2;sy=1-.13*math.sin(math.pi*impact);sx=1/math.sqrt(sy);y=floor-bottom(270,sy)
    elif stage.name=='get_up':
        left=right=0.;bare=0.;flower=1.
        if local<.12:angle=270-3*math.sin(math.pi*local/.12)
        else:angle=mix(270,360,ease((local-.12)/.83))
        y=floor-bottom(angle)
        if local>.95:
            shake=(local-.95)/.7;amplitude=math.sin(math.pi*shake)
            x+=2.2*math.sin(shake*10*math.pi)*amplitude;dust=clamp((local-.95)/.7)
    elif stage.name=='offer':
        left=right=0.;bare=0.;flower=1.;offer=local
        env=min(ease(local/.3),ease((3.6-local)/.3))
        x+=1.8*math.sin(local*2.8*math.pi)*env;angle=360+1.2*math.sin(local*2.8*math.pi)*env
        y=floor-bottom(angle)
    else:
        left=right=0.;bare=0.;flower=0.;angle=360
        walk=clamp((local-.35)/2.25)
        target=-140 if anchor_fraction<.5 else width+140
        x=mix(ax,target,ease(walk))
        if local<.35:
            wind=math.sin(math.pi*local/.35);x+=2*wind*(1 if anchor_fraction<.5 else -1);angle=360+2*wind
        y=floor-bottom(angle)-1.2*math.sin(walk*12*math.pi)*math.sin(math.pi*walk)
    return dict(stage=stage.name,local=local,u=u,x=round(x,4),y=round(y,4),angle=round(angle,4),sy=round(sy,5),sx=round(sx,5),stage_duration=stage.duration,left=left,right=right,flower=flower,bare=bare,dust=dust,offer=offer,walk=walk,anchor_x=ax,floor=floor)


class BouquetAnimation:
    def __init__(self,assets,motion,meta):
        self.neutral=QPixmap(str(assets/'canonical-reference.png'))
        self.flowers=QPixmap(str(assets/'bouquet.png'))
        self.motion=motion;self.meta=meta
        self.bare=self.neutral.copy();p=QPainter(self.bare)
        p.setCompositionMode(QPainter.CompositionMode_Source);p.fillRect(QRectF(45,115,110,38),Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver);p.setRenderHint(QPainter.Antialiasing)
        torso=QPainterPath(QPointF(80,110));torso.quadTo(73,128,75,153);torso.lineTo(126,153);torso.quadTo(128,128,120,110);torso.closeSubpath()
        p.fillPath(torso,QColor('#fffefe'))
        pen=QPen(QColor('#48251f'),4.2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin);p.setPen(pen)
        side=QPainterPath(QPointF(80,114));side.quadTo(73,131,75,151);p.drawPath(side)
        side=QPainterPath(QPointF(120,114));side.quadTo(128,131,126,151);p.drawPath(side);p.end()
        self.head=self.neutral.copy(0,0,200,116)
        self.body_neutral=self.neutral.copy();self.body_bare=self.bare.copy()
        for layer in [self.body_neutral,self.body_bare]:
            painter=QPainter(layer);painter.setCompositionMode(QPainter.CompositionMode_Clear);painter.fillRect(QRectF(0,0,200,110),Qt.transparent);painter.end()
    def frame(self,name,phase):
        m=self.meta[name];i=min(m['count']-1,int(clamp(phase)*m['count']))
        return self.motion[name].copy(0,i*m['height'],m['width'],m['height'])
    def flower(self,p,x,y,scale=1,angle=0,opacity=1):
        p.save();p.setOpacity(p.opacity()*opacity);p.translate(round(x,4),round(y,4));p.rotate(round(angle,4)%360);p.scale(scale,scale)
        p.drawPixmap(QRectF(-34,-83,68,86),self.flowers,QRectF(self.flowers.rect()));p.restore()
    def paint(self,p,t,width,height,anchor_fraction):
        s=sample(t,width,height,anchor_fraction);ax=s['anchor_x']
        velocity=(sample(t+.005,width,height,anchor_fraction)['angle']-sample(max(0,t-.005),width,height,anchor_fraction)['angle'])/.01
        envelope=min(ease(s['local']/.14),ease((s['stage_duration']-s['local'])/.14))
        head_lag=max(-2.8,min(2.8,-velocity*.009))*envelope
        if s['stage']=='get_up' or s['stage']=='fall' and s['local']>=.9:head_lag=0
        head_lag=round(head_lag,4)
        held_angle=-25+4*math.sin(t*5)-max(-16,min(16,velocity*.04))*envelope
        # The hands are fixed to the monitor edge; the body hangs beneath them.
        def body_point(px,py):
            dx,dy=rotate(px-100,py-95,s['angle']);return QPointF(s['x']+dx*s['sx'],s['y']+dy*s['sy'])
        wrist_y=9.;wrists={}
        for side,amount in [('left',s['left']),('right',s['right'])]:
            if amount<=0:continue
            shoulder=body_point(74 if side=='left' else 126,123)
            wrist=QPointF(ax+(-65 if side=='left' else 65),wrist_y)
            if s['stage']=='fall' or s['stage']=='slip' and side=='left':
                q=ease((s['local']-(.12 if s['stage']=='fall' else .1))/(.18 if s['stage']=='fall' else .1375));wrist=QPointF(mix(wrist.x(),shoulder.x(),q),mix(wrist.y(),shoulder.y(),q))
            wrists[side]=wrist
            p.save();p.setOpacity(amount);path=QPainterPath(shoulder)
            path.quadTo(wrist.x()+max(-8,min(8,velocity*.025))*envelope,shoulder.y()-18,wrist.x(),wrist.y())
            p.setPen(QPen(QColor('#48251f'),16,Qt.SolidLine,Qt.RoundCap));p.drawPath(path)
            p.setPen(QPen(QColor('#fffefe'),10,Qt.SolidLine,Qt.RoundCap));p.drawPath(path);p.restore()
        p.save();p.translate(s['x'],s['y']);p.scale(s['sx'],s['sy']);p.rotate(s['angle']%360)
        if s['stage']=='exit':
            if anchor_fraction>=.5 and s['local']<.35:image=self.frame('turn-right',s['local']/.35)
            else:image=self.frame('return-walk' if anchor_fraction>=.5 else 'walk',s['walk'])
            p.drawPixmap(QPointF(-100,-95),image)
        else:
            p.save()
            if s['stage']=='offer':p.shear(round(.015*math.sin(s['local']*2.8*math.pi)*min(ease(s['local']/.3),ease((3.6-s['local'])/.3)),6),0)
            p.drawPixmap(QPointF(-100,-95),self.body_bare if s['bare']>0 else self.body_neutral)
            if 0<s['bare']<1:p.save();p.setOpacity(1-s['bare']);p.drawPixmap(QPointF(-100,-95),self.body_neutral);p.restore()
            p.restore()
            p.save();p.translate(0,15);p.rotate(head_lag);p.translate(0,-15);p.drawPixmap(QPointF(-100,-95),self.head);p.restore()
        p.restore()
        if s['flower']>0 and s['stage']!='offer':
            hand=body_point(61,148);flower_angle=s['angle']+held_angle
            offsets=[rotate(cx,cy,flower_angle)[1] for cx in (-34,34) for cy in (-83,3)]
            hand.setY(hand.y()-max(0,hand.y()+max(offsets)-s['floor']))
            self.flower(p,hand.x(),hand.y(),opacity=s['flower'],angle=flower_angle)
            p.save();p.setOpacity(s['flower']);p.setPen(QPen(QColor('#48251f'),2.5));p.setBrush(QColor('#fffefe'));p.drawEllipse(QPointF(hand.x(),hand.y()-2),8,7);p.restore()
        # Gripping paws sit in front of the body and remain on the edge.
        for side,amount in [('left',s['left']),('right',s['right'])]:
            if amount<=0:continue
            p.save();p.setOpacity(amount);p.setPen(QPen(QColor('#48251f'),3.5));p.setBrush(QColor('#fffefe'))
            p.drawEllipse(wrists[side],12,8);p.restore()
        if s['stage']=='get_up' and s['local']>=.95:
            q=s['dust']
            for i in range(8):
                direction=-1 if i%2==0 else 1;speed=22+(i//2)*12
                px=s['x']+direction*(24+speed*q);py=s['floor']-14-(25+i*3)*q+30*q*q
                p.save();p.setOpacity((1-q)*.6);p.setPen(Qt.NoPen);p.setBrush(QColor('#d1c9ce'));p.drawEllipse(QPointF(px,py),2+i%3,2+i%3);p.restore()
        if s['stage']=='offer':
            local=s['offer'];reach=ease((local-.65)/1.2);lower=ease((local-1.95)/1.25)
            scale=mix(1,2,reach);fx=s['x']+mix(-39,0,reach);fy=s['y']+mix(53,61,reach)+lower*260
            self.flower(p,fx,fy,scale,held_angle*(1-reach))
            if lower<.05:
                p.save();p.setPen(QPen(QColor('#48251f'),2.5));p.setBrush(QColor('#fffefe'));p.drawEllipse(QPointF(fx,fy-3),8,7);p.restore()
        return s

