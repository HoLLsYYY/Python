"""User-provided bouquet clip, transparent 60 fps frames, handover and nearest-edge exit."""
import json,math
from dataclasses import dataclass
from PySide6.QtCore import QRectF,QPointF,Qt
from PySide6.QtGui import QPixmap,QPainter,QPainterPath,QColor,QPen

def clamp(value):return max(0.,min(1.,value))
def ease(value):value=clamp(value);return value*value*(3-2*value)
def mix(a,b,u):return a+(b-a)*u

def offer_pose(local):
    reach=ease((local-.4)/1.1)
    release=ease((local-1.35)/.4)
    return dict(scale=1+.25*reach,drop=260*ease((local-1.6)/1.15),
                grip=1-release,reach=reach)

def clean_head(source):
    """Keep the clip's eyes and ears; rebuild the occluded muzzle and cheek contour."""
    result=QPixmap(source.size());result.fill(Qt.transparent)
    p=QPainter(result);p.setRenderHint(QPainter.Antialiasing)
    white=QColor('#f3f9fb');ink=QColor('#3e1a11')
    # Ears retain the original shape; the head has one clean contour instead of matte remnants.
    p.setPen(QPen(ink,3.2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    for rect in [QRectF(89,17,44,43),QRectF(219,12,43,42)]:
        p.setBrush(white);p.drawEllipse(rect)
        p.setPen(Qt.NoPen);p.setBrush(QColor('#edb8ba'));p.drawEllipse(rect.adjusted(10,10,-10,-10))
        p.setPen(QPen(ink,3.2,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    edge=QPainterPath(QPointF(180,7));edge.cubicTo(145,6,116,25,109,58)
    edge.cubicTo(105,73,105,88,102,99);edge.cubicTo(98,119,134,131,180,131)
    edge.cubicTo(225,131,256,118,252,99);edge.cubicTo(256,75,244,39,226,21)
    edge.cubicTo(211,9,197,6,180,7);edge.closeSubpath();p.setBrush(white);p.drawPath(edge)
    # Keep the actual eye pixels from the clip, without any bouquet-coloured muzzle pixels.
    for rect in [QRectF(136,68,20,20),QRectF(197,63,21,20)]:
        p.save();eye=QPainterPath();eye.addEllipse(rect);p.setClipPath(eye);p.drawPixmap(0,0,source);p.restore()
    p.setPen(Qt.NoPen);p.setBrush(QColor('#edb8ba'))
    p.drawEllipse(QRectF(111,81,27,24));p.drawEllipse(QRectF(219,78,27,25))
    p.setPen(Qt.NoPen);p.setBrush(ink)
    nose=QPainterPath(QPointF(173,80));nose.quadTo(180,78,187,80)
    nose.quadTo(185,84,180,85);nose.quadTo(175,84,173,80);p.drawPath(nose)
    p.setBrush(Qt.NoBrush);p.setPen(QPen(ink,2.6,Qt.SolidLine,Qt.RoundCap))
    mouth=QPainterPath(QPointF(180,84));mouth.lineTo(180,90)
    mouth.cubicTo(179,96,172,96,169,92);mouth.moveTo(180,90)
    mouth.cubicTo(182,96,188,96,191,92);p.drawPath(mouth);p.end()
    return result

def clean_flowers(source):
    """Flowers and wrapping only. Skin pixels never travel with the present."""
    result=QPixmap(source.size());result.fill(Qt.transparent)
    p=QPainter(result);p.setRenderHint(QPainter.Antialiasing)
    # Follow the petals and paper inside the original matte, excluding nose, fur and hands.
    points=[(139,105),(139,94),(142,90),(150,91),(155,88),(160,91),(168,96),
            (174,86),(181,79),(188,79),(199,83),(209,92),(221,96),
            (230,104),(229,114),(233,118),(225,130),(216,139),
            (203,143),(192,155),(177,158),(164,145),(146,134),
            (136,126),(135,121),(138,119),(134,111)]
    boundary=QPainterPath(QPointF(*points[0]))
    for point in points[1:]:boundary.lineTo(*point)
    boundary.closeSubpath();p.setClipPath(boundary);p.drawPixmap(0,0,source);p.setClipping(False)
    # The hands hid this part of the paper in the video; restore its folded shape.
    p.setPen(QPen(QColor('#795043'),1.6,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    paper=QPainterPath(QPointF(153,135));paper.quadTo(166,138,180,150)
    paper.quadTo(193,138,212,135);paper.lineTo(194,162);paper.lineTo(199,187)
    paper.quadTo(183,197,168,186);paper.lineTo(174,161);paper.closeSubpath()
    p.setBrush(QColor('#f2e5ce'));p.drawPath(paper)
    p.setPen(QPen(QColor('#bc9d82'),1.2));p.drawLine(QPointF(163,141),QPointF(181,161))
    p.drawLine(QPointF(203,141),QPointF(183,161));p.drawLine(QPointF(183,167),QPointF(181,188))
    p.setPen(QPen(QColor('#9c605c'),1.4,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin));p.setBrush(QColor('#e5a3a6'))
    for sign in [-1,1]:
        bow=QPainterPath(QPointF(182,161));bow.cubicTo(182+sign*8,151,182+sign*20,158,182+sign*12,166)
        bow.quadTo(182+sign*6,170,182,164);p.drawPath(bow)
        ribbon=QPainterPath(QPointF(182+sign*3,164));ribbon.lineTo(182+sign*19,181)
        ribbon.lineTo(182+sign*12,179);ribbon.lineTo(182+sign*10,185)
        ribbon.quadTo(182+sign*2,178,182,165);p.drawPath(ribbon)
    p.setBrush(QColor('#edb3b5'));p.drawEllipse(QRectF(178.5,158,7,7));p.end()
    return result

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
        self.head=clean_head(QPixmap(str(assets/'bouquet-video-head.png')))
        self.flowers=clean_flowers(QPixmap(str(assets/'bouquet-video-gift.png')))
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
    def hands(self,p,local):
        pose=offer_pose(local);grip=pose['grip']
        p.save();p.setOpacity(p.opacity()*ease(grip/.3))
        for left in [True,False]:
            sign=-1 if left else 1
            # Release leads the bouquet's downward movement; wrists stay attached to shoulders.
            x=mix(149 if left else 216,155 if left else 209,grip)+sign*pose['reach']*3*grip
            y=mix(160,153,grip)
            shoulder=149 if left else 216
            arm=QPainterPath(QPointF(shoulder,137))
            arm.cubicTo(shoulder+sign*6,143,x+sign*12,y+5,x+sign*6,y+9)
            arm.cubicTo(x-sign*2,y+12,x-sign*10,y+6,x-sign*10,y)
            arm.quadTo(x-sign*9,y-7,x-sign*3,y-7)
            arm.quadTo(shoulder-sign*2,147,shoulder,137)
            self.path(p,arm)
        p.restore()
    def offer(self,p,local):
        self.rig(p,local*3,amount=ease(local/.25)*ease((OFFER_DURATION-local)/.25))
        pose=offer_pose(local)
        p.save();p.translate(182,145+pose['drop']);p.scale(pose['scale'],pose['scale']);p.translate(-182,-145)
        p.drawPixmap(0,0,self.flowers);p.restore()
        if pose['grip']>0:self.hands(p,local)
    def paint(self,p,t,width,height,anchor_fraction):
        s=sample(t,width,height,anchor_fraction);floor=s['floor'];anchor=s['anchor_x']
        if s['stage']=='video':
            self.clip(p,t,anchor,floor);return s
        local=s['local']
        if s['stage']=='offer':
            blend=ease(local/.35)
            p.save();p.translate(anchor-180,floor-207)
            if blend<1:
                # Mix premultiplied layers before compositing onto the desktop, keeping
                # the shared silhouette opaque throughout the video-to-rig transition.
                current=QPixmap(384,500);current.fill(Qt.transparent)
                q=QPainter(current);q.setRenderHints(p.renderHints());self.offer(q,local);q.end()
                weighted=QPixmap(current.size());weighted.fill(Qt.transparent)
                q=QPainter(weighted);q.setOpacity(blend);q.drawPixmap(0,0,current);q.end()
                combined=QPixmap(current.size());combined.fill(Qt.transparent)
                q=QPainter(combined);q.setRenderHints(p.renderHints())
                self.clip(q,CLIP_DURATION,180,207,1-blend)
                q.setCompositionMode(QPainter.CompositionMode_Plus)
                q.drawPixmap(0,0,weighted);q.end();p.drawPixmap(0,0,combined)
            else:self.offer(p,local)
            p.restore()
        else:
            p.save();p.translate(s['x']-180,floor-207)
            self.rig(p,local*2*math.pi*3.2,running=True,direction=s['direction'],amount=ease(local/.28));p.restore()
        return s

