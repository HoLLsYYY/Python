import os,sys,json,unittest
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter
from PySide6.QtCore import Qt
from bouquet_timeline import BouquetAnimation,sample,DURATION,CLIP_DURATION,OFFER_DURATION,offer_pose
app=QApplication.instance() or QApplication([])
class BouquetVideoTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.animation=BouquetAnimation(Path(__file__).resolve().parents[1]/'assets')
 def render(self,t,side=.36):
  frame=QImage(960,540,QImage.Format_RGBA8888);frame.fill(Qt.transparent);p=QPainter(frame);self.animation.paint(p,t,960,540,side);p.end();return frame
 def pixels(self,t,side=.36):
  image=self.render(t,side);return image.bits().tobytes()
 def test_transparent_video_assets_and_60fps(self):
  m=self.animation.meta;self.assertEqual(m['fps'],60);self.assertEqual(m['source_fps'],30);self.assertEqual(m['count'],396)
  self.assertEqual(len(self.animation.pages),3)
  for page in self.animation.pages:self.assertTrue(page.hasAlphaChannel());self.assertEqual(page.width(),384*12)
  self.assertTrue(self.render(0).isNull()==False);self.assertFalse(any(self.pixels(0)[3::4]))
 def test_visible_phases_and_complete_exit(self):
  for side in [.36,.64]:
   for t in [1.3,2.7,4.4,6.59,7.5,8.8,9.6]:self.assertTrue(any(self.pixels(t,side)[3::4]),(t,side))
   self.assertFalse(any(self.pixels(DURATION,side)[3::4]))
 def test_nearest_side_and_continuous_position(self):
  for side,direction in [(.36,-1),(.64,1)]:
   previous=sample(CLIP_DURATION+OFFER_DURATION,960,540,side)['x']
   for i in range(1,145):
    state=sample(CLIP_DURATION+OFFER_DURATION+i/60,960,540,side)
    self.assertEqual(state['direction'],direction);self.assertGreaterEqual(direction*(state['x']-previous),-1e-6);previous=state['x']
 def test_rendered_transition_has_no_jump(self):
  for side in [.36,.64]:
   for t in [CLIP_DURATION,CLIP_DURATION+OFFER_DURATION]:
    a=self.pixels(t-1e-6,side);b=self.pixels(t+1e-6,side)
    mean=sum(abs(x-y) for x,y in zip(a,b))/len(a)
    self.assertLess(mean,.15,(t,side,mean))
 def test_only_flowers_and_wrapping_travel_with_the_gift(self):
  image=self.animation.flowers.toImage()
  # Former nose/fur above the petals, both hands, and detached torso pieces.
  for x,y in [(174,80),(156,84),(134,99),(151,154),(213,154),(155,170),(204,174),(186,196)]:
   self.assertEqual(image.pixelColor(x,y).alpha(),0,(x,y))
  self.assertGreater(image.pixelColor(181,114).alpha(),250)
  self.assertGreater(image.pixelColor(182,182).alpha(),250)
 def test_muzzle_has_strokes_without_a_brown_fill_or_cheek_remnants(self):
  image=self.animation.head.toImage()
  for x,y in [(175,90),(185,90),(160,116),(200,116),(230,111)]:
   color=image.pixelColor(x,y)
   self.assertGreater(color.red(),230,(x,y,color.name()))
   self.assertEqual(color.alpha(),255)
  for x,y in [(180,82),(180,89),(171,94),(189,94)]:
   self.assertLess(image.pixelColor(x,y).red(),150,(x,y))
 def test_video_to_offer_blend_keeps_shared_body_opaque(self):
  for dt in [.04,.12,.175,.23,.31]:
   image=self.render(CLIP_DURATION+dt)
   # A shared forehead point must not let the desktop shine through during a blend.
   self.assertGreaterEqual(image.pixelColor(round(960*.36),365).alpha(),250,dt)
 def test_gift_releases_after_hands_open_and_pose_is_continuous(self):
  self.assertEqual(offer_pose(1.6)['drop'],0)
  self.assertLess(offer_pose(1.6)['grip'],.32)
  self.assertEqual(offer_pose(1.75)['grip'],0)
  self.assertEqual(offer_pose(OFFER_DURATION)['scale'],1.25)
  for local in [.4,1.35,1.5,1.6,1.75,2.75]:
   a=self.pixels(CLIP_DURATION+local-1e-6);b=self.pixels(CLIP_DURATION+local+1e-6)
   self.assertLess(sum(abs(x-y) for x,y in zip(a,b))/len(a),.15,local)
if __name__=='__main__':unittest.main()

