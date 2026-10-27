import os,sys,unittest,time
from pathlib import Path
from unittest.mock import Mock
os.environ['QT_QPA_PLATFORM']='offscreen'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import test_letter_routing
import bear
from love_heart import DURATION,TEXT
from PySide6.QtGui import QImage,QPainter
class LoveTests(unittest.TestCase):
 setUp=test_letter_routing.LetterRoutingTests.setUp
 tearDown=test_letter_routing.LetterRoutingTests.tearDown
 def test_love_encrypted_delivery_and_update_check(self):
  c=self.control;key=bear.new_code();payload,_=bear.encode(key,'love');data=bear.decode(key,payload,set());c.updater=Mock()
  c.receive(data);self.assertEqual(c.pet.action,'love');self.assertTrue(c.pet.active);c.updater.check.assert_called_once()
  screen=bear.QApplication.primaryScreen();self.assertEqual(c.pet.geometry().right(),screen.geometry().right());self.assertEqual(c.pet.geometry().bottom(),screen.availableGeometry().bottom());self.assertEqual(DURATION,12.5)
  c.pet.draw_entry=Mock();c.pet.draw_heart=Mock();c.pet.started=time.monotonic()-3;c.pet.grab();c.pet.draw_entry.assert_not_called();c.pet.draw_heart.assert_not_called()
  c.pet.started=time.monotonic()-DURATION-.1;c.pet.tick();self.assertFalse(c.pet.active)
 def test_every_frame_is_renderable_and_inside_window(self):
  c=self.control
  for frame in range(int(DURATION*60)+1):
   image=QImage(340,335,QImage.Format_ARGB32_Premultiplied);image.fill(0);p=QPainter(image);c.pet.love_heart.paint(p,frame/60,340,335);p.end()
   for x,y in [(0,0),(339,334),(170,0),(170,334)]:self.assertEqual(image.pixelColor(x,y).alpha(),0)
  self.assertEqual(TEXT,'Вам хотят напомнить как сильно вас любят и ценят')
if __name__=='__main__':unittest.main()
