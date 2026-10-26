import os,sys,json,unittest,math,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
os.environ['QT_QPA_PLATFORM']='offscreen';sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from protocol import new_code,encode,decode,validate_letter,LETTER_LIMIT
from letter_scene import (LetterCard,LetterComposer,LetterPose,NoteContent,card_pose,held_pose,
                          CARD_DURATION,CARD_ANGLE,NOTE_RECT,CLOSE_RECT,READ_RECT,READ_SECONDS,DISMISS_DURATION,HANDOFF_TIME,HANDOFF_WIDTH,HANDOFF_Y)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QPainter,QFont,QFontDatabase,QTransform
from PySide6.QtCore import Qt,QPointF
from PySide6.QtTest import QTest
app=QApplication.instance() or QApplication([]);assets=Path(__file__).resolve().parents[1]/'assets'
fid=QFontDatabase.addApplicationFont(str(assets/'Mojangles.ttf'));font=QFont(QFontDatabase.applicationFontFamilies(fid)[0],17)

class LetterProtocolTests(unittest.TestCase):
 def test_encrypted_roundtrip_unicode_newlines_and_200_characters(self):
  key=new_code();text=('Я рядом ♥\n'+'Ш'*200)[:200];payload,ident=encode(key,'letter',text=text,sender='a',target='b',reply_to=new_code())
  self.assertNotIn('Я рядом',payload);data=decode(key,payload,set());self.assertEqual(data['text'],text);self.assertEqual(data['id'],ident)
 def test_validation_rejects_empty_too_long_and_controls(self):
  for text in [None,123,'','  \n ','а'*201,'текст\x00письма']:
   with self.assertRaises(ValueError):validate_letter(text)
  self.assertEqual(validate_letter('  Привет!\r\nЯ рядом.  '),'Привет!\nЯ рядом.')
 def test_tamper_wrong_key_and_replay_rejected(self):
  key=new_code();payload,_=encode(key,'letter',text='Привет!');seen=set();decode(key,payload,seen)
  with self.assertRaises(ValueError):decode(key,payload,seen)
  with self.assertRaises(Exception):decode(new_code(),payload,set())
 def test_decoded_oversize_text_rejected(self):
  import base64,secrets
  from cryptography.hazmat.primitives.ciphers.aead import AESGCM
  from protocol import key_for
  key=new_code();nonce=secrets.token_bytes(12);data={'cmd':'letter','id':'test','time':time.time(),'text':'а'*201}
  payload=base64.urlsafe_b64encode(nonce+AESGCM(key_for(key)).encrypt(nonce,json.dumps(data).encode(),b'bear-v1')).decode()
  with self.assertRaises(ValueError):decode(key,payload,set())

class LetterVisualTests(unittest.TestCase):
 def card(self,text='Я рядом. Обнимаю! ♥'):
  return SimpleNamespace(origin=(1140,671),origin_width=HANDOFF_WIDTH,content=NoteContent(text,font),hover=False)
 def render(self,t,text='Я рядом. Обнимаю! ♥',size=(1280,720)):
  image=QImage(*size,QImage.Format_RGBA8888);image.fill(Qt.transparent);p=QPainter(image);p.setRenderHint(QPainter.Antialiasing);LetterCard.paint_scene(self.card(text),p,t,*size);p.end();return image
 def test_common_200_character_messages_fit_and_keep_font(self):
  for text in ['Ш'*200,('Ты рядом, даже когда далеко. '*8)[:200],'♥'*200]:
   content=NoteContent(text,font);self.assertEqual(content.font.family(),font.family());self.assertLessEqual(content.font.pixelSize(),12);self.assertGreaterEqual(content.font.pixelSize(),10)
   self.assertEqual(content.max_scroll,0,(len(text),content.height,content.font.pixelSize()))
 def test_explicit_long_line_breaks_remain_scrollable(self):
  content=NoteContent(('Я\n'*99)+'Я',font);self.assertGreater(content.max_scroll,0);self.assertEqual(content.text.count('\n'),99)
 def test_corner_angle_compact_size_and_continuous_pose(self):
  for width,height in [(640,480),(1280,720),(1920,1080)]:
   for t in [1.1,2.25,3.75,4.85]:
    state=card_pose(t,width,height);self.assertEqual(state.angle,CARD_ANGLE);self.assertLessEqual(state.scale*240,280.01)
    if state.note_opacity and t>=3.75:
     transform=QTransform();transform.translate(state.x,state.y);transform.rotate(state.angle);transform.scale(state.scale*state.note_scale,state.scale*state.note_scale);transform.translate(0,state.note_y)
     for point in [NOTE_RECT.topLeft(),NOTE_RECT.topRight(),NOTE_RECT.bottomLeft(),NOTE_RECT.bottomRight()]:
      point=transform.map(point);self.assertGreaterEqual(point.x(),-1);self.assertLessEqual(point.x(),width+1);self.assertGreaterEqual(point.y(),-1);self.assertLessEqual(point.y(),height+1)
  for t in [.6,1.9,2.15,HANDOFF_TIME]:
   a,b=held_pose(t-1e-7),held_pose(t+1e-7);self.assertLess(abs(a.y-b.y),.001);self.assertLess(abs(a.scale-b.scale),.001)
 def test_layer_switch_has_no_visual_jump(self):
  for t in [1.9,3.95,CARD_DURATION]:
   a=self.render(t-1e-6);b=self.render(t+1e-6);ma=sum(abs(x-y) for x,y in zip(a.bits().tobytes(),b.bits().tobytes()))/(1280*720*4);self.assertLess(ma,.02,(t,ma))
 def test_text_inside_envelope_does_not_leak_below_it(self):
  actual=self.render(2.2);card=self.card();card.content=SimpleNamespace(paint=lambda *args:None)
  reference=QImage(1280,720,QImage.Format_RGBA8888);reference.fill(Qt.transparent);p=QPainter(reference);p.setRenderHint(QPainter.Antialiasing);LetterCard.paint_scene(card,p,2.2,1280,720);p.end()
  a=actual.bits().tobytes()[3::4];b=reference.bits().tobytes()[3::4]
  self.assertFalse(any(x>32 and y==0 for x,y in zip(a,b)))
 def test_close_hit_target_and_stopped_idle_timer(self):
  card=LetterCard('Письмо ♥',font);card.started=time.monotonic()-CARD_DURATION-1;card.tick();app.processEvents();card.repaint();app.processEvents()
  self.assertTrue(card.finished);self.assertFalse(card.timer.isActive());self.assertFalse(bool(card.windowFlags()&Qt.WindowTransparentForInput))
  self.assertEqual(card.read_timer.interval(),10000);self.assertTrue(card.read_timer.isActive())
  point=card.note_transform.map(CLOSE_RECT.center());self.assertTrue(card.mask().contains(point.toPoint()));self.assertFalse(card.mask().contains(QPointF(10,10).toPoint()))
  closed=[];card.closed.connect(lambda item:closed.append(True));QTest.mouseClick(card,Qt.LeftButton,Qt.NoModifier,point.toPoint());QTest.qWait(450);app.processEvents();self.assertEqual(closed,[True])
 def test_read_button_and_expiry_close_the_note_gently(self):
  self.assertEqual(READ_SECONDS,10)
  for by_button in [True,False]:
   card=LetterCard('Прочитать ♥',font);card.started=time.monotonic()-CARD_DURATION-1;card.tick();app.processEvents();card.repaint();closed=[];card.closed.connect(lambda item:closed.append(True))
   if by_button:
    point=card.note_transform.map(READ_RECT.center()).toPoint();self.assertTrue(card.mask().contains(point));QTest.mouseClick(card,Qt.LeftButton,Qt.NoModifier,point)
    self.assertIsNotNone(card.closing_started);self.assertFalse(closed)
   else:card.read_timer.start(1)
   QTest.qWait(450);app.processEvents();self.assertEqual(closed,[True])
 def test_composer_limit_and_preview_do_not_send(self):
  send=Mock(return_value=True);dialog=LetterComposer(font,send);previews=[];dialog.preview_requested.connect(previews.append)
  self.assertFalse(dialog.send.isEnabled());dialog.editor.setPlainText('а'*201);self.assertFalse(dialog.send.isEnabled())
  dialog.editor.setPlainText('Я скучаю ♥');self.assertTrue(dialog.send.isEnabled());dialog.preview.click();self.assertEqual(previews,['Я скучаю ♥']);send.assert_not_called()
  dialog.send.click();send.assert_called_once_with('Я скучаю ♥');dialog.close()

if __name__=='__main__':unittest.main()


